from flask import Blueprint, request, jsonify
from model import Bottleneck
from config import db

bottleneck_bp = Blueprint("bottleneck", __name__, url_prefix="/bottlenecks")


# CREATE — POST /bottlenecks
@bottleneck_bp.route("/", methods=["POST"])
def create_bottleneck():
    data = request.get_json()

    new_bottleneck = Bottleneck(
        name=data["name"],
        location=data["location"],
        priority_level=data["priority_level"],
        road_type_fk=data.get("road_type_fk"),   # optional
        typical_volume=data["typical_volume"],
    )

    db.session.add(new_bottleneck)
    db.session.commit()

    return jsonify(new_bottleneck.to_json()), 201


# READ ALL — GET /bottlenecks
@bottleneck_bp.route("/", methods=["GET"])
def get_bottlenecks():
    bottlenecks = Bottleneck.query.all()
    return jsonify([b.to_json() for b in bottlenecks]), 200


# READ ONE — GET /bottlenecks/<id>
@bottleneck_bp.route("/<int:bottleneck_id>", methods=["GET"])
def get_bottleneck(bottleneck_id):
    bottleneck = Bottleneck.query.get_or_404(bottleneck_id)
    return jsonify(bottleneck.to_json()), 200


# UPDATE — PUT /bottlenecks/<id>
@bottleneck_bp.route("/<int:bottleneck_id>", methods=["PUT"])
def update_bottleneck(bottleneck_id):
    bottleneck = Bottleneck.query.get_or_404(bottleneck_id)
    data = request.get_json()

    bottleneck.name = data.get("name", bottleneck.name)
    bottleneck.location = data.get("location", bottleneck.location)
    bottleneck.priority_level = data.get("priority_level", bottleneck.priority_level)
    bottleneck.road_type_fk = data.get("road_type_fk", bottleneck.road_type_fk)
    bottleneck.typical_volume = data.get("typical_volume", bottleneck.typical_volume)

    db.session.commit()

    return jsonify(bottleneck.to_json()), 200


# DELETE — DELETE /bottlenecks/<id>
@bottleneck_bp.route("/<int:bottleneck_id>", methods=["DELETE"])
def delete_bottleneck(bottleneck_id):
    bottleneck = Bottleneck.query.get_or_404(bottleneck_id)

    db.session.delete(bottleneck)
    db.session.commit()

    return jsonify({"message": f"Bottleneck {bottleneck_id} deleted."}), 200