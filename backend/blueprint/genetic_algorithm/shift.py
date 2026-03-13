
from flask import Blueprint, request, jsonify
from config import db
from model import Shift
from datetime import datetime

shift_bp = Blueprint("shift", __name__, url_prefix="/shifts")


# Helper to parse time strings e.g. "06:00:00"
def parse_time(time_str):
    try:
        return datetime.strptime(time_str, "%H:%M:%S").time()
    except ValueError:
        return None


# CREATE — POST /shifts
@shift_bp.route("/", methods=["POST"])
def create_shift():
    data = request.get_json()

    # Validate required fields
    required = ["shift_name", "start_time", "end_time"]
    for field in required:
        if field not in data:
            return jsonify({"error": f"Missing required field: {field}"}), 400

    start_time = parse_time(data["start_time"])
    end_time = parse_time(data["end_time"])

    if not start_time or not end_time:
        return jsonify({"error": "Invalid time format. Use HH:MM:SS"}), 400

    if start_time >= end_time:
        return jsonify({"error": "start_time must be before end_time"}), 400

    # Check for duplicate shift name
    if Shift.query.filter_by(shift_name=data["shift_name"]).first():
        return jsonify({"error": "Shift name already exists"}), 409

    new_shift = Shift(
        shift_name=data["shift_name"],
        start_time=start_time,
        end_time=end_time,
    )

    db.session.add(new_shift)
    db.session.commit()

    return jsonify(new_shift.to_json()), 201


# READ ALL — GET /shifts
@shift_bp.route("/", methods=["GET"])
def get_shifts():
    shifts = Shift.query.all()
    return jsonify([s.to_json() for s in shifts]), 200


# READ ONE — GET /shifts/<id>
@shift_bp.route("/<int:shift_id>", methods=["GET"])
def get_shift(shift_id):
    shift = Shift.query.get_or_404(shift_id)
    return jsonify(shift.to_json()), 200


# READ OVERLAPPING — GET /shifts/overlapping?start=06:00:00&end=14:00:00
# Useful for checking if a new shift clashes with existing ones
@shift_bp.route("/overlapping", methods=["GET"])
def get_overlapping_shifts():
    start_str = request.args.get("start")
    end_str = request.args.get("end")

    if not start_str or not end_str:
        return jsonify({"error": "Provide both start and end query params e.g. ?start=06:00:00&end=14:00:00"}), 400

    start_time = parse_time(start_str)
    end_time = parse_time(end_str)

    if not start_time or not end_time:
        return jsonify({"error": "Invalid time format. Use HH:MM:SS"}), 400

    # A shift overlaps if it starts before our end AND ends after our start
    overlapping = Shift.query.filter(
        Shift.start_time < end_time,
        Shift.end_time > start_time
    ).all()

    return jsonify([s.to_json() for s in overlapping]), 200


# UPDATE — PUT /shifts/<id>
@shift_bp.route("/<int:shift_id>", methods=["PUT"])
def update_shift(shift_id):
    shift = Shift.query.get_or_404(shift_id)
    data = request.get_json()

    # Parse times if provided
    start_time = parse_time(data["start_time"]) if "start_time" in data else shift.start_time
    end_time = parse_time(data["end_time"]) if "end_time" in data else shift.end_time

    if "start_time" in data and not start_time:
        return jsonify({"error": "Invalid start_time format. Use HH:MM:SS"}), 400
    if "end_time" in data and not end_time:
        return jsonify({"error": "Invalid end_time format. Use HH:MM:SS"}), 400

    if start_time >= end_time:
        return jsonify({"error": "start_time must be before end_time"}), 400

    # Check name uniqueness if being changed
    if "shift_name" in data and data["shift_name"] != shift.shift_name:
        if Shift.query.filter_by(shift_name=data["shift_name"]).first():
            return jsonify({"error": "Shift name already exists"}), 409

    shift.shift_name = data.get("shift_name", shift.shift_name)
    shift.start_time = start_time
    shift.end_time = end_time

    db.session.commit()

    return jsonify(shift.to_json()), 200


# DELETE — DELETE /shifts/<id>
@shift_bp.route("/<int:shift_id>", methods=["DELETE"])
def delete_shift(shift_id):
    shift = Shift.query.get_or_404(shift_id)

    # Prevent deleting a shift that has assignments
    if shift.assignments:
        return jsonify({"error": "Cannot delete shift with existing assignments. Reassign or delete them first."}), 409

    db.session.delete(shift)
    db.session.commit()

    return jsonify({"message": f"Shift {shift_id} deleted."}), 200