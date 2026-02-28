"""
Advanced Fraud Signal Detection Engine.
Detects 6 structural and behavioral fraud signals from the graph.
"""
from typing import Dict, List
from database.neo4j_client import neo4j_client


class FraudSignalEngine:
    """Compute advanced fraud signals for companies."""

    def compute_all_signals(self, company_id: str) -> Dict:
        """Compute all 6 fraud signals for a company."""
        signals = []
        total_score = 0

        # 1. High betweenness centrality spike
        bc = self._betweenness_spike(company_id)
        signals.append(bc)
        total_score += bc["score"]

        # 2. High clustering coefficient
        cc = self._clustering_anomaly(company_id)
        signals.append(cc)
        total_score += cc["score"]

        # 3. Repeated round-number transactions
        rn = self._round_number_transactions(company_id)
        signals.append(rn)
        total_score += rn["score"]

        # 4. Same-day multi-hop transfers
        sd = self._same_day_multihop(company_id)
        signals.append(sd)
        total_score += sd["score"]

        # 5. Director connected to multiple high-risk clusters
        dc = self._director_multi_cluster(company_id)
        signals.append(dc)
        total_score += dc["score"]

        # 6. Sudden transaction volume surge
        vs = self._volume_surge(company_id)
        signals.append(vs)
        total_score += vs["score"]

        return {
            "company_id": company_id,
            "signals": signals,
            "total_signal_score": round(total_score, 2),
            "signal_count": sum(1 for s in signals if s["triggered"]),
            "max_possible": 600,
        }

    def _betweenness_spike(self, company_id: str) -> Dict:
        result = neo4j_client.run_query(
            """
            MATCH (c:Company {id: $id})
            WITH c, coalesce(c.betweenness_centrality, 0) AS bc
            MATCH (all:Company)
            WITH c, bc, avg(coalesce(all.betweenness_centrality, 0)) AS avg_bc,
                 stDev(coalesce(all.betweenness_centrality, 0)) AS std_bc
            RETURN bc, avg_bc, std_bc, CASE WHEN std_bc > 0 THEN (bc - avg_bc) / std_bc ELSE 0 END AS z_score
            """, {"id": company_id}
        )
        if not result:
            return {"signal": "Betweenness Centrality Spike", "triggered": False, "score": 0, "detail": "No data"}
        r = result[0]
        z = r.get("z_score", 0)
        triggered = z > 2
        return {
            "signal": "Betweenness Centrality Spike",
            "triggered": triggered,
            "score": min(round(max(z * 25, 0), 1), 100),
            "detail": f"Z-score: {z:.2f} (>{'>'}2σ = structural broker)" if triggered else f"Z-score: {z:.2f} (normal)",
            "z_score": round(z, 4),
        }

    def _clustering_anomaly(self, company_id: str) -> Dict:
        result = neo4j_client.run_query(
            """
            MATCH (c:Company {id: $id})
            RETURN coalesce(c.clustering_coefficient, 0) AS cc
            """, {"id": company_id}
        )
        cc = result[0]["cc"] if result else 0
        triggered = cc > 0.7
        return {
            "signal": "High Clustering Coefficient",
            "triggered": triggered,
            "score": min(round(cc * 100, 1), 100),
            "detail": f"Coefficient: {cc:.4f} — tight inner circle detected" if triggered else f"Coefficient: {cc:.4f}",
        }

    def _round_number_transactions(self, company_id: str) -> Dict:
        result = neo4j_client.run_query(
            """
            MATCH (c:Company {id: $id})-[r:SUPPLIES_TO]-()
            WITH r.amount AS amt
            WHERE amt > 0
            WITH amt, CASE WHEN amt % 100000 = 0 THEN 1 ELSE 0 END AS is_round
            RETURN count(*) AS total, sum(is_round) AS round_count
            """, {"id": company_id}
        )
        if not result or result[0]["total"] == 0:
            return {"signal": "Round-Number Transactions", "triggered": False, "score": 0, "detail": "No transactions"}
        r = result[0]
        ratio = r["round_count"] / r["total"]
        triggered = ratio > 0.3
        return {
            "signal": "Round-Number Transactions",
            "triggered": triggered,
            "score": min(round(ratio * 100, 1), 100),
            "detail": f"{r['round_count']}/{r['total']} transactions are round numbers ({ratio:.0%})",
        }

    def _same_day_multihop(self, company_id: str) -> Dict:
        result = neo4j_client.run_query(
            """
            MATCH (c:Company {id: $id})-[r1:SUPPLIES_TO]->(mid)-[r2:SUPPLIES_TO]->(dest)
            WHERE r1.date = r2.date AND c.id <> dest.id
            RETURN count(*) AS same_day_hops
            """, {"id": company_id}
        )
        count = result[0]["same_day_hops"] if result else 0
        triggered = count > 2
        return {
            "signal": "Same-Day Multi-Hop Transfers",
            "triggered": triggered,
            "score": min(count * 15, 100),
            "detail": f"{count} same-day multi-hop patterns detected" if triggered else "No same-day chains found",
        }

    def _director_multi_cluster(self, company_id: str) -> Dict:
        result = neo4j_client.run_query(
            """
            MATCH (d:Director)-[:OWNS]->(c:Company {id: $id})
            WITH d
            MATCH (d)-[:OWNS]->(other:Company)
            WHERE other.id <> $id
            WITH d, count(DISTINCT other) AS company_count,
                 collect(DISTINCT coalesce(other.risk_band, 'Monitor')) AS risk_bands
            RETURN d.name AS director, company_count,
                   size([b IN risk_bands WHERE b IN ['Investigate', 'EDD']]) AS high_risk_count
            """, {"id": company_id}
        )
        if not result:
            return {"signal": "Director Multi-Cluster Risk", "triggered": False, "score": 0, "detail": "No director links"}
        total_companies = sum(r["company_count"] for r in result)
        high_risk = sum(r.get("high_risk_count", 0) for r in result)
        triggered = total_companies >= 3 or high_risk >= 2
        return {
            "signal": "Director Multi-Cluster Risk",
            "triggered": triggered,
            "score": min((total_companies * 10 + high_risk * 20), 100),
            "detail": f"Directors control {total_companies} other companies ({high_risk} high-risk)",
            "directors": [{"name": r["director"], "companies": r["company_count"]} for r in result],
        }

    def _volume_surge(self, company_id: str) -> Dict:
        result = neo4j_client.run_query(
            """
            MATCH (c:Company {id: $id})-[r:SUPPLIES_TO]-()
            WITH c, count(r) AS txn_count, sum(r.amount) AS total_vol
            MATCH (all:Company)-[ra:SUPPLIES_TO]-()
            WITH c, txn_count, total_vol, avg(ra.amount) AS avg_amount, count(ra) AS total_txns
            WITH c, txn_count, total_vol, avg_amount,
                 toFloat(total_txns) / CASE WHEN count { (n:Company) } > 0 THEN count { (n:Company) } ELSE 1 END AS avg_txn_count
            RETURN txn_count, total_vol, avg_amount, avg_txn_count,
                   CASE WHEN avg_txn_count > 0 THEN txn_count / avg_txn_count ELSE 0 END AS volume_ratio
            """, {"id": company_id}
        )
        if not result:
            return {"signal": "Transaction Volume Surge", "triggered": False, "score": 0, "detail": "No data"}
        r = result[0]
        ratio = r.get("volume_ratio", 0)
        triggered = ratio > 2
        return {
            "signal": "Transaction Volume Surge",
            "triggered": triggered,
            "score": min(round(ratio * 25, 1), 100),
            "detail": f"Volume is {ratio:.1f}x average" if triggered else f"Volume ratio: {ratio:.1f}x (normal)",
        }


fraud_signal_engine = FraudSignalEngine()
