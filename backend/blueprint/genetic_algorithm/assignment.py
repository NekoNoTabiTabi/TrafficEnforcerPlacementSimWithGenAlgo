from flask import Blueprint, request, jsonify
from config import db
from model import Assignment, Officer, Bottleneck, OptimizationRun, Shift

assignment_bp = Blueprint("assignment", __name__, url_prefix="/assignments")


# CREATE — POST /assignments
@assignment_bp.route("/", methods=["POST"])
def create_assignment():
    data = request.get_json()

    # Validate required foreign keys exist
    if not Officer.query.get(data.get("officer_id_fk")):
        return jsonify({"error": "Officer not found"}), 404
    if not Bottleneck.query.get(data.get("bottleneck_id_fk")):
        return jsonify({"error": "Bottleneck not found"}), 404
    if not Shift.query.get(data.get("shift_id_fk")):
        return jsonify({"error": "Shift not found"}), 404

    # ga_run_id_fk is optional but validate if provided
    if data.get("ga_run_id_fk") and not OptimizationRun.query.get(data.get("ga_run_id_fk")):
        return jsonify({"error": "OptimizationRun not found"}), 404

    new_assignment = Assignment(
        officer_id_fk=data["officer_id_fk"],
        bottleneck_id_fk=data["bottleneck_id_fk"],
        shift_id_fk=data["shift_id_fk"],
        assignment_date=data["assignment_date"],
        ga_run_id_fk=data.get("ga_run_id_fk"),   # optional
        status=data.get("status", "planned"),      # defaults to planned
    )

    db.session.add(new_assignment)
    db.session.commit()

    return jsonify(new_assignment.to_json()), 201


# READ ALL — GET /assignments
@assignment_bp.route("/", methods=["GET"])
def get_assignments():
    assignments = Assignment.query.all()
    return jsonify([a.to_json() for a in assignments]), 200


# READ ONE — GET /assignments/<id>
@assignment_bp.route("/<int:assignment_id>", methods=["GET"])
def get_assignment(assignment_id):
    assignment = Assignment.query.get_or_404(assignment_id)
    return jsonify(assignment.to_json()), 200


# READ BY OFFICER — GET /assignments/officer/<officer_id>
@assignment_bp.route("/officer/<int:officer_id>", methods=["GET"])
def get_assignments_by_officer(officer_id):
    assignments = Assignment.query.filter_by(officer_id_fk=officer_id).all()
    return jsonify([a.to_json() for a in assignments]), 200


# READ BY BOTTLENECK — GET /assignments/bottleneck/<bottleneck_id>
@assignment_bp.route("/bottleneck/<int:bottleneck_id>", methods=["GET"])
def get_assignments_by_bottleneck(bottleneck_id):
    assignments = Assignment.query.filter_by(bottleneck_id_fk=bottleneck_id).all()
    return jsonify([a.to_json() for a in assignments]), 200


# UPDATE — PUT /assignments/<id>
@assignment_bp.route("/<int:assignment_id>", methods=["PUT"])
def update_assignment(assignment_id):
    assignment = Assignment.query.get_or_404(assignment_id)
    data = request.get_json()

    # Validate foreign keys if they are being changed
    if "officer_id_fk" in data and not Officer.query.get(data["officer_id_fk"]):
        return jsonify({"error": "Officer not found"}), 404
    if "bottleneck_id_fk" in data and not Bottleneck.query.get(data["bottleneck_id_fk"]):
        return jsonify({"error": "Bottleneck not found"}), 404
    if "shift_id_fk" in data and not Shift.query.get(data["shift_id_fk"]):
        return jsonify({"error": "Shift not found"}), 404
    if "ga_run_id_fk" in data and data["ga_run_id_fk"] and not OptimizationRun.query.get(data["ga_run_id_fk"]):
        return jsonify({"error": "OptimizationRun not found"}), 404

    assignment.officer_id_fk = data.get("officer_id_fk", assignment.officer_id_fk)
    assignment.bottleneck_id_fk = data.get("bottleneck_id_fk", assignment.bottleneck_id_fk)
    assignment.shift_id_fk = data.get("shift_id_fk", assignment.shift_id_fk)
    assignment.ga_run_id_fk = data.get("ga_run_id_fk", assignment.ga_run_id_fk)
    assignment.assignment_date = data.get("assignment_date", assignment.assignment_date)
    assignment.status = data.get("status", assignment.status)

    db.session.commit()

    return jsonify(assignment.to_json()), 200


# DELETE — DELETE /assignments/<id>
@assignment_bp.route("/<int:assignment_id>", methods=["DELETE"])
def delete_assignment(assignment_id):
    assignment = Assignment.query.get_or_404(assignment_id)

    db.session.delete(assignment)
    db.session.commit()

    return jsonify({"message": f"Assignment {assignment_id} deleted."}), 200