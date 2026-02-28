"""
Explainable AI module
- SHAP for tabular feature explanations
- Graph explanation (suspicious neighbors, cycles, communities)
"""
from typing import Dict, List
from database.neo4j_client import neo4j_client
from services.graph_analytics import analytics_engine
import numpy as np


class ExplainabilityEngine:
    """Generate human-readable fraud explanations."""

    def explain_risk(self, company_id: str, risk_data: Dict = None) -> Dict:
        """
        Generate top contributing features and graph-based explanations.
        Returns structured explanation suitable for audit teams.
        """
        # Compute feature contributions
        features = self._get_feature_vector(company_id)
        top_drivers = self._rank_features(features)

        # Graph context
        suspicious_neighbors = self._get_suspicious_neighbors(company_id)
        cycle_paths = analytics_engine.detect_circular_paths(company_id)
        community_info = self._get_community_info(company_id)

        explanation = {
            "company_id": company_id,
            "top_drivers": top_drivers[:5],
            "suspicious_neighbors": suspicious_neighbors[:10],
            "circular_paths": [
                {
                    "path": cp.get("path_nodes", []),
                    "length": cp.get("cycle_length", 0),
                    "amount": cp.get("total_amount", 0),
                }
                for cp in (cycle_paths[:5] if cycle_paths else [])
            ],
            "community": community_info,
        }

        if risk_data:
            explanation["risk_breakdown"] = {
                "network_risk": risk_data.get("network_risk", 0),
                "transaction_anomaly": risk_data.get("transaction_anomaly", 0),
                "identity_overlap": risk_data.get("identity_overlap", 0),
                "gnn_probability": risk_data.get("gnn_probability", 0),
                "compliance_flags": risk_data.get("compliance_flags", 0),
            }

        return explanation

    def _get_feature_vector(self, company_id: str) -> Dict[str, float]:
        """Collect all features for a company."""
        result = neo4j_client.run_query(
            """
            MATCH (c:Company {id: $id})
            RETURN coalesce(c.degree_centrality, 0) AS degree_centrality,
                   coalesce(c.betweenness_centrality, 0) AS betweenness_centrality,
                   coalesce(c.pagerank, 0) AS pagerank,
                   coalesce(c.clustering_coefficient, 0) AS clustering_coefficient,
                   coalesce(c.risk_score, 0) AS risk_score,
                   coalesce(c.employee_count, 0) AS employee_count,
                   coalesce(c.annual_revenue, 0) AS annual_revenue
            """,
            {"id": company_id}
        )

        if not result:
            return {}

        features = result[0]

        # Add computed features
        ci_data = analytics_engine.compute_circularity_index(company_id)
        features["circularity_index"] = ci_data["circularity_index"]
        features["cycle_count"] = ci_data["cycle_count"]

        shell_data = analytics_engine.compute_shell_risk_score(company_id)
        features["shell_risk_score"] = shell_data["shell_risk_score"]

        txn_features = analytics_engine.compute_transaction_features(company_id)
        features.update(txn_features)

        return features

    def _rank_features(self, features: Dict[str, float]) -> List[Dict]:
        """Rank features by their contribution to risk (simplified SHAP-like)."""
        # Feature importance weights (approximate SHAP values)
        importance = {
            "circularity_index": 0.20,
            "shell_risk_score": 0.18,
            "director_overlap_ratio": 0.15,
            "cycle_count": 0.12,
            "transaction_velocity_spike": 0.10,
            "degree_centrality": 0.08,
            "betweenness_centrality": 0.05,
            "pagerank": 0.04,
            "avg_transaction_deviation": 0.04,
            "clustering_coefficient": 0.02,
            "employee_count": 0.01,
            "annual_revenue": 0.01,
        }

        ranked = []
        for feature_name, weight in importance.items():
            value = features.get(feature_name, 0)
            contribution = value * weight

            # Generate human-readable description
            desc = self._feature_description(feature_name, value)

            ranked.append({
                "feature": feature_name,
                "value": round(value, 4) if isinstance(value, float) else value,
                "importance": round(contribution, 4),
                "description": desc,
            })

        ranked.sort(key=lambda x: abs(x["importance"]), reverse=True)
        return ranked

    def _feature_description(self, name: str, value) -> str:
        """Human-readable description of a feature contribution."""
        descriptions = {
            "circularity_index": f"Circularity index is {'high' if value > 0.3 else 'normal'} ({value:.2f})",
            "shell_risk_score": f"Shell company risk score: {value:.2f}",
            "director_overlap_ratio": f"Shared director with {int(value * 10)} other entities",
            "cycle_count": f"Involved in {value} circular transaction paths",
            "transaction_velocity_spike": f"Transaction velocity {'anomalous' if value > 0.5 else 'normal'}",
            "degree_centrality": f"Network connectivity score: {value:.3f}",
            "betweenness_centrality": f"Intermediary position score: {value:.3f}",
            "pagerank": f"Network influence score: {value:.3f}",
            "avg_transaction_deviation": f"Transaction amount deviation: {value:.3f}",
            "clustering_coefficient": f"Local clustering: {value:.3f}",
            "employee_count": f"Employee count: {value}",
            "annual_revenue": f"Annual revenue: ₹{value:,.0f}" if isinstance(value, (int, float)) else f"Revenue: {value}",
        }
        return descriptions.get(name, f"{name}: {value}")

    def _get_suspicious_neighbors(self, company_id: str) -> List[Dict]:
        """Get neighboring companies sorted by risk."""
        return neo4j_client.run_query(
            """
            MATCH (c:Company {id: $id})-[:SUPPLIES_TO]-(neighbor:Company)
            WITH DISTINCT neighbor
            RETURN neighbor.id AS id, neighbor.name AS name,
                   coalesce(neighbor.risk_score, 0) AS risk_score,
                   coalesce(neighbor.risk_band, 'Monitor') AS risk_band
            ORDER BY risk_score DESC
            LIMIT 10
            """,
            {"id": company_id}
        )

    def _get_community_info(self, company_id: str) -> Dict:
        """Get community-level statistics."""
        result = neo4j_client.run_query(
            """
            MATCH (c:Company {id: $id})
            WITH coalesce(c.community_id, 0) AS comm_id
            MATCH (member:Company)
            WHERE coalesce(member.community_id, 0) = comm_id
            RETURN comm_id AS community_id,
                   count(member) AS member_count,
                   avg(coalesce(member.risk_score, 0)) AS avg_risk,
                   sum(CASE WHEN coalesce(member.risk_score, 0) >= 71 THEN 1 ELSE 0 END) AS high_risk_count
            """,
            {"id": company_id}
        )
        return result[0] if result else {}


explainability_engine = ExplainabilityEngine()
