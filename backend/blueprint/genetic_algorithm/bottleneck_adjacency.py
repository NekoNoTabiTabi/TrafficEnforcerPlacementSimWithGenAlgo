from flask import Blueprint, request, jsonify
from config import db
from model import BottleneckAdjacency, Bottleneck

bottleneck_adjacency_bp = Blueprint("bottleneck_adjacency", __name__, url_prefix="/adjacencies")


# CREATE — POST /adjacencies
@bottleneck_adjacency_bp.route("/", methods=["POST"])
def create_adjacency():
    data = request.get_json()

    # Validate required fields
    required = ["from_bottleneck_id", "to_bottleneck_id", "influence_weight"]
    for field in required:
        if field not in data:
            return jsonify({"error": f"Missing required field: {field}"}), 400

    # Prevent self-referencing adjacency
    if data["from_bottleneck_id"] == data["to_bottleneck_id"]:
        return jsonify({"error": "A bottleneck cannot be adjacent to itself"}), 400

    # Validate influence_weight range (0.0 to 1.0)
    try:
        weight = float(data["influence_weight"])
        if not (0.0 <= weight <= 1.0):
            raise ValueError
    except (ValueError, TypeError):
        return jsonify({"error": "influence_weight must be a number between 0.0 and 1.0"}), 400

    # Validate both bottlenecks exist
    if not Bottleneck.query.get(data["from_bottleneck_id"]):
        return jsonify({"error": f"Bottleneck {data['from_bottleneck_id']} (from) not found"}), 404
    if not Bottleneck.query.get(data["to_bottleneck_id"]):
        return jsonify({"error": f"Bottleneck {data['to_bottleneck_id']} (to) not found"}), 404

    # Check for duplicate adjacency pair
    existing = BottleneckAdjacency.query.filter_by(
        from_bottleneck_id=data["from_bottleneck_id"],
        to_bottleneck_id=data["to_bottleneck_id"]
    ).first()
    if existing:
        return jsonify({"error": "This adjacency pair already exists"}), 409

    new_adjacency = BottleneckAdjacency(
        from_bottleneck_id=data["from_bottleneck_id"],
        to_bottleneck_id=data["to_bottleneck_id"],
        influence_weight=weight,
    )

    db.session.add(new_adjacency)
    db.session.commit()

    return jsonify(new_adjacency.to_json()), 201


# READ ALL — GET /adjacencies
@bottleneck_adjacency_bp.route("/", methods=["GET"])
def get_adjacencies():
    adjacencies = BottleneckAdjacency.query.all()
    return jsonify([a.to_json() for a in adjacencies]), 200


# READ ONE — GET /adjacencies/<id>
@bottleneck_adjacency_bp.route("/<int:adjacency_id>", methods=["GET"])
def get_adjacency(adjacency_id):
    adjacency = BottleneckAdjacency.query.get_or_404(adjacency_id)
    return jsonify(adjacency.to_json()), 200


# READ BY BOTTLENECK — GET /adjacencies/bottleneck/<bottleneck_id>
# Returns all adjacencies where this bottleneck is the source (from_node)
@bottleneck_adjacency_bp.route("/bottleneck/<int:bottleneck_id>", methods=["GET"])
def get_adjacencies_by_bottleneck(bottleneck_id):
    if not Bottleneck.query.get(bottleneck_id):
        return jsonify({"error": "Bottleneck not found"}), 404

    outgoing = BottleneckAdjacency.query.filter_by(from_bottleneck_id=bottleneck_id).all()
    incoming = BottleneckAdjacency.query.filter_by(to_bottleneck_id=bottleneck_id).all()

    return jsonify({
        "bottleneck_id": bottleneck_id,
        "outgoing": [a.to_json() for a in outgoing],
        "incoming": [a.to_json() for a in incoming],
    }), 200


# UPDATE — PUT /adjacencies/<id>
# Only influence_weight can be updated — changing the pair itself
# should be a delete + create instead
@bottleneck_adjacency_bp.route("/<int:adjacency_id>", methods=["PUT"])
def update_adjacency(adjacency_id):
    adjacency = BottleneckAdjacency.query.get_or_404(adjacency_id)
    data = request.get_json()

    if "influence_weight" not in data:
        return jsonify({"error": "Only influence_weight can be updated"}), 400

    try:
        weight = float(data["influence_weight"])
        if not (0.0 <= weight <= 1.0):
            raise ValueError
    except (ValueError, TypeError):
        return jsonify({"error": "influence_weight must be a number between 0.0 and 1.0"}), 400

    adjacency.influence_weight = weight

    db.session.commit()

    return jsonify(adjacency.to_json()), 200


# DELETE — DELETE /adjacencies/<id>
@bottleneck_adjacency_bp.route("/<int:adjacency_id>", methods=["DELETE"])
def delete_adjacency(adjacency_id):
    adjacency = BottleneckAdjacency.query.get_or_404(adjacency_id)

    db.session.delete(adjacency)
    db.session.commit()

    return jsonify({"message": f"Adjacency {adjacency_id} deleted."}), 200


# DELETE BY PAIR — DELETE /adjacencies/pair?from=1&to=2
# Useful when you know the bottleneck IDs but not the adjacency_id
@bottleneck_adjacency_bp.route("/pair", methods=["DELETE"])
def delete_adjacency_by_pair():
    from_id = request.args.get("from", type=int)
    to_id = request.args.get("to", type=int)

    if not from_id or not to_id:
        return jsonify({"error": "Provide both ?from=<id>&to=<id> query params"}), 400

    adjacency = BottleneckAdjacency.query.filter_by(
        from_bottleneck_id=from_id,
        to_bottleneck_id=to_id
    ).first_or_404()

    db.session.delete(adjacency)
    db.session.commit()

    return jsonify({"message": f"Adjacency from {from_id} to {to_id} deleted."}), 200