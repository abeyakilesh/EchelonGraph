"""Advanced features: fraud propagation and contagion simulation."""
from fastapi import APIRouter
from services.propagation import propagation_engine

router = APIRouter(prefix="/advanced")


@router.post("/propagate-fraud/{company_id}")
async def propagate_fraud(company_id: str, confirmed_risk: float = 100.0, max_hops: int = 5):
    """
    Propagate risk from a confirmed fraud company.
    Risk_boost = ConfirmedRisk × e^(-hop_distance)
    """
    result = propagation_engine.propagate_fraud(company_id, confirmed_risk, max_hops)
    return result


@router.post("/simulate-removal/{company_id}")
async def simulate_removal(company_id: str):
    """
    Simulate what happens if a company is removed from the supply chain.
    Shows downstream impact and critical dependencies.
    """
    result = propagation_engine.simulate_removal(company_id)
    return result
