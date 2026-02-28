"""SQLAlchemy ORM models for PostgreSQL tables."""
from sqlalchemy import Column, String, Float, Integer, Boolean, Date, DateTime, ARRAY, Text, ForeignKey
from sqlalchemy.sql import func
from database.postgres_client import Base


class CompanyDB(Base):
    __tablename__ = "companies"

    id = Column(String(64), primary_key=True)
    name = Column(String(255), nullable=False)
    incorporation_date = Column(Date)
    industry = Column(String(128))
    annual_revenue = Column(Float, default=0)
    employee_count = Column(Integer, default=0)
    is_shell_suspect = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())


class CompanyFeatureDB(Base):
    __tablename__ = "company_features"

    company_id = Column(String(64), ForeignKey("companies.id"), primary_key=True)
    degree_centrality = Column(Float, default=0)
    betweenness_centrality = Column(Float, default=0)
    pagerank = Column(Float, default=0)
    clustering_coefficient = Column(Float, default=0)
    community_id = Column(Integer, default=-1)
    avg_transaction_deviation = Column(Float, default=0)
    transaction_velocity_spike = Column(Float, default=0)
    director_overlap_ratio = Column(Float, default=0)
    circularity_index = Column(Float, default=0)
    shell_risk_score = Column(Float, default=0)
    cycle_count = Column(Integer, default=0)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class RiskScoreDB(Base):
    __tablename__ = "risk_scores"

    company_id = Column(String(64), ForeignKey("companies.id"), primary_key=True)
    network_risk = Column(Float, default=0)
    transaction_anomaly = Column(Float, default=0)
    identity_overlap = Column(Float, default=0)
    gnn_probability = Column(Float, default=0)
    compliance_flags = Column(Float, default=0)
    composite_score = Column(Float, default=0)
    risk_band = Column(String(20), default="Monitor")
    is_confirmed_fraud = Column(Boolean, default=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class FraudExplanationDB(Base):
    __tablename__ = "fraud_explanations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(String(64), ForeignKey("companies.id"))
    feature_name = Column(String(128))
    feature_value = Column(Float)
    shap_value = Column(Float)
    rank = Column(Integer)
    created_at = Column(DateTime, server_default=func.now())


class CircularPathDB(Base):
    __tablename__ = "circular_paths"

    id = Column(Integer, primary_key=True, autoincrement=True)
    origin_company_id = Column(String(64), ForeignKey("companies.id"))
    path_nodes = Column(ARRAY(Text))
    cycle_length = Column(Integer)
    total_amount = Column(Float)
    detected_at = Column(DateTime, server_default=func.now())
