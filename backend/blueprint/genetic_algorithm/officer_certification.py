from flask import Blueprint, request, jsonify
from config import db
from model import OfficerCertification, Officer
from datetime import datetime, date

officer_certification_bp = Blueprint("officer_certification", __name__, url_prefix="/certifications")


def parse_date(date_str):
    try:
        return date.fromisoformat(date_str)
    except (ValueError, TypeError):
        return None


# CREATE — POST /certifications
@officer_certification_bp.route("/", methods=["POST"])
def create_certification():
    data = request.get_json()

    required = ["officer_id_fk", "qualification_id"]
    for field in required:
        if field not in data:
            return jsonify({"error": f"Missing required field: {field}"}), 400

    # Validate officer exists
    if not Officer.query.get(data["officer_id_fk"]):
        return jsonify({"error": "Officer not found"}), 404

    try:
        qualification_id = int(data["qualification_id"])
        if qualification_id <= 0:
            raise ValueError
    except (ValueError, TypeError):
        return jsonify({"error": "qualification_id must be a positive integer"}), 400

    # Check for duplicate certification for same officer + qualification
    existing = OfficerCertification.query.filter_by(
        officer_id_fk=data["officer_id_fk"],
        qualification_id=qualification_id,
    ).first()
    if existing:
        return jsonify({
            "error": f"Officer {data['officer_id_fk']} already holds certification for qualification {qualification_id}",
            "cert_id": existing.cert_id,
        }), 409

    # Validate expiry_date if provided
    expiry_date = None
    if "expiry_date" in data and data["expiry_date"]:
        expiry_date = parse_date(data["expiry_date"])
        if not expiry_date:
            return jsonify({"error": "Invalid expiry_date format. Use ISO 8601 e.g. 2026-12-31"}), 400

        # Warn if expiry date is in the past
        if expiry_date < date.today():
            return jsonify({
                "error": "expiry_date is in the past. If this is intentional use POST /certifications/expired to record it."
            }), 400

    new_cert = OfficerCertification(
        officer_id_fk=data["officer_id_fk"],
        qualification_id=qualification_id,
        expiry_date=expiry_date,
    )

    db.session.add(new_cert)
    db.session.commit()

    return jsonify(new_cert.to_json()), 201


# CREATE EXPIRED — POST /certifications/expired
# Allows recording certifications that are already expired
# e.g. for historical data import during initial system setup
@officer_certification_bp.route("/expired", methods=["POST"])
def create_expired_certification():
    data = request.get_json()

    required = ["officer_id_fk", "qualification_id", "expiry_date"]
    for field in required:
        if field not in data:
            return jsonify({"error": f"Missing required field: {field}"}), 400

    if not Officer.query.get(data["officer_id_fk"]):
        return jsonify({"error": "Officer not found"}), 404

    try:
        qualification_id = int(data["qualification_id"])
        if qualification_id <= 0:
            raise ValueError
    except (ValueError, TypeError):
        return jsonify({"error": "qualification_id must be a positive integer"}), 400

    expiry_date = parse_date(data["expiry_date"])
    if not expiry_date:
        return jsonify({"error": "Invalid expiry_date format. Use ISO 8601 e.g. 2025-01-01"}), 400

    new_cert = OfficerCertification(
        officer_id_fk=data["officer_id_fk"],
        qualification_id=qualification_id,
        expiry_date=expiry_date,
    )

    db.session.add(new_cert)
    db.session.commit()

    return jsonify(new_cert.to_json()), 201


# READ ALL — GET /certifications
@officer_certification_bp.route("/", methods=["GET"])
def get_certifications():
    certs = OfficerCertification.query.all()
    return jsonify([c.to_json() for c in certs]), 200


# READ ONE — GET /certifications/<id>
@officer_certification_bp.route("/<int:cert_id>", methods=["GET"])
def get_certification(cert_id):
    cert = OfficerCertification.query.get_or_404(cert_id)
    return jsonify(cert.to_json()), 200


# READ BY OFFICER — GET /certifications/officer/<officer_id>
# Returns all certifications held by a specific officer
@officer_certification_bp.route("/officer/<int:officer_id>", methods=["GET"])
def get_certifications_by_officer(officer_id):
    if not Officer.query.get(officer_id):
        return jsonify({"error": "Officer not found"}), 404

    certs = OfficerCertification.query.filter_by(officer_id_fk=officer_id).all()
    return jsonify([c.to_json() for c in certs]), 200


# READ EXPIRING SOON — GET /certifications/expiring?days=30
# Returns certifications expiring within the next N days
# Useful for admin dashboard to flag officers needing renewal
@officer_certification_bp.route("/expiring", methods=["GET"])
def get_expiring_certifications():
    try:
        days = int(request.args.get("days", 30))
        if days <= 0:
            raise ValueError
    except (ValueError, TypeError):
        return jsonify({"error": "days must be a positive integer"}), 400

    from datetime import timedelta
    cutoff = date.today() + timedelta(days=days)

    certs = OfficerCertification.query.filter(
        OfficerCertification.expiry_date != None,
        OfficerCertification.expiry_date <= cutoff,
        OfficerCertification.expiry_date >= date.today(),
    ).order_by(OfficerCertification.expiry_date.asc()).all()

    return jsonify([c.to_json() for c in certs]), 200


# READ EXPIRED — GET /certifications/expired
# Returns all certifications that have already expired
@officer_certification_bp.route("/expired", methods=["GET"])
def get_expired_certifications():
    certs = OfficerCertification.query.filter(
        OfficerCertification.expiry_date != None,
        OfficerCertification.expiry_date < date.today(),
    ).order_by(OfficerCertification.expiry_date.asc()).all()

    return jsonify([c.to_json() for c in certs]), 200


# UPDATE — PUT /certifications/<id>
# Only expiry_date can be updated — officer and qualification are immutable
@officer_certification_bp.route("/<int:cert_id>", methods=["PUT"])
def update_certification(cert_id):
    cert = OfficerCertification.query.get_or_404(cert_id)
    data = request.get_json()

    # Block changes to identity fields
    if "officer_id_fk" in data or "qualification_id" in data:
        return jsonify({"error": "officer_id_fk and qualification_id cannot be changed. Delete and recreate instead."}), 400

    if "expiry_date" not in data:
        return jsonify({"error": "Nothing to update. Provide an expiry_date field."}), 400

    if data["expiry_date"] is None:
        cert.expiry_date = None
    else:
        expiry_date = parse_date(data["expiry_date"])
        if not expiry_date:
            return jsonify({"error": "Invalid expiry_date format. Use ISO 8601 e.g. 2026-12-31"}), 400
        cert.expiry_date = expiry_date

    db.session.commit()

    return jsonify(cert.to_json()), 200


# DELETE — DELETE /certifications/<id>
@officer_certification_bp.route("/<int:cert_id>", methods=["DELETE"])
def delete_certification(cert_id):
    cert = OfficerCertification.query.get_or_404(cert_id)

    db.session.delete(cert)
    db.session.commit()

    return jsonify({"message": f"Certification {cert_id} deleted."}), 200