from flask import Blueprint, request, jsonify
from config import db
from model import ShiftRule, Officer

shift_rule_bp = Blueprint("shift_rule", __name__, url_prefix="/shiftrules")


# CREATE — POST /shiftrules
@shift_rule_bp.route("/", methods=["POST"])
def create_shift_rule():
    data = request.get_json()

    required = ["rank", "max_consecutive_hours", "break_required"]
    for field in required:
        if field not in data:
            return jsonify({"error": f"Missing required field: {field}"}), 400

    # rank is the PK so must be unique
    if ShiftRule.query.get(data["rank"]):
        return jsonify({"error": f"ShiftRule for rank '{data['rank']}' already exists"}), 409

    try:
        max_hours = int(data["max_consecutive_hours"])
        if max_hours <= 0:
            raise ValueError
    except (ValueError, TypeError):
        return jsonify({"error": "max_consecutive_hours must be a positive integer"}), 400

    if not isinstance(data["break_required"], bool):
        return jsonify({"error": "break_required must be a boolean (true or false)"}), 400

    new_rule = ShiftRule(
        rank=data["rank"],
        max_consecutive_hours=max_hours,
        break_required=data["break_required"],
    )

    db.session.add(new_rule)
    db.session.commit()

    return jsonify(new_rule.to_json()), 201


# READ ALL — GET /shiftrules
@shift_rule_bp.route("/", methods=["GET"])
def get_shift_rules():
    rules = ShiftRule.query.all()
    return jsonify([r.to_json() for r in rules]), 200


# READ ONE — GET /shiftrules/<rank>
# e.g. GET /shiftrules/Supervisor
@shift_rule_bp.route("/<string:rank>", methods=["GET"])
def get_shift_rule(rank):
    rule = ShiftRule.query.get_or_404(rank)
    return jsonify(rule.to_json()), 200


# READ BY OFFICER — GET /shiftrules/officer/<officer_id>
# Looks up the shift rule that applies to a specific officer based on their rank
@shift_rule_bp.route("/officer/<int:officer_id>", methods=["GET"])
def get_shift_rule_by_officer(officer_id):
    officer = Officer.query.get_or_404(officer_id)

    rule = ShiftRule.query.get(officer.rank)
    if not rule:
        return jsonify({
            "error": f"No ShiftRule found for rank '{officer.rank}'. Create one at POST /shiftrules."
        }), 404

    return jsonify({
        "officer_id": officer.officer_id,
        "officer_name": officer.full_name,
        "rank": officer.rank,
        "shift_rule": rule.to_json(),
    }), 200


# UPDATE — PUT /shiftrules/<rank>
# Only max_consecutive_hours and break_required can be updated
# rank is the PK and cannot be changed
@shift_rule_bp.route("/<string:rank>", methods=["PUT"])
def update_shift_rule(rank):
    rule = ShiftRule.query.get_or_404(rank)
    data = request.get_json()

    # Block PK changes
    if "rank" in data and data["rank"] != rank:
        return jsonify({"error": "rank is the primary key and cannot be changed. Delete and recreate instead."}), 400

    if "max_consecutive_hours" not in data and "break_required" not in data:
        return jsonify({"error": "Provide at least one of: max_consecutive_hours, break_required"}), 400

    if "max_consecutive_hours" in data:
        try:
            max_hours = int(data["max_consecutive_hours"])
            if max_hours <= 0:
                raise ValueError
            rule.max_consecutive_hours = max_hours
        except (ValueError, TypeError):
            return jsonify({"error": "max_consecutive_hours must be a positive integer"}), 400

    if "break_required" in data:
        if not isinstance(data["break_required"], bool):
            return jsonify({"error": "break_required must be a boolean (true or false)"}), 400
        rule.break_required = data["break_required"]

    db.session.commit()

    return jsonify(rule.to_json()), 200


# DELETE — DELETE /shiftrules/<rank>
# Blocked if any officers currently hold this rank
@shift_rule_bp.route("/<string:rank>", methods=["DELETE"])
def delete_shift_rule(rank):
    rule = ShiftRule.query.get_or_404(rank)

    # Check if any officers use this rank
    linked_officers = Officer.query.filter_by(rank=rank).count()
    if linked_officers > 0:
        return jsonify({
            "error": f"Cannot delete rule for rank '{rank}' — {linked_officers} officer(s) currently hold this rank.",
            "officer_count": linked_officers,
        }), 409

    db.session.delete(rule)
    db.session.commit()

    return jsonify({"message": f"ShiftRule for rank '{rank}' deleted."}), 200