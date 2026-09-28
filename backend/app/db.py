"""
SQLAlchemy persistence for Evidence Records and Journey State.

See app/config.py for the documented PostGIS -> SQLite substitution
rationale. Road-graph risk factors themselves are held in-memory in the
networkx graph (app/graph.py), rebuilt from the data lake at startup;
this DB stores the *evidence* trail (for explainability / audit) and
live journey/safety state (for RouteGuard + WalkGuard continuity).
"""
from __future__ import annotations

from sqlalchemy import create_engine, Column, String, Float, Boolean, Integer
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import DB_URL

engine = create_engine(DB_URL, connect_args={"check_same_thread": False} if DB_URL.startswith("sqlite") else {})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


class EvidenceRecordORM(Base):
    __tablename__ = "evidence_records"
    id = Column(String, primary_key=True)
    source = Column(String, nullable=False)
    factor = Column(String, nullable=False)
    value = Column(Float, nullable=False)
    raw_value = Column(String, nullable=True)
    confidence = Column(Float, nullable=False, default=0.7)
    timestamp = Column(Float, nullable=False)
    lat = Column(Float, nullable=False)
    lon = Column(Float, nullable=False)
    segment_id = Column(String, nullable=True, index=True)
    description = Column(String, nullable=True)


class JourneyStateORM(Base):
    __tablename__ = "journey_states"
    journey_id = Column(String, primary_key=True)
    origin_lat = Column(Float)
    origin_lon = Column(Float)
    dest_lat = Column(Float)
    dest_lon = Column(Float)
    mode = Column(String)
    expected_route_json = Column(String)  # comma-joined segment ids
    departure_time = Column(Float)
    current_lat = Column(Float, nullable=True)
    current_lon = Column(Float, nullable=True)
    safety_state = Column(String, default="normal")
    level1_since = Column(Float, nullable=True)
    walkguard_active_until = Column(Float, nullable=True)
    companion_status_json = Column(String, nullable=True)  # JSON-serialized CompanionStatus, or null
    transit_status_json = Column(String, nullable=True)  # JSON-serialized TransitStatus, or null
    updated_at = Column(Float)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


def get_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
