from config import db
import datetime

class RoadType(db.Model):
    __tablename__ = "roadtype"
 
    road_type = db.Column(db.String(50), primary_key=True)
    description = db.Column(db.String(255), nullable=False)
 
    bottlenecks = db.relationship("Bottleneck", back_populates="road_type_rel")
 
    def to_json(self):
        return {
            "road_type": self.road_type,
            "description": self.description,
        }
 
    def __repr__(self):
        return f"<RoadType {self.road_type}>"
 
 
class ShiftRule(db.Model):
    __tablename__ = "shiftrule"
 
    rank = db.Column(db.String(50), primary_key=True)
    max_consecutive_hours = db.Column(db.Integer, nullable=False)
    break_required = db.Column(db.Boolean, default=True, nullable=False)
 
    def to_json(self):
        return {
            "rank": self.rank,
            "max_consecutive_hours": self.max_consecutive_hours,
            "break_required": self.break_required,
        }
 
    def __repr__(self):
        return f"<ShiftRule {self.rank}>"
 
 
class Bottleneck(db.Model):
    __tablename__ = "bottleneck"
 
    bottleneck_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False)
    location = db.Column(db.String(255), nullable=False)
    priority_level = db.Column(db.Integer, nullable=False)
    road_type_fk = db.Column(db.String(50), db.ForeignKey("roadtype.road_type"), nullable=True)
    typical_volume = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
 
    road_type_rel = db.relationship("RoadType", back_populates="bottlenecks")
    adjacency_from = db.relationship("BottleneckAdjacency", foreign_keys="BottleneckAdjacency.from_bottleneck_id", back_populates="from_bottleneck")
    adjacency_to = db.relationship("BottleneckAdjacency", foreign_keys="BottleneckAdjacency.to_bottleneck_id", back_populates="to_bottleneck")
    traffic_metrics = db.relationship("TrafficMetric", back_populates="bottleneck")
    weather_readings = db.relationship("WeatherReading", back_populates="bottleneck")
    incidents = db.relationship("Incident", back_populates="bottleneck")
    assignments = db.relationship("Assignment", back_populates="bottleneck")
 
    def to_json(self):
        return {
            "bottleneck_id": self.bottleneck_id,
            "name": self.name,
            "location": self.location,
            "priority_level": self.priority_level,
            "road_type_fk": self.road_type_fk,
            "typical_volume": self.typical_volume,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
 
    def __repr__(self):
        return f"<Bottleneck {self.bottleneck_id}: {self.name}>"
 
 
class BottleneckAdjacency(db.Model):
    __tablename__ = "bottleneck_adjacency"
 
    adjacency_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    from_bottleneck_id = db.Column(db.Integer, db.ForeignKey("bottleneck.bottleneck_id"), nullable=False)
    to_bottleneck_id = db.Column(db.Integer, db.ForeignKey("bottleneck.bottleneck_id"), nullable=False)
    influence_weight = db.Column(db.Numeric(5, 2), nullable=False)
 
    from_bottleneck = db.relationship("Bottleneck", foreign_keys=[from_bottleneck_id], back_populates="adjacency_from")
    to_bottleneck = db.relationship("Bottleneck", foreign_keys=[to_bottleneck_id], back_populates="adjacency_to")
 
    __table_args__ = (
        db.UniqueConstraint("from_bottleneck_id", "to_bottleneck_id", name="uq_adjacency_pair"),
    )
 
    def to_json(self):
        return {
            "adjacency_id": self.adjacency_id,
            "from_bottleneck_id": self.from_bottleneck_id,
            "to_bottleneck_id": self.to_bottleneck_id,
            "influence_weight": float(self.influence_weight) if self.influence_weight is not None else None,
        }
 
    def __repr__(self):
        return f"<BottleneckAdjacency {self.from_bottleneck_id} → {self.to_bottleneck_id}>"
 
 
class Officer(db.Model):
    __tablename__ = "officer"
 
    officer_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    badge_number = db.Column(db.String(20), unique=True, nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    rank = db.Column(db.String(50), nullable=False)
    status = db.Column(
        db.Enum("active", "inactive", "on_leave", name="officer_status"),
        default="active",
        nullable=False,
    )
    max_weekly_hours = db.Column(db.Integer, default=40, nullable=False)
 
    certifications = db.relationship("OfficerCertification", back_populates="officer")
    assignments = db.relationship("Assignment", back_populates="officer")
 
    def to_json(self):
        return {
            "officer_id": self.officer_id,
            "badge_number": self.badge_number,
            "full_name": self.full_name,
            "rank": self.rank,
            "status": self.status,
            "max_weekly_hours": self.max_weekly_hours,
        }
 
    def __repr__(self):
        return f"<Officer {self.badge_number}: {self.full_name}>"
 
 
class OfficerCertification(db.Model):
    __tablename__ = "officer_certification"
 
    cert_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    officer_id_fk = db.Column(db.Integer, db.ForeignKey("officer.officer_id"), nullable=False)
    qualification_id = db.Column(db.Integer, nullable=False)
    expiry_date = db.Column(db.Date, nullable=True)
 
    officer = db.relationship("Officer", back_populates="certifications")
 
    def to_json(self):
        return {
            "cert_id": self.cert_id,
            "officer_id_fk": self.officer_id_fk,
            "qualification_id": self.qualification_id,
            "expiry_date": self.expiry_date.isoformat() if self.expiry_date else None,
        }
 
    def __repr__(self):
        return f"<OfficerCertification {self.cert_id} — Officer {self.officer_id_fk}>"
 
 
class Shift(db.Model):
    __tablename__ = "shift"
 
    shift_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    shift_name = db.Column(db.String(50), nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
 
    assignments = db.relationship("Assignment", back_populates="shift")
 
    def to_json(self):
        return {
            "shift_id": self.shift_id,
            "shift_name": self.shift_name,
            "start_time": self.start_time.strftime("%H:%M:%S") if self.start_time else None,
            "end_time": self.end_time.strftime("%H:%M:%S") if self.end_time else None,
        }
 
    def __repr__(self):
        return f"<Shift {self.shift_name} ({self.start_time}–{self.end_time})>"
 
 
class WeatherReading(db.Model):
    __tablename__ = "weatherreading"
 
    reading_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    rainfall_mm = db.Column(db.Numeric(6, 2), nullable=False)
    bottleneck_id_fk = db.Column(db.Integer, db.ForeignKey("bottleneck.bottleneck_id"), nullable=True)
    timestamp = db.Column(db.DateTime, nullable=False)
    flood_warning = db.Column(db.Boolean, default=False, nullable=False)
    rainfall_intensity = db.Column(
        db.Enum("none", "light", "moderate", "heavy", name="rainfall_intensity"),
        default="none",
        nullable=False,
    )
 
    bottleneck = db.relationship("Bottleneck", back_populates="weather_readings")
 
    def to_json(self):
        return {
            "reading_id": self.reading_id,
            "rainfall_mm": float(self.rainfall_mm) if self.rainfall_mm is not None else None,
            "bottleneck_id_fk": self.bottleneck_id_fk,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "flood_warning": self.flood_warning,
            "rainfall_intensity": self.rainfall_intensity,
        }
 
    def __repr__(self):
        return f"<WeatherReading {self.reading_id} @ {self.timestamp}>"
 
 
class TrafficMetric(db.Model):
    __tablename__ = "trafficmetric"
 
    metric_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    bottleneck_id_fk = db.Column(db.Integer, db.ForeignKey("bottleneck.bottleneck_id"), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False)
    congestion_level = db.Column(db.Integer, nullable=False)
    average_speed = db.Column(db.Numeric(5, 2), nullable=False)
    data_source = db.Column(
        db.Enum("API", "manual", name="data_source"),
        default="API",
        nullable=False,
    )
 
    bottleneck = db.relationship("Bottleneck", back_populates="traffic_metrics")
 
    def to_json(self):
        return {
            "metric_id": self.metric_id,
            "bottleneck_id_fk": self.bottleneck_id_fk,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "congestion_level": self.congestion_level,
            "average_speed": float(self.average_speed) if self.average_speed is not None else None,
            "data_source": self.data_source,
        }
 
    def __repr__(self):
        return f"<TrafficMetric {self.metric_id} — Bottleneck {self.bottleneck_id_fk}>"
 
 
class Incident(db.Model):
    __tablename__ = "incident"
 
    incident_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    bottleneck_id_fk = db.Column(db.Integer, db.ForeignKey("bottleneck.bottleneck_id"), nullable=True)
    report_time = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    severity = db.Column(
        db.Enum("critical", "major", "minor", "informational", name="incident_severity"),
        nullable=False,
    )
    status = db.Column(
        db.Enum("active", "resolved", name="incident_status"),
        default="active",
        nullable=False,
    )
 
    bottleneck = db.relationship("Bottleneck", back_populates="incidents")
 
    def to_json(self):
        return {
            "incident_id": self.incident_id,
            "bottleneck_id_fk": self.bottleneck_id_fk,
            "report_time": self.report_time.isoformat() if self.report_time else None,
            "severity": self.severity,
            "status": self.status,
        }
 
    def __repr__(self):
        return f"<Incident {self.incident_id} ({self.severity})>"
 
 
class OptimizationRun(db.Model):
    __tablename__ = "optimizationrun"
 
    ga_run_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    input_data_hash = db.Column(db.String(255), nullable=False)
    run_timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    best_fitness = db.Column(db.Numeric(10, 4), nullable=False)
    convergence_gen = db.Column(db.Integer, nullable=False)
 
    assignments = db.relationship("Assignment", back_populates="ga_run")
 
    def to_json(self):
        return {
            "ga_run_id": self.ga_run_id,
            "input_data_hash": self.input_data_hash,
            "run_timestamp": self.run_timestamp.isoformat() if self.run_timestamp else None,
            "best_fitness": float(self.best_fitness) if self.best_fitness is not None else None,
            "convergence_gen": self.convergence_gen,
        }
 
    def __repr__(self):
        return f"<OptimizationRun {self.ga_run_id} — fitness {self.best_fitness}>"
 
 
class Assignment(db.Model):
    __tablename__ = "assignment"
 
    assignment_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    officer_id_fk = db.Column(db.Integer, db.ForeignKey("officer.officer_id"), nullable=False)
    bottleneck_id_fk = db.Column(db.Integer, db.ForeignKey("bottleneck.bottleneck_id"), nullable=False)
    ga_run_id_fk = db.Column(db.Integer, db.ForeignKey("optimizationrun.ga_run_id"), nullable=True)
    shift_id_fk = db.Column(db.Integer, db.ForeignKey("shift.shift_id"), nullable=False)
    assignment_date = db.Column(db.Date, nullable=False)
    status = db.Column(
        db.Enum("planned", "active", "completed", "cancelled", name="assignment_status"),
        default="planned",
        nullable=False,
    )
 
    officer = db.relationship("Officer", back_populates="assignments")
    bottleneck = db.relationship("Bottleneck", back_populates="assignments")
    ga_run = db.relationship("OptimizationRun", back_populates="assignments")
    shift = db.relationship("Shift", back_populates="assignments")
 
    def to_json(self):
        return {
            "assignment_id": self.assignment_id,
            "officer_id_fk": self.officer_id_fk,
            "bottleneck_id_fk": self.bottleneck_id_fk,
            "ga_run_id_fk": self.ga_run_id_fk,
            "shift_id_fk": self.shift_id_fk,
            "assignment_date": self.assignment_date.isoformat() if self.assignment_date else None,
            "status": self.status,
        }
 
    def __repr__(self):
        return f"<Assignment {self.assignment_id} — Officer {self.officer_id_fk} @ Bottleneck {self.bottleneck_id_fk}>"
 