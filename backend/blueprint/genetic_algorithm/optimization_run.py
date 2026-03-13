from flask import Blueprint, request, jsonify
from config import db
from model import OptimizationRun, Assignment
from datetime import datetime

optimization_run_bp = Blueprint("optimization_run", __name__, url_prefix="/runs")


def parse_datetime(dt_str):
    try:
        return datetime.fromisoformat(dt_str)
    except (ValueError, TypeError):
        return None


# CREATE — POST /runs
# Called programmatically by the GA engine when a run completes
@optimization_run_bp.route("/", methods=["POST"])
def create_optimization_run():
    data = request.get_json()

    required = ["input_data_hash", "best_fitness", "convergence_gen"]
    for field in required:
        if field not in data:
            return jsonify({"error": f"Missing required field: {field}"}), 400

    try:
        best_fitness = float(data["best_fitness"])
    except (ValueError, TypeError):
        return jsonify({"error": "best_fitness must be a number"}), 400

    try:
        convergence_gen = int(data["convergence_gen"])
        if convergence_gen < 0:
            raise ValueError
    except (ValueError, TypeError):
        return jsonify({"error": "convergence_gen must be a non-negative integer"}), 400

    run_timestamp = parse_datetime(data["run_timestamp"]) if "run_timestamp" in data else datetime.utcnow()
    if "run_timestamp" in data and not run_timestamp:
        return jsonify({"error": "Invalid run_timestamp format. Use ISO 8601 e.g. 2025-06-15T08:30:00"}), 400

    new_run = OptimizationRun(
        input_data_hash=data["input_data_hash"],
        run_timestamp=run_timestamp,
        best_fitness=best_fitness,
        convergence_gen=convergence_gen,
    )

    db.session.add(new_run)
    db.session.commit()

    return jsonify(new_run.to_json()), 201


# READ ALL — GET /runs
# Ordered by most recent first
@optimization_run_bp.route("/", methods=["GET"])
def get_optimization_runs():
    runs = OptimizationRun.query.order_by(OptimizationRun.run_timestamp.desc()).all()
    return jsonify([r.to_json() for r in runs]), 200


# READ ONE — GET /runs/<id>
@optimization_run_bp.route("/<int:ga_run_id>", methods=["GET"])
def get_optimization_run(ga_run_id):
    run = OptimizationRun.query.get_or_404(ga_run_id)
    return jsonify(run.to_json()), 200


# READ WITH ASSIGNMENTS — GET /runs/<id>/assignments
# Returns the run plus all assignments it generated
# Useful for the supervisor review screen and Gantt chart
@optimization_run_bp.route("/<int:ga_run_id>/assignments", methods=["GET"])
def get_run_with_assignments(ga_run_id):
    run = OptimizationRun.query.get_or_404(ga_run_id)

    return jsonify({
        **run.to_json(),
        "assignments": [a.to_json() for a in run.assignments],
        "total_assignments": len(run.assignments),
    }), 200


# READ BEST — GET /runs/best
# Returns the run with the highest fitness score across all runs
@optimization_run_bp.route("/best", methods=["GET"])
def get_best_run():
    run = OptimizationRun.query.order_by(OptimizationRun.best_fitness.desc()).first()

    if not run:
        return jsonify({"error": "No optimization runs found"}), 404

    return jsonify(run.to_json()), 200


# READ LATEST — GET /runs/latest
# Returns the most recently executed run
# Useful for dashboard to show last optimization result
@optimization_run_bp.route("/latest", methods=["GET"])
def get_latest_run():
    run = OptimizationRun.query.order_by(OptimizationRun.run_timestamp.desc()).first()

    if not run:
        return jsonify({"error": "No optimization runs found"}), 404

    return jsonify({
        **run.to_json(),
        "assignments": [a.to_json() for a in run.assignments],
        "total_assignments": len(run.assignments),
    }), 200


# READ BY DATE RANGE — GET /runs/range?from=2025-06-01T00:00:00&to=2025-06-30T23:59:59
# Useful for the scenario analysis / historical comparison tool
@optimization_run_bp.route("/range", methods=["GET"])
def get_runs_by_date_range():
    from_str = request.args.get("from")
    to_str = request.args.get("to")

    if not from_str or not to_str:
        return jsonify({"error": "Provide both ?from=<ISO timestamp>&to=<ISO timestamp> query params"}), 400

    from_dt = parse_datetime(from_str)
    to_dt = parse_datetime(to_str)

    if not from_dt or not to_dt:
        return jsonify({"error": "Invalid timestamp format. Use ISO 8601 e.g. 2025-06-01T00:00:00"}), 400

    if from_dt >= to_dt:
        return jsonify({"error": "from must be before to"}), 400

    runs = OptimizationRun.query.filter(
        OptimizationRun.run_timestamp >= from_dt,
        OptimizationRun.run_timestamp <= to_dt
    ).order_by(OptimizationRun.run_timestamp.desc()).all()

    return jsonify([r.to_json() for r in runs]), 200


# READ BY HASH — GET /runs/hash/<hash>
# Check if an identical input snapshot has already been optimized
# Avoids redundant GA runs when data hasn't changed
@optimization_run_bp.route("/hash/<string:input_data_hash>", methods=["GET"])
def get_run_by_hash(input_data_hash):
    runs = OptimizationRun.query.filter_by(
        input_data_hash=input_data_hash
    ).order_by(OptimizationRun.run_timestamp.desc()).all()

    if not runs:
        return jsonify({"error": "No runs found for this input hash"}), 404

    return jsonify([r.to_json() for r in runs]), 200


# UPDATE — PUT /runs/<id>
# Limited — only fitness and convergence_gen can be corrected post-run
# run_timestamp and input_data_hash are immutable for audit integrity
@optimization_run_bp.route("/<int:ga_run_id>", methods=["PUT"])
def update_optimization_run(ga_run_id):
    run = OptimizationRun.query.get_or_404(ga_run_id)
    data = request.get_json()

    if "best_fitness" in data:
        try:
            run.best_fitness = float(data["best_fitness"])
        except (ValueError, TypeError):
            return jsonify({"error": "best_fitness must be a number"}), 400

    if "convergence_gen" in data:
        try:
            convergence_gen = int(data["convergence_gen"])
            if convergence_gen < 0:
                raise ValueError
            run.convergence_gen = convergence_gen
        except (ValueError, TypeError):
            return jsonify({"error": "convergence_gen must be a non-negative integer"}), 400

    # Explicitly block changes to audit fields
    if "input_data_hash" in data or "run_timestamp" in data:
        return jsonify({"error": "input_data_hash and run_timestamp are immutable for audit integrity"}), 400

    db.session.commit()

    return jsonify(run.to_json()), 200


# DELETE — DELETE /runs/<id>
# Blocked if the run has assignments — delete assignments first
@optimization_run_bp.route("/<int:ga_run_id>", methods=["DELETE"])
def delete_optimization_run(ga_run_id):
    run = OptimizationRun.query.get_or_404(ga_run_id)

    if run.assignments:
        return jsonify({
            "error": "Cannot delete a run with existing assignments. Delete or reassign them first.",
            "assignment_count": len(run.assignments),
        }), 409

    db.session.delete(run)
    db.session.commit()

    return jsonify({"message": f"OptimizationRun {ga_run_id} deleted."}), 200