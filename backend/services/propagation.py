"""
Fraud Propagation Engine
- Decay-based risk propagation from confirmed fraud nodes
- Supply chain contagion simulation
"""
import math
from typing import Dict, List
from database.neo4j_client import neo4j_client


class PropagationEngine:
    """Simulate fraud risk propagation through the supply chain."""

    def propagate_fraud(self, company_id: str, confirmed_risk: float = 100.0, max_hops: int = 5) -> Dict:
        """
        Propagate risk from a confirmed fraud company to neighbors.
        Risk_boost = ConfirmedRisk × e^(-hop_distance)
        """
        # Mark as confirmed fraud
        neo4j_client.run_write(
            """
            MATCH (c:Company {id: $id})
            SET c.is_confirmed_fraud = true, c.risk_score = 100, c.risk_band = 'Investigate'
            """,
            {"id": company_id}
        )

        affected = []

        for hop in range(1, max_hops + 1):
            risk_boost = confirmed_risk * math.exp(-hop)

            if risk_boost < 1:
                break

            neighbors = neo4j_client.run_query(
                f"""
                MATCH (start:Company {{id: $id}})-[:SUPPLIES_TO|SHARES_DIRECTOR*{hop}]-(target:Company)
                WHERE target.id <> $id
                RETURN DISTINCT target.id AS id, target.name AS name,
                       coalesce(target.risk_score, 0) AS current_risk
                """,
                {"id": company_id}
            )

            for n in neighbors:
                new_risk = min(n["current_risk"] + risk_boost, 100)
                band = "Investigate" if new_risk >= 71 else ("EDD" if new_risk >= 41 else "Monitor")

                neo4j_client.run_write(
                    """
                    MATCH (c:Company {id: $id})
                    SET c.risk_score = $new_risk, c.risk_band = $band
                    """,
                    {"id": n["id"], "new_risk": round(new_risk, 2), "band": band}
                )

                affected.append({
                    "id": n["id"],
                    "name": n["name"],
                    "hop_distance": hop,
                    "risk_boost": round(risk_boost, 2),
                    "previous_risk": round(n["current_risk"], 2),
                    "new_risk": round(new_risk, 2),
                    "risk_band": band,
                })

        return {
            "source_company_id": company_id,
            "confirmed_risk": confirmed_risk,
            "max_hops_reached": max_hops,
            "affected_companies": affected,
            "total_affected": len(affected),
            "total_risk_increase": round(sum(a["risk_boost"] for a in affected), 2),
        }

    def simulate_removal(self, company_id: str) -> Dict:
        """
        Simulate what happens if a node is removed from the supply chain.
        Identify downstream entities that would be affected.
        """
        # Get direct and indirect dependents
        downstream = neo4j_client.run_query(
            """
            MATCH path = (c:Company {id: $id})-[:SUPPLIES_TO*1..4]->(downstream:Company)
            WITH downstream, length(path) AS distance
            RETURN DISTINCT downstream.id AS id, downstream.name AS name,
                   min(distance) AS min_distance,
                   coalesce(downstream.risk_score, 0) AS current_risk,
                   downstream.annual_revenue AS revenue
            ORDER BY min_distance
            """,
            {"id": company_id}
        )

        # Check if any downstream nodes have single supplier (this company)
        critical_impacts = []
        for d in downstream:
            suppliers = neo4j_client.run_query(
                """
                MATCH (supplier:Company)-[:SUPPLIES_TO]->(c:Company {id: $id})
                RETURN count(supplier) AS supplier_count
                """,
                {"id": d["id"]}
            )
            supplier_count = suppliers[0]["supplier_count"] if suppliers else 0

            impact_severity = "CRITICAL" if supplier_count <= 1 else (
                "HIGH" if supplier_count <= 3 else "MODERATE"
            )

            critical_impacts.append({
                **d,
                "supplier_count": supplier_count,
                "impact_severity": impact_severity,
                "estimated_revenue_impact": d.get("revenue", 0) * (1 / max(supplier_count, 1)),
            })

        return {
            "removed_company_id": company_id,
            "downstream_affected": critical_impacts,
            "total_downstream": len(downstream),
            "critical_count": sum(1 for c in critical_impacts if c["impact_severity"] == "CRITICAL"),
            "total_revenue_at_risk": sum(c.get("estimated_revenue_impact", 0) for c in critical_impacts),
        }


propagation_engine = PropagationEngine()
