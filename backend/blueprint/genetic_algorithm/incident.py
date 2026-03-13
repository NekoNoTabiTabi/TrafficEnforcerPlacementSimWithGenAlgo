from flask import Blueprint, request, jsonify
from config import db
from model import Incident, Bottleneck
from datetime import datetime

incident_bp = Blueprint("incident", __name__, url_prefix="/incidents")


VALID_SEVERITIES = ["critical", "major", "minor", "informational"]
VALID_STATUSES = ["active", "resolved"]


def parse_datetime(dt_str):
    try:
        return datetime.fromisoformat(dt_str)
    except (ValueError, TypeError):
        return None


# CREATE — POST /incidents
@incident_bp.route("/", methods=["POST"])
def create_incident():
    data = request.get_json()

    # Validate required fields
    required = ["severity", "report_time"]
    for field in required:
        if field not in data:
            return jsonify({"error": f"Missing required field: {field}"}), 400

    if data["severity"] not in VALID_SEVERITIES:
        return jsonify({"error": f"Invalid severity. Must be one of: {VALID_SEVERITIES}"}), 400

    report_time = parse_datetime(data["report_time"])
    if not report_time:
        return jsonify({"error": "Invalid report_time format. Use ISO 8601 e.g. 2025-06-15T08:30:00"}), 400

    # Validate bottleneck exists if provided (nullable — mobile incidents have no fixed bottleneck)
    if data.get("bottleneck_id_fk") and not Bottleneck.query.get(data["bottleneck_id_fk"]):
        return jsonify({"error": "Bottleneck not found"}), 404

    new_incident = Incident(
        bottleneck_id_fk=data.get("bottleneck_id_fk"),  # nullable
        report_time=report_time,
        severity=data["severity"],
        status=data.get("status", "active"),             # defaults to active
    )

    db.session.add(new_incident)
    db.session.commit()

    return jsonify(new_incident.to_json()), 201


# READ ALL — GET /incidents
@incident_bp.route("/", methods=["GET"])
def get_incidents():
    incidents = Incident.query.order_by(Incident.report_time.desc()).all()
    return jsonify([i.to_json() for i in incidents]), 200


# READ ONE — GET /incidents/<id>
@incident_bp.route("/<int:incident_id>", methods=["GET"])
def get_incident(incident_id):
    incident = Incident.query.get_or_404(incident_id)
    return jsonify(incident.to_json()), 200


# READ ACTIVE — GET /incidents/active
# Returns all unresolved incidents — primary feed for dashboard alert ticker
@incident_bp.route("/active", methods=["GET"])
def get_active_incidents():
    incidents = Incident.query.filter_by(
        status="active"
    ).order_by(Incident.report_time.desc()).all()

    return jsonify([i.to_json() for i in incidents]), 200


# READ BY SEVERITY — GET /incidents/severity/<severity>
# e.g. GET /incidents/severity/critical — triggers re-optimization check
@incident_bp.route("/severity/<string:severity>", methods=["GET"])
def get_incidents_by_severity(severity):
    if severity not in VALID_SEVERITIES:
        return jsonify({"error": f"Invalid severity. Must be one of: {VALID_SEVERITIES}"}), 400

    incidents = Incident.query.filter_by(
        severity=severity
    ).order_by(Incident.report_time.desc()).all()

    return jsonify([i.to_json() for i in incidents]), 200


# READ BY BOTTLENECK — GET /incidents/bottleneck/<bottleneck_id>
@incident_bp.route("/bottleneck/<int:bottleneck_id>", methods=["GET"])
def get_incidents_by_bottleneck(bottleneck_id):
    if not Bottleneck.query.get(bottleneck_id):
        return jsonify({"error": "Bottleneck not found"}), 404

    incidents = Incident.query.filter_by(
        bottleneck_id_fk=bottleneck_id
    ).order_by(Incident.report_time.desc()).all()

    return jsonify([i.to_json() for i in incidents]), 200


# READ ACTIVE CRITICAL/MAJOR — GET /incidents/active/serious
# Convenience route — returns active incidents that should trigger re-optimization
@incident_bp.route("/active/serious", methods=["GET"])
def get_serious_active_incidents():
    incidents = Incident.query.filter(
        Incident.status == "active",
        Incident.severity.in_(["critical", "major"])
    ).order_by(Incident.report_time.desc()).all()

    return jsonify([i.to_json() for i in incidents]), 200


# UPDATE — PUT /incidents/<id>
@incident_bp.route("/<int:incident_id>", methods=["PUT"])
def update_incident(incident_id):
    incident = Incident.query.get_or_404(incident_id)
    data = request.get_json()

    if "severity" in data and data["severity"] not in VALID_SEVERITIES:
        return jsonify({"error": f"Invalid severity. Must be one of: {VALID_SEVERITIES}"}), 400

    if "status" in data and data["status"] not in VALID_STATUSES:
        return jsonify({"error": f"Invalid status. Must be one of: {VALID_STATUSES}"}), 400

    if "bottleneck_id_fk" in data and data["bottleneck_id_fk"]:
        if not Bottleneck.query.get(data["bottleneck_id_fk"]):
            return jsonify({"error": "Bottleneck not found"}), 404

    if "report_time" in data:
        report_time = parse_datetime(data["report_time"])
        if not report_time:
            return jsonify({"error": "Invalid report_time format. Use ISO 8601 e.g. 2025-06-15T08:30:00"}), 400
        incident.report_time = report_time

    incident.bottleneck_id_fk = data.get("bottleneck_id_fk", incident.bottleneck_id_fk)
    incident.severity = data.get("severity", incident.severity)
    incident.status = data.get("status", incident.status)

    db.session.commit()

    return jsonify(incident.to_json()), 200


# RESOLVE — PATCH /incidents/<id>/resolve
# Dedicated route for marking an incident resolved
# more explicit than a generic PUT for this common workflow
@incident_bp.route("/<int:incident_id>/resolve", methods=["PATCH"])
def resolve_incident(incident_id):
    incident = Incident.query.get_or_404(incident_id)

    if incident.status == "resolved":
        return jsonify({"error": "Incident is already resolved"}), 409

    incident.status = "resolved"
    db.session.commit()

    return jsonify(incident.to_json()), 200


# DELETE — DELETE /incidents/<id>
@incident_bp.route("/<int:incident_id>", methods=["DELETE"])
def delete_incident(incident_id):
    incident = Incident.query.get_or_404(incident_id)

    db.session.delete(incident)
    db.session.commit()

    return jsonify({"message": f"Incident {incident_id} deleted."}), 200