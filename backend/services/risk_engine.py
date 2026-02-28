"""
Risk Scoring Engine — Enhanced 5-factor weighted formula.
Final Risk = 0.25×Structural + 0.25×TxnAnomaly + 0.20×OwnershipOverlap + 0.15×CircularPath + 0.15×MLProb
"""
from typing import Dict, List, Optional
from database.neo4j_client import neo4j_client
from services.graph_analytics import analytics_engine


class RiskEngine:
    """Compute composite risk scores for companies."""

    WEIGHTS = {
        "structural_centrality": 0.25,
        "transaction_anomaly": 0.25,
        "ownership_overlap": 0.20,
        "circular_involvement": 0.15,
        "ml_probability": 0.15,
    }

    def compute_risk_score(self, company_id: str, gnn_prob: float = None) -> Dict:
        """Compute composite risk score for a single company."""

        # 1. Structural centrality (degree + betweenness + pagerank)
        features = neo4j_client.run_query("""
            MATCH (c:Company {id: $id})
            RETURN coalesce(c.degree_centrality, 0) AS degree,
                   coalesce(c.betweenness_centrality, 0) AS betweenness,
                   coalesce(c.pagerank, 0) AS pagerank
        """, {"id": company_id})

        if not features:
            return {"company_id": company_id, "composite_score": 0, "risk_band": "Monitor"}

        f = features[0]
        structural = min((f["degree"] * 200 + f["betweenness"] * 500 + f["pagerank"] * 200), 100)

        # 2. Transaction anomaly (circularity + velocity + deviation)
        ci_data = analytics_engine.compute_circularity_index(company_id)
        ci = ci_data.get("circularity_index", 0)
        txn_features = analytics_engine.compute_transaction_features(company_id)
        transaction_anomaly = min(
            (ci * 50 + txn_features.get("transaction_velocity_spike", 0) * 25 +
             txn_features.get("avg_transaction_deviation", 0) * 25), 100
        )

        # 3. Ownership overlap (shell risk)
        shell_data = analytics_engine.compute_shell_risk_score(company_id)
        ownership_overlap = shell_data.get("shell_risk_score", 0) * 100

        # 4. Circular path involvement
        circular_involvement = min(ci_data.get("cycle_count", 0) * 15, 100)

        # 5. ML probability (0-100 scale)
        ml_score = (gnn_prob or 0) * 100

        # Composite
        composite = (
            self.WEIGHTS["structural_centrality"] * structural +
            self.WEIGHTS["transaction_anomaly"] * transaction_anomaly +
            self.WEIGHTS["ownership_overlap"] * ownership_overlap +
            self.WEIGHTS["circular_involvement"] * circular_involvement +
            self.WEIGHTS["ml_probability"] * ml_score
        )
        composite = round(min(composite, 100), 2)

        # Risk band
        if composite >= 71:
            band = "Critical"
        elif composite >= 51:
            band = "High"
        elif composite >= 31:
            band = "Medium"
        else:
            band = "Low"

        return {
            "company_id": company_id,
            "structural_centrality": round(structural, 2),
            "transaction_anomaly": round(transaction_anomaly, 2),
            "ownership_overlap": round(ownership_overlap, 2),
            "circular_involvement": round(circular_involvement, 2),
            "ml_probability": round(ml_score, 2),
            "composite_score": composite,
            "risk_band": band,
            "weights": self.WEIGHTS,
        }

    def compute_all_risk_scores(self, gnn_probs: Dict[str, float] = None) -> List[Dict]:
        """Compute risk scores for all companies."""
        companies = neo4j_client.run_query("MATCH (c:Company) RETURN c.id AS id")
        gnn_probs = gnn_probs or {}
        results = []
        for c in companies:
            cid = c["id"]
            try:
                score = self.compute_risk_score(cid, gnn_probs.get(cid))
                results.append(score)
                neo4j_client.run_write("""
                    MATCH (c:Company {id: $id})
                    SET c.risk_score = $composite_score,
                        c.risk_band = $risk_band
                """, {"id": cid, "composite_score": score["composite_score"],
                      "risk_band": score["risk_band"]})
            except Exception:
                pass
        return results

    @staticmethod
    def get_risk_band(score: float) -> str:
        if score >= 71:
            return "Critical"
        elif score >= 51:
            return "High"
        elif score >= 31:
            return "Medium"
        return "Low"


risk_engine = RiskEngine()
