from flask import Blueprint, request, jsonify
from config import db
from model import TrafficMetric, Bottleneck
from datetime import datetime

traffic_metric_bp = Blueprint("traffic_metric", __name__, url_prefix="/traffic")


VALID_SOURCES = ["API", "manual"]


def parse_datetime(dt_str):
    try:
        return datetime.fromisoformat(dt_str)
    except (ValueError, TypeError):
        return None


# CREATE ONE — POST /traffic
@traffic_metric_bp.route("/", methods=["POST"])
def create_traffic_metric():
    data = request.get_json()

    required = ["bottleneck_id_fk", "timestamp", "congestion_level", "average_speed"]
    for field in required:
        if field not in data:
            return jsonify({"error": f"Missing required field: {field}"}), 400

    if not Bottleneck.query.get(data["bottleneck_id_fk"]):
        return jsonify({"error": "Bottleneck not found"}), 404

    timestamp = parse_datetime(data["timestamp"])
    if not timestamp:
        return jsonify({"error": "Invalid timestamp format. Use ISO 8601 e.g. 2025-06-15T08:30:00"}), 400

    try:
        congestion = int(data["congestion_level"])
        if not (0 <= congestion <= 100):
            raise ValueError
    except (ValueError, TypeError):
        return jsonify({"error": "congestion_level must be an integer between 0 and 100"}), 400

    try:
        speed = float(data["average_speed"])
        if not (0 <= speed <= 150):
            raise ValueError
    except (ValueError, TypeError):
        return jsonify({"error": "average_speed must be a number between 0 and 150"}), 400

    if "data_source" in data and data["data_source"] not in VALID_SOURCES:
        return jsonify({"error": f"Invalid data_source. Must be one of: {VALID_SOURCES}"}), 400

    new_metric = TrafficMetric(
        bottleneck_id_fk=data["bottleneck_id_fk"],
        timestamp=timestamp,
        congestion_level=congestion,
        average_speed=speed,
        data_source=data.get("data_source", "API"),
    )

    db.session.add(new_metric)
    db.session.commit()

    return jsonify(new_metric.to_json()), 201


# BULK CREATE — POST /traffic/bulk
# For ETL pipeline batch inserts from API polling
@traffic_metric_bp.route("/bulk", methods=["POST"])
def bulk_create_traffic_metrics():
    data = request.get_json()

    if not isinstance(data, list) or len(data) == 0:
        return jsonify({"error": "Provide a non-empty list of traffic metrics"}), 400

    created = []
    errors = []

    for i, item in enumerate(data):
        required = ["bottleneck_id_fk", "timestamp", "congestion_level", "average_speed"]
        missing = [f for f in required if f not in item]
        if missing:
            errors.append({"index": i, "error": f"Missing fields: {missing}"})
            continue

        if not Bottleneck.query.get(item["bottleneck_id_fk"]):
            errors.append({"index": i, "error": f"Bottleneck {item['bottleneck_id_fk']} not found"})
            continue

        timestamp = parse_datetime(item["timestamp"])
        if not timestamp:
            errors.append({"index": i, "error": "Invalid timestamp format"})
            continue

        try:
            congestion = int(item["congestion_level"])
            if not (0 <= congestion <= 100):
                raise ValueError
        except (ValueError, TypeError):
            errors.append({"index": i, "error": "Invalid congestion_level"})
            continue

        try:
            speed = float(item["average_speed"])
            if not (0 <= speed <= 150):
                raise ValueError
        except (ValueError, TypeError):
            errors.append({"index": i, "error": "Invalid average_speed"})
            continue

        if item.get("data_source") and item["data_source"] not in VALID_SOURCES:
            errors.append({"index": i, "error": f"Invalid data_source: {item['data_source']}"})
            continue

        metric = TrafficMetric(
            bottleneck_id_fk=item["bottleneck_id_fk"],
            timestamp=timestamp,
            congestion_level=congestion,
            average_speed=speed,
            data_source=item.get("data_source", "API"),
        )
        db.session.add(metric)
        created.append(i)

    db.session.commit()

    return jsonify({
        "created": len(created),
        "errors": errors,
    }), 207 if errors else 201


# READ ALL — GET /traffic
@traffic_metric_bp.route("/", methods=["GET"])
def get_traffic_metrics():
    metrics = TrafficMetric.query.order_by(TrafficMetric.timestamp.desc()).all()
    return jsonify([m.to_json() for m in metrics]), 200


# READ ONE — GET /traffic/<id>
@traffic_metric_bp.route("/<int:metric_id>", methods=["GET"])
def get_traffic_metric(metric_id):
    metric = TrafficMetric.query.get_or_404(metric_id)
    return jsonify(metric.to_json()), 200


