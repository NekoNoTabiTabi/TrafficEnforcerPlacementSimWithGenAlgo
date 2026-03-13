from flask import Blueprint, request, jsonify
from config import db
from model import WeatherReading, Bottleneck
from datetime import datetime

weather_reading_bp = Blueprint("weather_reading", __name__, url_prefix="/weather")


# Helper to parse datetime strings e.g. "2025-06-15T08:30:00"
def parse_datetime(dt_str):
    try:
        return datetime.fromisoformat(dt_str)
    except (ValueError, TypeError):
        return None


VALID_INTENSITIES = ["none", "light", "moderate", "heavy"]


# CREATE ONE — POST /weather
@weather_reading_bp.route("/", methods=["POST"])
def create_weather_reading():
    data = request.get_json()

    # Validate required fields
    required = ["rainfall_mm", "timestamp", "rainfall_intensity"]
    for field in required:
        if field not in data:
            return jsonify({"error": f"Missing required field: {field}"}), 400

    # Validate intensity
    if data["rainfall_intensity"] not in VALID_INTENSITIES:
        return jsonify({"error": f"Invalid intensity. Must be one of: {VALID_INTENSITIES}"}), 400

    # Validate rainfall_mm is non-negative
    try:
        rainfall = float(data["rainfall_mm"])
        if rainfall < 0:
            raise ValueError
    except (ValueError, TypeError):
        return jsonify({"error": "rainfall_mm must be a non-negative number"}), 400

    # Validate bottleneck exists if provided
    if data.get("bottleneck_id_fk") and not Bottleneck.query.get(data["bottleneck_id_fk"]):
        return jsonify({"error": "Bottleneck not found"}), 404

    timestamp = parse_datetime(data["timestamp"])
    if not timestamp:
        return jsonify({"error": "Invalid timestamp format. Use ISO 8601 e.g. 2025-06-15T08:30:00"}), 400

    new_reading = WeatherReading(
        rainfall_mm=rainfall,
        bottleneck_id_fk=data.get("bottleneck_id_fk"),   # optional
        timestamp=timestamp,
        flood_warning=data.get("flood_warning", False),
        rainfall_intensity=data["rainfall_intensity"],
    )

    db.session.add(new_reading)
    db.session.commit()

    return jsonify(new_reading.to_json()), 201


# BULK CREATE — POST /weather/bulk
# For ETL pipeline to insert multiple readings in one request
@weather_reading_bp.route("/bulk", methods=["POST"])
def bulk_create_weather_readings():
    data = request.get_json()

    if not isinstance(data, list) or len(data) == 0:
        return jsonify({"error": "Provide a non-empty list of weather readings"}), 400

    created = []
    errors = []

    for i, item in enumerate(data):
        # Validate each item
        required = ["rainfall_mm", "timestamp", "rainfall_intensity"]
        missing = [f for f in required if f not in item]
        if missing:
            errors.append({"index": i, "error": f"Missing fields: {missing}"})
            continue

        if item["rainfall_intensity"] not in VALID_INTENSITIES:
            errors.append({"index": i, "error": f"Invalid intensity: {item['rainfall_intensity']}"})
            continue

        timestamp = parse_datetime(item["timestamp"])
        if not timestamp:
            errors.append({"index": i, "error": "Invalid timestamp format"})
            continue

        try:
            rainfall = float(item["rainfall_mm"])
            if rainfall < 0:
                raise ValueError
        except (ValueError, TypeError):
            errors.append({"index": i, "error": "Invalid rainfall_mm"})
            continue

        reading = WeatherReading(
            rainfall_mm=rainfall,
            bottleneck_id_fk=item.get("bottleneck_id_fk"),
            timestamp=timestamp,
            flood_warning=item.get("flood_warning", False),
            rainfall_intensity=item["rainfall_intensity"],
        )
        db.session.add(reading)
        created.append(i)

    db.session.commit()

    return jsonify({
        "created": len(created),
        "errors": errors,
    }), 207 if errors else 201


# READ ALL — GET /weather
@weather_reading_bp.route("/", methods=["GET"])
def get_weather_readings():
    readings = WeatherReading.query.order_by(WeatherReading.timestamp.desc()).all()
    return jsonify([r.to_json() for r in readings]), 200


# READ ONE — GET /weather/<id>
@weather_reading_bp.route("/<int:reading_id>", methods=["GET"])
def get_weather_reading(reading_id):
    reading = WeatherReading.query.get_or_404(reading_id)
    return jsonify(reading.to_json()), 200


