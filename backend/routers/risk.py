"""Risk scoring, dashboard stats, and investigation intelligence endpoints."""
from fastapi import APIRouter
from database.neo4j_client import neo4j_client
from services.risk_engine import risk_engine
from services.graph_analytics import analytics_engine
from services.explainability import explainability_engine
from services.fraud_signals import fraud_signal_engine

router = APIRouter(tags=["Risk & Intelligence"])


@router.get("/dashboard-stats")
async def dashboard_stats():
    """Executive dashboard statistics."""
    stats = neo4j_client.run_query("""
        MATCH (c:Company)
        WITH count(c) AS total,
             sum(CASE WHEN c.risk_band = 'Investigate' THEN 1 ELSE 0 END) AS critical,
             sum(CASE WHEN c.risk_band = 'EDD' THEN 1 ELSE 0 END) AS high,
             sum(CASE WHEN c.risk_band = 'Monitor' THEN 1 ELSE 0 END) AS low,
             avg(coalesce(c.risk_score, 0)) AS avg_risk
        RETURN total, critical, high, low, avg_risk
    """)
    s = stats[0] if stats else {}

    shell = neo4j_client.run_query("""
        MATCH (d:Director)-[:OWNS]->(c:Company)
        WITH d, count(c) AS cnt WHERE cnt >= 3
        RETURN count(d) AS shell_clusters
    """)

    circular = neo4j_client.run_query("""
        MATCH path = (c:Company)-[:SUPPLIES_TO*3..7]->(c)
        RETURN count(DISTINCT c) AS circular_count
    """)

    return {
        "total_companies": s.get("total", 0),
        "critical_risk": s.get("critical", 0),
        "high_risk": s.get("high", 0),
        "low_risk": s.get("low", 0),
        "avg_risk_score": round(s.get("avg_risk", 0), 1),
        "shell_clusters": shell[0]["shell_clusters"] if shell else 0,
        "circular_paths": circular[0]["circular_count"] if circular else 0,
    }


@router.get("/top-risk-companies")
async def top_risk_companies(limit: int = 10):
    """Top N highest risk companies."""
    results = neo4j_client.run_query("""
        MATCH (c:Company)
        WHERE c.risk_score IS NOT NULL
        RETURN c.id AS id, c.name AS name, c.risk_score AS risk_score,
               c.risk_band AS risk_band, c.industry AS industry,
               coalesce(c.gnn_fraud_probability, 0) AS gnn_prob,
               coalesce(c.annual_revenue, 0) AS revenue,
               coalesce(c.community_id, 0) AS community
        ORDER BY c.risk_score DESC LIMIT $limit
    """, {"limit": limit})
    return {"companies": results, "total": len(results)}


@router.get("/risk-distribution")
async def risk_distribution():
    """Risk score distribution for charting."""
    results = neo4j_client.run_query("""
        MATCH (c:Company)
        WHERE c.risk_score IS NOT NULL
        WITH CASE
            WHEN c.risk_score >= 80 THEN 'Critical (80-100)'
            WHEN c.risk_score >= 60 THEN 'High (60-80)'
            WHEN c.risk_score >= 40 THEN 'Medium (40-60)'
            WHEN c.risk_score >= 20 THEN 'Low (20-40)'
            ELSE 'Minimal (0-20)'
        END AS band, count(*) AS count, avg(c.risk_score) AS avg_score
        RETURN band, count, avg_score
        ORDER BY avg_score DESC
    """)
    return {"distribution": results}


@router.get("/company/{company_id}")
async def get_company(company_id: str):
    """Full company details with network metrics."""
    result = neo4j_client.run_query("""
        MATCH (c:Company {id: $id})
        OPTIONAL MATCH (c)-[r:SUPPLIES_TO]-(other:Company)
        WITH c, count(DISTINCT other) AS neighbor_count, collect(DISTINCT {
            id: other.id, name: other.name,
            risk_score: coalesce(other.risk_score, 0),
            risk_band: coalesce(other.risk_band, 'Monitor')
        })[..10] AS neighbors
        RETURN c.id AS id, c.name AS name, c.industry AS industry,
               c.annual_revenue AS annual_revenue, c.employee_count AS employee_count,
               coalesce(c.risk_score, 0) AS risk_score,
               coalesce(c.risk_band, 'Monitor') AS risk_band,
               coalesce(c.degree_centrality, 0) AS degree_centrality,
               coalesce(c.betweenness_centrality, 0) AS betweenness_centrality,
               coalesce(c.pagerank, 0) AS pagerank,
               coalesce(c.clustering_coefficient, 0) AS clustering_coefficient,
               coalesce(c.community_id, 0) AS community_id,
               coalesce(c.gnn_fraud_probability, 0) AS gnn_probability,
               coalesce(c.is_fraud, false) AS is_fraud,
               neighbor_count, neighbors
    """, {"id": company_id})

    if not result:
        return {"error": "Company not found", "id": company_id}

    data = result[0]

    # Get explanation
    try:
        explanation = explainability_engine.explain(company_id)
        data["explanation"] = explanation
    except Exception:
        data["explanation"] = None

    # Get fraud signals
    try:
        signals = fraud_signal_engine.compute_all_signals(company_id)
        data["fraud_signals"] = signals
    except Exception:
        data["fraud_signals"] = None

    return data


