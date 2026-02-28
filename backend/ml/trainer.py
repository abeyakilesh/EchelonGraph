"""
GNN Training Pipeline with scikit-learn fallback.
Uses RandomForest when PyTorch is unavailable (Python 3.13).
"""
import os
import json
import pickle
import numpy as np
from typing import Dict, List, Optional

from ml.graph_converter import graph_converter
from config import settings
from database.neo4j_client import neo4j_client

try:
    import torch
    import torch.nn.functional as F
    from torch import nn
    from ml.model import FraudGNN
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False

from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score


class GNNTrainer:
    """Train and evaluate fraud detection model (PyTorch or scikit-learn fallback)."""

    def __init__(self):
        self.model = None
        self.graph_data: Optional[Dict] = None
        self.training_history: List[Dict] = []
        self.predictions: Dict[str, float] = {}
        self.use_torch = HAS_TORCH

    def train(self, epochs: int = None, lr: float = None) -> Dict:
        """Train the model on the current graph."""
        epochs = epochs or settings.gnn_epochs
        lr = lr or settings.gnn_lr

        # Convert graph
        self.graph_data = graph_converter.convert()
        if not self.graph_data:
            return {"error": "No graph data available. Upload data first."}

        if self.use_torch:
            return self._train_pytorch(epochs, lr)
        else:
            return self._train_sklearn()

    def _train_sklearn(self) -> Dict:
        """Fallback training with scikit-learn RandomForest."""
        x = self.graph_data["x"]  # numpy array
        y = self.graph_data["y"]  # numpy array
        idx_to_id = self.graph_data["idx_to_id"]

        X_train, X_val, y_train, y_val, idx_train, idx_val = train_test_split(
            x, y, np.arange(len(y)), test_size=0.2, random_state=42, stratify=y
        )

        # Train gradient boosting (better for fraud detection)
        self.model = GradientBoostingClassifier(
            n_estimators=100, max_depth=5, learning_rate=0.1,
            random_state=42, min_samples_split=5
        )
        self.model.fit(X_train, y_train)

        # Evaluate
        val_preds = self.model.predict(X_val)
        val_probs = self.model.predict_proba(X_val)[:, 1]

        accuracy = accuracy_score(y_val, val_preds)
        precision = precision_score(y_val, val_preds, zero_division=0)
        recall = recall_score(y_val, val_preds, zero_division=0)
        f1 = f1_score(y_val, val_preds, zero_division=0)

        self.training_history = [{
            "epoch": 1,
            "train_loss": 0,
            "val_loss": 0,
            "accuracy": round(accuracy, 4),
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1_score": round(f1, 4),
        }]

        # Save model
        self._save_model()

        return {
            "status": "trained",
            "model_type": "GradientBoosting (PyTorch unavailable)",
            "num_nodes": len(y),
            "num_features": x.shape[1],
            "fraud_ratio": round(float(y.mean()), 4),
            "final_metrics": self.training_history[-1],
            "history": self.training_history,
            "feature_importance": dict(
                zip(
                    ["degree_centrality", "betweenness_centrality", "pagerank",
                     "clustering_coeff", "revenue_norm", "employee_norm"],
                    [round(float(v), 4) for v in self.model.feature_importances_]
                )
            ),
        }

    def _train_pytorch(self, epochs: int, lr: float) -> Dict:
        """Train using PyTorch/PyG when available."""
        x = torch.tensor(self.graph_data["x"], dtype=torch.float)
        y = torch.tensor(self.graph_data["y"], dtype=torch.float)
        edge_index = torch.tensor(self.graph_data["edge_index"], dtype=torch.long) if self.graph_data["edge_index"] is not None else None

        num_features = x.shape[1]
        self.model = FraudGNN(in_channels=num_features, hidden_channels=64)
        optimizer = torch.optim.Adam(self.model.parameters(), lr=lr, weight_decay=5e-4)
        criterion = nn.BCEWithLogitsLoss()

        num_nodes = x.shape[0]
        perm = torch.randperm(num_nodes)
        train_size = int(0.8 * num_nodes)
        train_mask = torch.zeros(num_nodes, dtype=torch.bool)
        val_mask = torch.zeros(num_nodes, dtype=torch.bool)
        train_mask[perm[:train_size]] = True
        val_mask[perm[train_size:]] = True

        self.model.train()
        self.training_history = []

        for epoch in range(epochs):
            optimizer.zero_grad()
            out = self.model(x, edge_index).squeeze()
            loss = criterion(out[train_mask], y[train_mask])
            loss.backward()
            optimizer.step()

            if (epoch + 1) % 10 == 0 or epoch == epochs - 1:
                self.model.eval()
                with torch.no_grad():
                    val_out = self.model(x, edge_index).squeeze()
                    val_loss = criterion(val_out[val_mask], y[val_mask]).item()
                    val_probs = torch.sigmoid(val_out[val_mask])
                    val_preds = (val_probs > 0.5).float()
                    val_labels = y[val_mask]

                    correct = (val_preds == val_labels).sum().item()
                    total = val_mask.sum().item()
                    accuracy = correct / total if total > 0 else 0

                    tp = ((val_preds == 1) & (val_labels == 1)).sum().item()
                    fp = ((val_preds == 1) & (val_labels == 0)).sum().item()
                    fn = ((val_preds == 0) & (val_labels == 1)).sum().item()

                    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
                    recall = tp / (tp + fn) if (tp + fn) > 0 else 0

                    self.training_history.append({
                        "epoch": epoch + 1,
                        "train_loss": round(loss.item(), 4),
                        "val_loss": round(val_loss, 4),
                        "accuracy": round(accuracy, 4),
                        "precision": round(precision, 4),
                        "recall": round(recall, 4),
                    })
                self.model.train()

        self._save_model()

        return {
            "status": "trained",
            "model_type": "GraphSAGE (PyTorch)",
            "epochs": epochs,
            "num_nodes": num_nodes,
            "fraud_ratio": round(y.mean().item(), 4),
            "final_metrics": self.training_history[-1] if self.training_history else {},
            "history": self.training_history,
        }

    def predict_all(self) -> Dict[str, float]:
        """Get fraud probabilities for all companies."""
        if not self.model or not self.graph_data:
            self._load_model()
            if not self.model:
                return {}

        idx_to_id = self.graph_data["idx_to_id"]

        if self.use_torch and HAS_TORCH:
            x = torch.tensor(self.graph_data["x"], dtype=torch.float)
            edge_index = torch.tensor(self.graph_data["edge_index"], dtype=torch.long) if self.graph_data["edge_index"] is not None else None
            probs = self.model.predict_proba(x, edge_index)
            for idx in range(len(probs)):
                company_id = idx_to_id.get(idx)
                if company_id:
                    self.predictions[company_id] = round(probs[idx].item(), 4)
        else:
            # sklearn
            x = self.graph_data["x"]
            probs = self.model.predict_proba(x)[:, 1]
            for idx in range(len(probs)):
                company_id = idx_to_id.get(idx)
                if company_id:
                    self.predictions[company_id] = round(float(probs[idx]), 4)

        # Store in Neo4j
        for company_id, prob in self.predictions.items():
            neo4j_client.run_write(
                """
                MATCH (c:Company {id: $id})
                SET c.gnn_fraud_probability = $prob
                """,
                {"id": company_id, "prob": prob}
            )

        return self.predictions

    def predict_single(self, company_id: str) -> float:
        if not self.predictions:
            self.predict_all()
        return self.predictions.get(company_id, 0.0)

    def _save_model(self):
        os.makedirs(settings.model_path, exist_ok=True)
        if self.use_torch and HAS_TORCH:
            path = os.path.join(settings.model_path, "fraud_gnn.pt")
            torch.save({
                "model_state": self.model.state_dict(),
                "in_channels": self.graph_data["num_features"],
            }, path)
        else:
            path = os.path.join(settings.model_path, "fraud_model.pkl")
            with open(path, 'wb') as f:
                pickle.dump(self.model, f)

    def _load_model(self):
        self.graph_data = graph_converter.convert()
        if not self.graph_data:
            return

        if self.use_torch and HAS_TORCH:
            path = os.path.join(settings.model_path, "fraud_gnn.pt")
            if os.path.exists(path):
                checkpoint = torch.load(path, weights_only=False)
                self.model = FraudGNN(in_channels=checkpoint["in_channels"])
                self.model.load_state_dict(checkpoint["model_state"])
        else:
            path = os.path.join(settings.model_path, "fraud_model.pkl")
            if os.path.exists(path):
                with open(path, 'rb') as f:
                    self.model = pickle.load(f)


gnn_trainer = GNNTrainer()