# READ BY BOTTLENECK — GET /weather/bottleneck/<bottleneck_id>
@weather_reading_bp.route("/bottleneck/<int:bottleneck_id>", methods=["GET"])
def get_readings_by_bottleneck(bottleneck_id):
    if not Bottleneck.query.get(bottleneck_id):
        return jsonify({"error": "Bottleneck not found"}), 404

    readings = WeatherReading.query.filter_by(
        bottleneck_id_fk=bottleneck_id
    ).order_by(WeatherReading.timestamp.desc()).all()

    return jsonify([r.to_json() for r in readings]), 200


# READ ACTIVE FLOOD WARNINGS — GET /weather/floods
# Returns all readings where flood_warning is True
@weather_reading_bp.route("/floods", methods=["GET"])
def get_flood_warnings():
    readings = WeatherReading.query.filter_by(
        flood_warning=True
    ).order_by(WeatherReading.timestamp.desc()).all()

    return jsonify([r.to_json() for r in readings]), 200


# READ LATEST PER BOTTLENECK — GET /weather/latest
# Returns the most recent reading for each bottleneck
# Useful for the GA to get current weather snapshot
@weather_reading_bp.route("/latest", methods=["GET"])
def get_latest_readings():
    # Subquery to get max timestamp per bottleneck
    subquery = db.session.query(
        WeatherReading.bottleneck_id_fk,
        db.func.max(WeatherReading.timestamp).label("max_ts")
    ).group_by(WeatherReading.bottleneck_id_fk).subquery()

    latest = WeatherReading.query.join(
        subquery,
        db.and_(
            WeatherReading.bottleneck_id_fk == subquery.c.bottleneck_id_fk,
            WeatherReading.timestamp == subquery.c.max_ts
        )
    ).all()

    return jsonify([r.to_json() for r in latest]), 200


# UPDATE — PUT /weather/<id>
@weather_reading_bp.route("/<int:reading_id>", methods=["PUT"])
def update_weather_reading(reading_id):
    reading = WeatherReading.query.get_or_404(reading_id)
    data = request.get_json()

    if "rainfall_intensity" in data and data["rainfall_intensity"] not in VALID_INTENSITIES:
        return jsonify({"error": f"Invalid intensity. Must be one of: {VALID_INTENSITIES}"}), 400

    if "rainfall_mm" in data:
        try:
            rainfall = float(data["rainfall_mm"])
            if rainfall < 0:
                raise ValueError
            reading.rainfall_mm = rainfall
        except (ValueError, TypeError):
            return jsonify({"error": "rainfall_mm must be a non-negative number"}), 400

    if "timestamp" in data:
        timestamp = parse_datetime(data["timestamp"])
        if not timestamp:
            return jsonify({"error": "Invalid timestamp format. Use ISO 8601 e.g. 2025-06-15T08:30:00"}), 400
        reading.timestamp = timestamp

    reading.bottleneck_id_fk = data.get("bottleneck_id_fk", reading.bottleneck_id_fk)
    reading.flood_warning = data.get("flood_warning", reading.flood_warning)
    reading.rainfall_intensity = data.get("rainfall_intensity", reading.rainfall_intensity)

    db.session.commit()

    return jsonify(reading.to_json()), 200


# DELETE — DELETE /weather/<id>
@weather_reading_bp.route("/<int:reading_id>", methods=["DELETE"])
def delete_weather_reading(reading_id):
    reading = WeatherReading.query.get_or_404(reading_id)

    db.session.delete(reading)
    db.session.commit()

    return jsonify({"message": f"WeatherReading {reading_id} deleted."}), 200


# DELETE OLD READINGS — DELETE /weather/purge?before=2025-01-01T00:00:00
# Cleans up stale data older than a given timestamp
@weather_reading_bp.route("/purge", methods=["DELETE"])
def purge_old_readings():
    before_str = request.args.get("before")
    if not before_str:
        return jsonify({"error": "Provide ?before=<ISO timestamp> query param"}), 400

    before_dt = parse_datetime(before_str)
    if not before_dt:
        return jsonify({"error": "Invalid timestamp format. Use ISO 8601 e.g. 2025-01-01T00:00:00"}), 400

    deleted = WeatherReading.query.filter(WeatherReading.timestamp < before_dt).delete()
    db.session.commit()

    return jsonify({"message": f"{deleted} readings deleted before {before_str}"}), 200