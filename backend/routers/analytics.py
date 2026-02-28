"""Analytics API endpoints."""
from fastapi import APIRouter
from services.graph_analytics import analytics_engine

router = APIRouter()


@router.get("/circular-paths/{company_id}")
async def get_circular_paths(company_id: str):
    """Detect circular transaction paths for a company."""
    ci_data = analytics_engine.compute_circularity_index(company_id)
    return ci_data


@router.get("/circular-paths")
async def get_all_circular_paths():
    """Detect all circular transaction paths in the graph."""
    paths = analytics_engine.detect_circular_paths()
    return {"circular_paths": paths, "total": len(paths)}


@router.get("/suspicious-clusters")
async def get_suspicious_clusters():
    """Get shell company clusters."""
    clusters = analytics_engine.detect_shell_clusters()
    return {"clusters": clusters, "total": len(clusters)}


@router.post("/compute-features")
async def compute_network_features():
    """Compute network features for all companies."""
    features = analytics_engine.compute_network_features()
    return {
        "status": "computed",
        "companies_processed": len(features),
        "features": features[:20],  # Sample
    }


@router.get("/shell-risk/{company_id}")
async def get_shell_risk(company_id: str):
    """Get shell company risk score."""
    return analytics_engine.compute_shell_risk_score(company_id)
