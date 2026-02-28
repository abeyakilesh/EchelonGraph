import os
from pydantic import BaseModel

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class Settings(BaseModel):
    # Neo4j
    neo4j_uri: str = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user: str = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password: str = os.getenv("NEO4J_PASSWORD", "echelon_secret")

    # PostgreSQL
    postgres_url: str = os.getenv(
        "POSTGRES_URL",
        "postgresql://echelon:echelon_secret@localhost:5433/echelon_db"
    )

    # ML
    model_path: str = os.getenv("MODEL_PATH", os.path.join(_BASE_DIR, "saved_models"))
    gnn_epochs: int = int(os.getenv("GNN_EPOCHS", "100"))
    gnn_lr: float = float(os.getenv("GNN_LR", "0.01"))

    # Risk thresholds
    circularity_threshold: float = 0.3
    shell_risk_threshold: float = 0.6
    high_risk_threshold: int = 71
    edd_threshold: int = 41


settings = Settings()