@router.get("/risk-score/{company_id}")
async def get_risk_score(company_id: str):
    """Compute and return composite risk score with full breakdown."""
    try:
        score = risk_engine.compute_risk_score(company_id)
        return score
    except Exception as e:
        return {"company_id": company_id, "composite_score": 0, "risk_band": "Monitor", "error": str(e)}


@router.post("/compute-risk-scores")
async def compute_all_risk_scores():
    """Batch compute risk scores for all companies."""
    results = risk_engine.compute_all_risk_scores()
    return {"status": "computed", "total": len(results)}


@router.get("/community-risk")
async def community_risk():
    """Community-level risk aggregation with enhanced metrics."""
    results = neo4j_client.run_query("""
        MATCH (c:Company)
        WHERE c.community_id IS NOT NULL
        WITH c.community_id AS cid, collect(c) AS members
        WITH cid, size(members) AS company_count,
             [m IN members | coalesce(m.risk_score, 0)] AS risks,
             size([m IN members WHERE coalesce(m.risk_band, 'Monitor') IN ['Investigate', 'EDD']]) AS high_risk_count
        WITH cid, company_count, high_risk_count,
             reduce(s = 0.0, r IN risks | s + r) / CASE WHEN size(risks) > 0 THEN size(risks) ELSE 1 END AS avg_risk,
             reduce(mx = 0.0, r IN risks | CASE WHEN r > mx THEN r ELSE mx END) AS max_risk,
             [m IN members | {id: m.id, name: m.name, risk_score: coalesce(m.risk_score, 0), industry: m.industry}] AS top_entities
        RETURN cid AS community_id, company_count, avg_risk, max_risk, high_risk_count, top_entities
        ORDER BY avg_risk DESC
    """)

    # Compute internal transaction density per community
    for comm in results:
        density = neo4j_client.run_query("""
            MATCH (c1:Company {community_id: $cid})-[r:SUPPLIES_TO]->(c2:Company {community_id: $cid})
            RETURN count(r) AS internal_txns, sum(r.amount) AS internal_volume
        """, {"cid": comm["community_id"]})
        if density:
            comm["internal_txns"] = density[0].get("internal_txns", 0)
            comm["internal_volume"] = density[0].get("internal_volume", 0)
        else:
            comm["internal_txns"] = 0
            comm["internal_volume"] = 0

    return {"communities": results, "total": len(results)}


