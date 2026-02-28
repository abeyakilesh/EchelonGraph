"""
Convert Neo4j graph to numpy arrays for ML training.
Falls back to numpy when PyTorch Geometric is unavailable.
"""
import numpy as np
from typing import Dict, Optional
from database.neo4j_client import neo4j_client

try:
    import torch
    from torch_geometric.data import Data
    HAS_GEOMETRIC = True
except ImportError:
    HAS_GEOMETRIC = False


class GraphConverter:
    """Convert Neo4j supply-chain graph to arrays for model training."""

    def convert(self) -> Optional[Dict]:
        """
        Extract graph from Neo4j and convert to numpy/torch tensors.
        Returns dict with features, labels, edge index, and id_mapping.
        """
        companies = neo4j_client.run_query(
            """
            MATCH (c:Company)
            RETURN c.id AS id, c.name AS name,
                   coalesce(c.degree_centrality, 0) AS degree_centrality,
                   coalesce(c.betweenness_centrality, 0) AS betweenness_centrality,
                   coalesce(c.pagerank, 0) AS pagerank,
                   coalesce(c.clustering_coefficient, 0) AS clustering_coefficient,
                   coalesce(c.annual_revenue, 0) AS annual_revenue,
                   coalesce(c.employee_count, 0) AS employee_count,
                   coalesce(c.is_fraud, false) AS is_fraud
            """
        )

        if not companies:
            return None

        id_to_idx = {c["id"]: i for i, c in enumerate(companies)}
        idx_to_id = {i: c["id"] for i, c in enumerate(companies)}

        features = []
        labels = []
        for c in companies:
            feature_vec = [
                c["degree_centrality"],
                c["betweenness_centrality"],
                c["pagerank"],
                c["clustering_coefficient"],
                min(c["annual_revenue"] / 500_000_000, 1.0),
                min(c["employee_count"] / 5000, 1.0),
            ]
            features.append(feature_vec)
            labels.append(1.0 if c["is_fraud"] else 0.0)

        x = np.array(features, dtype=np.float32)
        y = np.array(labels, dtype=np.float32)

        # Edges
        edges = neo4j_client.run_query(
            """
            MATCH (c1:Company)-[r:SUPPLIES_TO]->(c2:Company)
            RETURN c1.id AS source, c2.id AS target, coalesce(r.amount, 0) AS amount
            """
        )

        source_indices = []
        target_indices = []
        for e in edges:
            src = id_to_idx.get(e["source"])
            tgt = id_to_idx.get(e["target"])
            if src is not None and tgt is not None:
                source_indices.append(src)
                target_indices.append(tgt)

        dir_edges = neo4j_client.run_query(
            """
            MATCH (c1:Company)-[:SHARES_DIRECTOR]->(c2:Company)
            RETURN DISTINCT c1.id AS source, c2.id AS target
            """
        )
        for e in dir_edges:
            src = id_to_idx.get(e["source"])
            tgt = id_to_idx.get(e["target"])
            if src is not None and tgt is not None:
                source_indices.append(src)
                target_indices.append(tgt)

        edge_index = np.array([source_indices, target_indices], dtype=np.int64) if source_indices else None

        result = {
            "x": x,
            "y": y,
            "edge_index": edge_index,
            "id_to_idx": id_to_idx,
            "idx_to_id": idx_to_id,
            "num_nodes": len(companies),
            "num_edges": len(source_indices),
            "num_features": x.shape[1],
        }

        return result


graph_converter = GraphConverter()
