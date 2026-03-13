
from config import app, db

from blueprint.genetic_algorithm.traffic_metric import traffic_metric_bp
from blueprint.genetic_algorithm.incident import incident_bp
from blueprint.genetic_algorithm.weather_reading import weather_reading_bp
from blueprint.genetic_algorithm.bottleneck import bottleneck_bp
from blueprint.genetic_algorithm.officer import officer_bp
from blueprint.genetic_algorithm.assignment import assignment_bp
from blueprint.genetic_algorithm.shift import shift_bp
from blueprint.genetic_algorithm.bottleneck_adjacency import bottleneck_adjacency_bp
from blueprint.genetic_algorithm.road_type import road_type_bp
from blueprint.genetic_algorithm.shift_rule import shift_rule_bp
from blueprint.genetic_algorithm.officer_certification import officer_certification_bp
from blueprint.genetic_algorithm.optimization_run import optimization_run_bp


# ===============Register blueprints===============
app.register_blueprint(optimization_run_bp)
app.register_blueprint(officer_certification_bp)
app.register_blueprint(shift_rule_bp)
app.register_blueprint(road_type_bp)

app.register_blueprint(traffic_metric_bp)
app.register_blueprint(incident_bp)
app.register_blueprint(weather_reading_bp)

app.register_blueprint(bottleneck_adjacency_bp)
app.register_blueprint(bottleneck_bp)

app.register_blueprint(officer_bp)
app.register_blueprint(assignment_bp)
app.register_blueprint(shift_bp)


with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(debug=True)