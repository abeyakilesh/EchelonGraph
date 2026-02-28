"""
Graph Analytics Engine
- Circular transaction detection (DFS, Circularity Index)
- Shell company detection (rules-based scoring)
- Network feature engineering (centrality, PageRank, clustering, communities)
"""
import math
from typing import List, Dict, Set, Tuple
from database.neo4j_client import neo4j_client
from config import settings


class GraphAnalyticsEngine:
    """Core analytics for fraud detection on the supply-chain graph."""

    # ── Circular Transaction Detection ───────────────────────

    def detect_circular_paths(self, company_id: str = None, max_depth: int = 7) -> List[Dict]:
        """
        Detect circular transaction paths using Cypher variable-length paths.
        For a specific company or all companies.
        """
        if company_id:
            query = """
            MATCH path = (start:Company {id: $company_id})-[:SUPPLIES_TO*3..7]->(start)
            WITH path, [n IN nodes(path) | n.id] AS node_ids,
                 reduce(total = 0.0, r IN relationships(path) | total + coalesce(r.amount, 0)) AS total_amount
            RETURN DISTINCT
                $company_id AS origin,
                node_ids AS path_nodes,
                length(path) AS cycle_length,
                total_amount
            ORDER BY total_amount DESC
            LIMIT 50
            """
            return neo4j_client.run_query(query, {"company_id": company_id})
        else:
            query = """
            MATCH path = (start:Company)-[:SUPPLIES_TO*3..7]->(start)
            WITH start, path, [n IN nodes(path) | n.id] AS node_ids,
                 reduce(total = 0.0, r IN relationships(path) | total + coalesce(r.amount, 0)) AS total_amount
            RETURN DISTINCT
                start.id AS origin,
                node_ids AS path_nodes,
                length(path) AS cycle_length,
                total_amount
            ORDER BY total_amount DESC
            LIMIT 200
            """
            return neo4j_client.run_query(query)

    def compute_circularity_index(self, company_id: str) -> Dict:
        """
        CI = (Number of cycles × Avg cycle amount) / Total transaction volume
        """
        cycles = self.detect_circular_paths(company_id)
        cycle_count = len(cycles)

        if cycle_count == 0:
            return {"company_id": company_id, "circularity_index": 0.0, "cycle_count": 0}

        avg_cycle_amount = sum(c.get("total_amount", 0) for c in cycles) / cycle_count

        # Get total transaction volume
        vol = neo4j_client.run_query(
            """
            MATCH (c:Company {id: $id})-[r:SUPPLIES_TO]-()
            RETURN coalesce(sum(r.amount), 1) AS total_volume
            """,
            {"id": company_id}
        )
        total_volume = vol[0]["total_volume"] if vol else 1

        ci = (cycle_count * avg_cycle_amount) / max(total_volume, 1)

        return {
            "company_id": company_id,
            "circularity_index": round(min(ci, 1.0), 4),
            "cycle_count": cycle_count,
            "avg_cycle_amount": round(avg_cycle_amount, 2),
            "cycles": cycles[:10]  # Return top 10 cycles
        }

    # ── Shell Company Detection ──────────────────────────────

    def compute_shell_risk_score(self, company_id: str) -> Dict:
        """
        Shell risk based on:
        - Company age < 2 years
        - Transaction volume > 10x industry median
        - Shares director with 3+ entities
        - Registered at shared address with > 5 entities
        - No payroll/employee data
        """
        result = neo4j_client.run_query(
            """
            MATCH (c:Company {id: $id})
            OPTIONAL MATCH (c)-[:REGISTERED_AT]->(a:Address)<-[:REGISTERED_AT]-(other:Company)
            WITH c, a, count(DISTINCT other) AS address_sharing_count
            OPTIONAL MATCH (d:Director)-[:OWNS]->(c)
            OPTIONAL MATCH (d)-[:OWNS]->(other2:Company)
            WHERE other2.id <> c.id
            WITH c, address_sharing_count,
                 count(DISTINCT d) AS director_count,
                 count(DISTINCT other2) AS director_shared_companies
            OPTIONAL MATCH (c)-[r:SUPPLIES_TO]-()
            WITH c, address_sharing_count, director_count, director_shared_companies,
                 coalesce(sum(r.amount), 0) AS total_volume,
                 count(r) AS txn_count
            RETURN c.id AS id, c.name AS name,
                   c.incorporation_date AS inc_date,
                   c.employee_count AS employees,
                   c.annual_revenue AS revenue,
                   address_sharing_count, director_count,
                   director_shared_companies, total_volume, txn_count
            """,
            {"id": company_id}
        )

        if not result:
            return {"company_id": company_id, "shell_risk_score": 0}

        r = result[0]
        score = 0.0

        # Age check (< 2 years)
        inc_date = r.get("inc_date")
        if inc_date:
            from datetime import date
            try:
                if isinstance(inc_date, str):
                    from datetime import datetime
                    inc = datetime.strptime(inc_date, "%Y-%m-%d").date()
                else:
                    inc = inc_date
                age_years = (date.today() - inc).days / 365.25
                if age_years < 2:
                    score += 0.25
            except (ValueError, TypeError):
                pass

        # No employees
        if r.get("employees", 0) == 0:
            score += 0.20

        # High transaction volume relative to revenue
        if r.get("revenue", 0) > 0 and r.get("total_volume", 0) > 10 * r["revenue"]:
            score += 0.15

        # Shared directors with 3+ entities
        if r.get("director_shared_companies", 0) >= 3:
            score += 0.20

        # Shared address with > 5 entities
        if r.get("address_sharing_count", 0) > 5:
            score += 0.20

        return {
            "company_id": company_id,
            "company_name": r.get("name", ""),
            "shell_risk_score": round(min(score, 1.0), 4),
            "factors": {
                "young_company": inc_date is not None and score > 0,
                "no_employees": r.get("employees", 0) == 0,
                "high_volume_ratio": r.get("total_volume", 0) > 10 * r.get("revenue", 1),
                "director_overlap": r.get("director_shared_companies", 0),
                "address_sharing": r.get("address_sharing_count", 0),
            }
        }

    def detect_shell_clusters(self) -> List[Dict]:
        """Find clusters of companies sharing directors and addresses."""
        clusters = neo4j_client.run_query(
            """
            MATCH (d:Director)-[:OWNS]->(c:Company)
            WITH d, collect(c) AS companies
            WHERE size(companies) >= 3
            UNWIND companies AS c
            OPTIONAL MATCH (c)-[:REGISTERED_AT]->(a:Address)
            WITH d, c, a
            ORDER BY d.id
            WITH d.id AS director_id, d.name AS director_name,
                 collect(DISTINCT {id: c.id, name: c.name, annual_revenue: c.annual_revenue, risk_score: coalesce(c.risk_score, 0), industry: c.industry}) AS companies,
                 count(DISTINCT a) AS unique_addresses
            RETURN director_id, director_name, companies,
                   size(companies) AS company_count, unique_addresses
            ORDER BY company_count DESC
            LIMIT 50
            """
        )
        return clusters

    # ── Network Feature Engineering ──────────────────────────

    def compute_network_features(self) -> List[Dict]:
        """Compute centrality metrics for all Company nodes."""

        # Degree centrality
        degree = neo4j_client.run_query(
            """
            MATCH (c:Company)
            OPTIONAL MATCH (c)-[r:SUPPLIES_TO]-()
            WITH c, count(r) AS deg
            MATCH (total:Company)
            WITH c, deg, count(total) - 1 AS max_deg
            SET c.degree_centrality = CASE WHEN max_deg > 0
                THEN toFloat(deg) / max_deg ELSE 0 END
            RETURN c.id AS id, c.degree_centrality AS degree_centrality
            """
        )

        # PageRank using GDS if available, else approximate
        try:
            neo4j_client.run_query(
                """
                CALL gds.graph.project('supply_graph', 'Company', 'SUPPLIES_TO')
                """
            )
            neo4j_client.run_query(
                """
                CALL gds.pageRank.write('supply_graph', {writeProperty: 'pagerank'})
                """
            )
            neo4j_client.run_query(
                """
                CALL gds.betweenness.write('supply_graph', {writeProperty: 'betweenness_centrality'})
                """
            )
            neo4j_client.run_query(
                """
                CALL gds.localClusteringCoefficient.write('supply_graph', {writeProperty: 'clustering_coefficient'})
                """
            )
            # Community detection (Louvain)
            neo4j_client.run_query(
                """
                CALL gds.louvain.write('supply_graph', {writeProperty: 'community_id'})
                """
            )
            neo4j_client.run_query("CALL gds.graph.drop('supply_graph')")
        except Exception:
            # Fallback: compute simple approximations
            neo4j_client.run_query(
                """
                MATCH (c:Company)
                SET c.pagerank = coalesce(c.degree_centrality, 0),
                    c.betweenness_centrality = 0.0,
                    c.clustering_coefficient = 0.0,
                    c.community_id = 0
                """
            )

        # Fetch all computed features
        features = neo4j_client.run_query(
            """
            MATCH (c:Company)
            RETURN c.id AS id,
                   coalesce(c.degree_centrality, 0) AS degree_centrality,
                   coalesce(c.betweenness_centrality, 0) AS betweenness_centrality,
                   coalesce(c.pagerank, 0) AS pagerank,
                   coalesce(c.clustering_coefficient, 0) AS clustering_coefficient,
                   coalesce(c.community_id, 0) AS community_id
            """
        )
        return features

    def compute_transaction_features(self, company_id: str) -> Dict:
        """Compute transaction-related features for a company."""
        result = neo4j_client.run_query(
            """
            MATCH (c:Company {id: $id})-[r:SUPPLIES_TO]-()
            WITH c, collect(r.amount) AS amounts, count(r) AS txn_count
            WITH c, amounts, txn_count,
                 reduce(s = 0.0, a IN amounts | s + a) / CASE WHEN size(amounts) > 0 THEN size(amounts) ELSE 1 END AS avg_amount
            RETURN c.id AS id, txn_count,
                   avg_amount,
                   size(amounts) AS total_txns
            """,
            {"id": company_id}
        )

        if not result:
            return {"avg_transaction_deviation": 0, "transaction_velocity_spike": 0}

        r = result[0]

        # Compute director overlap ratio
        dir_result = neo4j_client.run_query(
            """
            MATCH (d:Director)-[:OWNS]->(c:Company {id: $id})
            WITH d
            MATCH (d)-[:OWNS]->(other:Company)
            WHERE other.id <> $id
            RETURN count(DISTINCT other) AS shared
            """,
            {"id": company_id}
        )
        shared = dir_result[0]["shared"] if dir_result else 0

        return {
            "avg_transaction_deviation": round(r.get("avg_amount", 0) / 1_000_000, 4),
            "transaction_velocity_spike": round(r.get("txn_count", 0) / 100, 4),
            "director_overlap_ratio": round(min(shared / 10, 1.0), 4),
        }


analytics_engine = GraphAnalyticsEngine()
