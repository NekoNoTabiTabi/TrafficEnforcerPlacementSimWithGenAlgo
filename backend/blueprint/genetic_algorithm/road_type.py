
from flask import Blueprint, request, jsonify
from config import db
from model import RoadType, Bottleneck

road_type_bp = Blueprint("road_type", __name__, url_prefix="/roadtypes")


# CREATE — POST /roadtypes
@road_type_bp.route("/", methods=["POST"])
def create_road_type():
    data = request.get_json()

    required = ["road_type", "description"]
    for field in required:
        if field not in data:
            return jsonify({"error": f"Missing required field: {field}"}), 400

    # road_type is the primary key so must be unique
    if RoadType.query.get(data["road_type"]):
        return jsonify({"error": f"RoadType '{data['road_type']}' already exists"}), 409

    new_road_type = RoadType(
        road_type=data["road_type"],
        description=data["description"],
    )

    db.session.add(new_road_type)
    db.session.commit()

    return jsonify(new_road_type.to_json()), 201


# READ ALL — GET /roadtypes
@road_type_bp.route("/", methods=["GET"])
def get_road_types():
    road_types = RoadType.query.all()
    return jsonify([r.to_json() for r in road_types]), 200


# READ ONE — GET /roadtypes/<road_type>
# Note: PK is a string e.g. /roadtypes/arterial
@road_type_bp.route("/<string:road_type>", methods=["GET"])
def get_road_type(road_type):
    road_type_obj = RoadType.query.get_or_404(road_type)
    return jsonify(road_type_obj.to_json()), 200


# READ WITH BOTTLENECKS — GET /roadtypes/<road_type>/bottlenecks
# Returns the road type with all bottlenecks that use it
@road_type_bp.route("/<string:road_type>/bottlenecks", methods=["GET"])
def get_road_type_with_bottlenecks(road_type):
    road_type_obj = RoadType.query.get_or_404(road_type)

    return jsonify({
        **road_type_obj.to_json(),
        "bottlenecks": [b.to_json() for b in road_type_obj.bottlenecks],
        "total_bottlenecks": len(road_type_obj.bottlenecks),
    }), 200


# UPDATE — PUT /roadtypes/<road_type>
# Only description can be updated — road_type is the PK and cannot change
@road_type_bp.route("/<string:road_type>", methods=["PUT"])
def update_road_type(road_type):
    road_type_obj = RoadType.query.get_or_404(road_type)
    data = request.get_json()

    # Block PK changes
    if "road_type" in data and data["road_type"] != road_type:
        return jsonify({"error": "road_type is the primary key and cannot be changed. Delete and recreate instead."}), 400

    if "description" not in data:
        return jsonify({"error": "Nothing to update. Provide a description field."}), 400

    road_type_obj.description = data["description"]

    db.session.commit()

    return jsonify(road_type_obj.to_json()), 200


# DELETE — DELETE /roadtypes/<road_type>
# Blocked if any bottlenecks are using this road type
@road_type_bp.route("/<string:road_type>", methods=["DELETE"])
def delete_road_type(road_type):
    road_type_obj = RoadType.query.get_or_404(road_type)

    # Check if any bottlenecks reference this road type
    linked_bottlenecks = Bottleneck.query.filter_by(road_type_fk=road_type).count()
    if linked_bottlenecks > 0:
        return jsonify({
            "error": f"Cannot delete '{road_type}' — {linked_bottlenecks} bottleneck(s) are using it. Reassign them first.",
            "bottleneck_count": linked_bottlenecks,
        }), 409

    db.session.delete(road_type_obj)
    db.session.commit()

    return jsonify({"message": f"RoadType '{road_type}' deleted."}), 200