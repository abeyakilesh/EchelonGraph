"""ML/GNN training and prediction API endpoints."""
from fastapi import APIRouter
from ml.trainer import gnn_trainer
from services.risk_engine import risk_engine

router = APIRouter(prefix="/ml")


@router.post("/train")
async def train_model(epochs: int = 100, lr: float = 0.01):
    """Train the GNN fraud detection model."""
    result = gnn_trainer.train(epochs=epochs, lr=lr)

    # After training, compute predictions for all companies
    if "error" not in result:
        predictions = gnn_trainer.predict_all()
        result["predictions_count"] = len(predictions)

        # Re-compute risk scores with GNN probabilities
        risk_engine.compute_all_risk_scores(gnn_probs=predictions)
        result["risk_scores_updated"] = True

    return result


@router.get("/predict/{company_id}")
async def predict_company(company_id: str):
    """Get GNN fraud probability for a company."""
    prob = gnn_trainer.predict_single(company_id)
    return {
        "company_id": company_id,
        "gnn_fraud_probability": prob,
        "label": "High Risk" if prob > 0.7 else ("Medium Risk" if prob > 0.4 else "Low Risk")
    }


@router.get("/predictions")
async def get_all_predictions():
    """Get GNN fraud probabilities for all companies."""
    predictions = gnn_trainer.predict_all()
    sorted_preds = sorted(predictions.items(), key=lambda x: x[1], reverse=True)
    return {
        "total": len(predictions),
        "predictions": [
            {"company_id": cid, "probability": prob}
            for cid, prob in sorted_preds[:100]
        ]
    }


@router.get("/training-history")
async def get_training_history():
    """Get training history metrics."""
    return {"history": gnn_trainer.training_history}
