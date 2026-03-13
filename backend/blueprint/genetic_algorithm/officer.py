from flask import Blueprint, request, jsonify
from config import db
from model import Officer

officer_bp = Blueprint("officer", __name__, url_prefix="/officers")


# CREATE — POST /officerss
@officer_bp.route("/", methods=["POST"])
def create_officer():
    data = request.get_json()

    # Validate status if provided
    valid_statuses = ["active", "inactive", "on_leave"]
    if "status" in data and data["status"] not in valid_statuses:
        return jsonify({"error": f"Invalid status. Must be one of: {valid_statuses}"}), 400

    # Check badge number is unique
    if Officer.query.filter_by(badge_number=data.get("badge_number")).first():
        return jsonify({"error": "Badge number already exists"}), 409

    new_officer = Officer(
        badge_number=data["badge_number"],
        full_name=data["full_name"],
        rank=data["rank"],
        status=data.get("status", "active"),        # defaults to active
        max_weekly_hours=data.get("max_weekly_hours", 40),  # defaults to 40
    )

    db.session.add(new_officer)
    db.session.commit()

    return jsonify(new_officer.to_json()), 201


# READ ALL — GET /officers
@officer_bp.route("/", methods=["GET"])
def get_officers():
    officers = Officer.query.all()
    return jsonify([o.to_json() for o in officers]), 200


# READ ONE — GET /officers/<id>
@officer_bp.route("/<int:officer_id>", methods=["GET"])
def get_officer(officer_id):
    officer = Officer.query.get_or_404(officer_id)
    return jsonify(officer.to_json()), 200


# READ BY STATUS — GET /officers/status/<status>
# e.g. GET /officers/status/active  ← useful for GA to fetch available officers
@officer_bp.route("/status/<string:status>", methods=["GET"])
def get_officers_by_status(status):
    valid_statuses = ["active", "inactive", "on_leave"]
    if status not in valid_statuses:
        return jsonify({"error": f"Invalid status. Must be one of: {valid_statuses}"}), 400

    officers = Officer.query.filter_by(status=status).all()
    return jsonify([o.to_json() for o in officers]), 200


# UPDATE — PUT /officers/<id>
@officer_bp.route("/<int:officer_id>", methods=["PUT"])
def update_officer(officer_id):
    officer = Officer.query.get_or_404(officer_id)
    data = request.get_json()

    # Validate status if being changed
    valid_statuses = ["active", "inactive", "on_leave"]
    if "status" in data and data["status"] not in valid_statuses:
        return jsonify({"error": f"Invalid status. Must be one of: {valid_statuses}"}), 400

    # Check badge number uniqueness if being changed
    if "badge_number" in data and data["badge_number"] != officer.badge_number:
        if Officer.query.filter_by(badge_number=data["badge_number"]).first():
            return jsonify({"error": "Badge number already exists"}), 409

    officer.badge_number = data.get("badge_number", officer.badge_number)
    officer.full_name = data.get("full_name", officer.full_name)
    officer.rank = data.get("rank", officer.rank)
    officer.status = data.get("status", officer.status)
    officer.max_weekly_hours = data.get("max_weekly_hours", officer.max_weekly_hours)

    db.session.commit()

    return jsonify(officer.to_json()), 200


# DELETE — DELETE /officers/<id>
@officer_bp.route("/<int:officer_id>", methods=["DELETE"])
def delete_officer(officer_id):
    officer = Officer.query.get_or_404(officer_id)

    db.session.delete(officer)
    db.session.commit()

    return jsonify({"message": f"Officer {officer_id} deleted."}), 200