# READ BY BOTTLENECK — GET /traffic/bottleneck/<bottleneck_id>
@traffic_metric_bp.route("/bottleneck/<int:bottleneck_id>", methods=["GET"])
def get_metrics_by_bottleneck(bottleneck_id):
    if not Bottleneck.query.get(bottleneck_id):
        return jsonify({"error": "Bottleneck not found"}), 404

    metrics = TrafficMetric.query.filter_by(
        bottleneck_id_fk=bottleneck_id
    ).order_by(TrafficMetric.timestamp.desc()).all()

    return jsonify([m.to_json() for m in metrics]), 200


# READ LATEST PER BOTTLENECK — GET /traffic/latest
# Returns the most recent metric for each bottleneck
# Primary route for GA to get current traffic snapshot before optimization
@traffic_metric_bp.route("/latest", methods=["GET"])
def get_latest_metrics():
    subquery = db.session.query(
        TrafficMetric.bottleneck_id_fk,
        db.func.max(TrafficMetric.timestamp).label("max_ts")
    ).group_by(TrafficMetric.bottleneck_id_fk).subquery()

    latest = TrafficMetric.query.join(
        subquery,
        db.and_(
            TrafficMetric.bottleneck_id_fk == subquery.c.bottleneck_id_fk,
            TrafficMetric.timestamp == subquery.c.max_ts
        )
    ).all()

    return jsonify([m.to_json() for m in latest]), 200


# READ CONGESTED — GET /traffic/congested?threshold=60
# Returns latest metric per bottleneck above a congestion threshold
# Useful for dashboard map to highlight red/orange bottlenecks
@traffic_metric_bp.route("/congested", methods=["GET"])
def get_congested_bottlenecks():
    try:
        threshold = int(request.args.get("threshold", 60))
        if not (0 <= threshold <= 100):
            raise ValueError
    except (ValueError, TypeError):
        return jsonify({"error": "threshold must be an integer between 0 and 100"}), 400

    subquery = db.session.query(
        TrafficMetric.bottleneck_id_fk,
        db.func.max(TrafficMetric.timestamp).label("max_ts")
    ).group_by(TrafficMetric.bottleneck_id_fk).subquery()

    congested = TrafficMetric.query.join(
        subquery,
        db.and_(
            TrafficMetric.bottleneck_id_fk == subquery.c.bottleneck_id_fk,
            TrafficMetric.timestamp == subquery.c.max_ts
        )
    ).filter(TrafficMetric.congestion_level >= threshold).all()

    return jsonify([m.to_json() for m in congested]), 200


# UPDATE — PUT /traffic/<id>
@traffic_metric_bp.route("/<int:metric_id>", methods=["PUT"])
def update_traffic_metric(metric_id):
    metric = TrafficMetric.query.get_or_404(metric_id)
    data = request.get_json()

    if "congestion_level" in data:
        try:
            congestion = int(data["congestion_level"])
            if not (0 <= congestion <= 100):
                raise ValueError
            metric.congestion_level = congestion
        except (ValueError, TypeError):
            return jsonify({"error": "congestion_level must be an integer between 0 and 100"}), 400

    if "average_speed" in data:
        try:
            speed = float(data["average_speed"])
            if not (0 <= speed <= 150):
                raise ValueError
            metric.average_speed = speed
        except (ValueError, TypeError):
            return jsonify({"error": "average_speed must be a number between 0 and 150"}), 400

    if "data_source" in data and data["data_source"] not in VALID_SOURCES:
        return jsonify({"error": f"Invalid data_source. Must be one of: {VALID_SOURCES}"}), 400

    if "timestamp" in data:
        timestamp = parse_datetime(data["timestamp"])
        if not timestamp:
            return jsonify({"error": "Invalid timestamp format. Use ISO 8601 e.g. 2025-06-15T08:30:00"}), 400
        metric.timestamp = timestamp

    metric.data_source = data.get("data_source", metric.data_source)

    db.session.commit()

    return jsonify(metric.to_json()), 200


# DELETE — DELETE /traffic/<id>
@traffic_metric_bp.route("/<int:metric_id>", methods=["DELETE"])
def delete_traffic_metric(metric_id):
    metric = TrafficMetric.query.get_or_404(metric_id)

    db.session.delete(metric)
    db.session.commit()

    return jsonify({"message": f"TrafficMetric {metric_id} deleted."}), 200


# DELETE OLD METRICS — DELETE /traffic/purge?before=2025-01-01T00:00:00
@traffic_metric_bp.route("/purge", methods=["DELETE"])
def purge_old_metrics():
    before_str = request.args.get("before")
    if not before_str:
        return jsonify({"error": "Provide ?before=<ISO timestamp> query param"}), 400

    before_dt = parse_datetime(before_str)
    if not before_dt:
        return jsonify({"error": "Invalid timestamp format. Use ISO 8601 e.g. 2025-01-01T00:00:00"}), 400

    deleted = TrafficMetric.query.filter(TrafficMetric.timestamp < before_dt).delete()
    db.session.commit()

    return jsonify({"message": f"{deleted} metrics deleted before {before_str}"}), 200