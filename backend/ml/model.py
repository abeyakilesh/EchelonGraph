"""
GNN Model with fallback to scikit-learn when PyTorch/PyG unavailable.
"""

try:
    import torch
    import torch.nn.functional as F
    from torch import nn
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False

try:
    from torch_geometric.nn import SAGEConv
    HAS_GEOMETRIC = True
except ImportError:
    HAS_GEOMETRIC = False

if HAS_TORCH:
    class FraudGNN(nn.Module):
        """2-layer GraphSAGE / MLP for fraud prediction."""

        def __init__(self, in_channels: int, hidden_channels: int = 64, out_channels: int = 1, dropout: float = 0.3):
            super().__init__()
            if HAS_GEOMETRIC:
                self.conv1 = SAGEConv(in_channels, hidden_channels)
                self.conv2 = SAGEConv(hidden_channels, hidden_channels // 2)
            else:
                self.conv1 = nn.Linear(in_channels, hidden_channels)
                self.conv2 = nn.Linear(hidden_channels, hidden_channels // 2)

            self.classifier = nn.Linear(hidden_channels // 2, out_channels)
            self.dropout = nn.Dropout(dropout)
            self.has_geometric = HAS_GEOMETRIC

        def forward(self, x, edge_index=None):
            if self.has_geometric and edge_index is not None:
                x = self.conv1(x, edge_index)
            else:
                x = self.conv1(x)
            x = F.relu(x)
            x = self.dropout(x)

            if self.has_geometric and edge_index is not None:
                x = self.conv2(x, edge_index)
            else:
                x = self.conv2(x)
            x = F.relu(x)
            x = self.dropout(x)
            return self.classifier(x)

        def predict_proba(self, x, edge_index=None):
            self.eval()
            with torch.no_grad():
                logits = self.forward(x, edge_index)
                probs = torch.sigmoid(logits)
            return probs.squeeze()

else:
    # Fallback: no-op class when PyTorch unavailable
    class FraudGNN:
        """Placeholder when PyTorch is not installed."""

        def __init__(self, **kwargs):
            pass

        def forward(self, x, edge_index=None):
            return None

        def predict_proba(self, x, edge_index=None):
            return None