@router.get("/investigation-summary/{company_id}")
async def investigation_summary(company_id: str):
    """AI-generated investigation summary for audit reports."""
    company = neo4j_client.run_query("""
        MATCH (c:Company {id: $id})
        RETURN c.name AS name, c.industry AS industry,
               coalesce(c.risk_score, 0) AS risk_score,
               coalesce(c.risk_band, 'Monitor') AS risk_band,
               coalesce(c.betweenness_centrality, 0) AS betweenness,
               coalesce(c.pagerank, 0) AS pagerank,
               coalesce(c.community_id, 0) AS community,
               coalesce(c.gnn_fraud_probability, 0) AS gnn_prob,
               coalesce(c.annual_revenue, 0) AS revenue
    """, {"id": company_id})

    if not company:
        return {"summary": "Company not found.", "company_id": company_id}

    c = company[0]

    # Gather evidence
    directors = neo4j_client.run_query("""
        MATCH (d:Director)-[:OWNS]->(c:Company {id: $id})
        WITH d
        MATCH (d)-[:OWNS]->(other:Company)
        WHERE other.id <> $id
        RETURN d.name AS director, count(other) AS shared_companies
    """, {"id": company_id})

    circular = neo4j_client.run_query("""
        MATCH path = (c:Company {id: $id})-[:SUPPLIES_TO*3..7]->(c)
        WITH path, reduce(total = 0, r IN relationships(path) | total + coalesce(r.amount, 0)) AS loop_amount
        RETURN count(DISTINCT path) AS loop_count, sum(loop_amount) AS total_amount
    """, {"id": company_id})

    counterparties = neo4j_client.run_query("""
        MATCH (c:Company {id: $id})-[r:SUPPLIES_TO]-(other:Company)
        RETURN other.name AS name, sum(r.amount) AS volume,
               coalesce(other.risk_score, 0) AS risk
        ORDER BY volume DESC LIMIT 5
    """, {"id": company_id})

    # Build summary
    name = c["name"]
    risk_band = c["risk_band"]
    risk_score = c["risk_score"]
    revenue_cr = round(c["revenue"] / 10_000_000, 1) if c["revenue"] else 0

    parts = [f"{name} is classified as **{risk_band}** with a composite risk score of **{risk_score:.0f}/100**."]

    if revenue_cr:
        parts.append(f"The company reports annual revenue of ₹{revenue_cr}Cr in the {c['industry']} sector.")

    # Director overlap
    total_shared = sum(d["shared_companies"] for d in directors) if directors else 0
    if total_shared > 0:
        dir_names = ", ".join(d["director"] for d in directors[:3])
        parts.append(f"Shared directorship detected with **{total_shared} entities** through directors: {dir_names}.")

    # Circular paths
    loop_data = circular[0] if circular else {}
    if loop_data.get("loop_count", 0) > 0:
        amt_cr = round(loop_data["total_amount"] / 10_000_000, 1)
        parts.append(f"Involved in **{loop_data['loop_count']} circular fund flow(s)** totaling ₹{amt_cr}Cr.")

    # Centrality
    if c["betweenness"] > 0.01:
        parts.append("High betweenness centrality indicates **structural brokerage behavior** — this entity sits on critical fund flow paths.")

    if c["gnn_prob"] > 0.5:
        parts.append(f"The GNN model assigns a **{c['gnn_prob']*100:.0f}% fraud probability** based on graph structure analysis.")

    # High-risk counterparties
    risky_cp = [cp for cp in counterparties if cp["risk"] > 60] if counterparties else []
    if risky_cp:
        cp_names = ", ".join(cp["name"] for cp in risky_cp[:3])
        parts.append(f"Transacts with {len(risky_cp)} high-risk counterparties including: {cp_names}.")

    # Recommendation
    if risk_score >= 71:
        parts.append("\n**Recommendation:** Immediate investigation warranted. Flag for enhanced due diligence and escalate to senior compliance team.")
    elif risk_score >= 41:
        parts.append("\n**Recommendation:** Enhanced monitoring required. Schedule periodic review and assess counterparty exposure.")
    else:
        parts.append("\n**Recommendation:** Standard monitoring sufficient. No immediate action required.")

    return {
        "company_id": company_id,
        "company_name": name,
        "risk_band": risk_band,
        "summary": " ".join(parts),
        "evidence": {
            "shared_directors": total_shared,
            "circular_loops": loop_data.get("loop_count", 0),
            "loop_amount": loop_data.get("total_amount", 0),
            "high_risk_counterparties": len(risky_cp),
            "betweenness_centrality": c["betweenness"],
            "gnn_probability": c["gnn_prob"],
        },
        "top_counterparties": counterparties or [],
    }


@router.get("/fraud-signals/{company_id}")
async def get_fraud_signals(company_id: str):
    """Get advanced fraud signals for a company."""
    return fraud_signal_engine.compute_all_signals(company_id)


@router.get("/search")
async def search_companies(q: str, limit: int = 20):
    """Search companies and directors by name or ID."""
    results = neo4j_client.run_query("""
        MATCH (c:Company)
        WHERE toLower(c.name) CONTAINS toLower($q) OR c.id CONTAINS $q
        RETURN c.id AS id, c.name AS name, 'company' AS type,
               coalesce(c.risk_score, 0) AS risk_score,
               coalesce(c.risk_band, 'Monitor') AS risk_band,
               c.industry AS industry
        ORDER BY c.risk_score DESC LIMIT $limit
    """, {"q": q, "limit": limit})
    return {"results": results, "total": len(results)}
