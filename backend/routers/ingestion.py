"""Data ingestion router – upload data and generate synthetic datasets."""
from fastapi import APIRouter, HTTPException
from database.neo4j_client import neo4j_client
from services.data_generator import SyntheticDataGenerator

router = APIRouter()


def _batch_create_graph(data: dict):
    """Push all entities into Neo4j."""
    client = neo4j_client

    # Create Address nodes
    for addr in data.get("addresses", []):
        client.run_write(
            """
            MERGE (a:Address {id: $id})
            SET a.line1 = $line1, a.city = $city,
                a.state = $state, a.pincode = $pincode
            """,
            addr
        )

    # Create Company nodes
    for c in data["companies"]:
        client.run_write(
            """
            MERGE (co:Company {id: $id})
            SET co.name = $name,
                co.incorporation_date = $incorporation_date,
                co.industry = $industry,
                co.annual_revenue = $annual_revenue,
                co.employee_count = $employee_count
            """,
            c
        )
        # GSTIN node
        if c.get("gstin"):
            client.run_write(
                """
                MERGE (g:GSTIN {number: $gstin})
                WITH g
                MATCH (co:Company {id: $id})
                MERGE (co)-[:HAS_GSTIN]->(g)
                """,
                {"gstin": c["gstin"], "id": c["id"]}
            )
        # PAN node
        if c.get("pan"):
            client.run_write(
                """
                MERGE (p:PAN {number: $pan})
                WITH p
                MATCH (co:Company {id: $id})
                MERGE (co)-[:HAS_PAN]->(p)
                """,
                {"pan": c["pan"], "id": c["id"]}
            )

    # Create Director nodes
    for d in data["directors"]:
        client.run_write(
            """
            MERGE (d:Director {id: $id})
            SET d.name = $name, d.pan = $pan
            """,
            d
        )

    # Director-Company links
    for link in data["director_company_links"]:
        client.run_write(
            """
            MATCH (d:Director {id: $director_id})
            MATCH (co:Company {id: $company_id})
            MERGE (d)-[:OWNS]->(co)
            """,
            link
        )
        # Also create SHARES_DIRECTOR edges between companies with same director
        client.run_write(
            """
            MATCH (d:Director {id: $director_id})-[:OWNS]->(c1:Company)
            MATCH (d)-[:OWNS]->(c2:Company)
            WHERE c1.id <> c2.id
            MERGE (c1)-[:SHARES_DIRECTOR {director_id: d.id}]->(c2)
            """,
            {"director_id": link["director_id"]}
        )

    # Address-Company links
    for link in data["address_company_links"]:
        client.run_write(
            """
            MATCH (a:Address {id: $address_id})
            MATCH (co:Company {id: $company_id})
            MERGE (co)-[:REGISTERED_AT]->(a)
            """,
            link
        )

    # Bank accounts
    for ba in data["bank_accounts"]:
        client.run_write(
            """
            MERGE (b:BankAccount {id: $id})
            SET b.bank_name = $bank_name, b.account_number = $account_number
            WITH b
            MATCH (co:Company {id: $company_id})
            MERGE (co)-[:OWNS_ACCOUNT]->(b)
            """,
            ba
        )

    # Invoices
    for inv in data["invoices"]:
        client.run_write(
            """
            MERGE (i:Invoice {id: $id})
            SET i.amount = $amount, i.date = $date
            WITH i
            MATCH (from_co:Company {id: $from_company_id})
            MATCH (to_co:Company {id: $to_company_id})
            MERGE (from_co)-[:ISSUED]->(i)
            MERGE (from_co)-[:SUPPLIES_TO {invoice_id: i.id, amount: $amount}]->(to_co)
            """,
            inv
        )

    # Transactions
    for txn in data["transactions"]:
        client.run_write(
            """
            MATCH (from_ba:BankAccount {id: $from_account_id})
            MATCH (to_ba:BankAccount {id: $to_account_id})
            MERGE (from_ba)-[:TRANSFERRED_TO {
                txn_id: $id, amount: $amount, date: $date
            }]->(to_ba)
            """,
            txn
        )

    # Store fraud labels as Company properties
    for company_id, is_fraud in data.get("fraud_labels", {}).items():
        client.run_write(
            """
            MATCH (co:Company {id: $id})
            SET co.is_fraud = $is_fraud
            """,
            {"id": company_id, "is_fraud": is_fraud}
        )


@router.post("/upload-data")
async def upload_data(generate_synthetic: bool = True):
    """Upload or generate data and build the graph."""
    try:
        if generate_synthetic:
            generator = SyntheticDataGenerator(seed=42)
            data = generator.generate_all()

            # Clear existing data
            neo4j_client.clear_database()
            neo4j_client.create_constraints()

            # Push to Neo4j
            _batch_create_graph(data)

            return {
                "status": "success",
                "message": "Synthetic data generated and graph built",
                "stats": data["stats"]
            }

        raise HTTPException(400, "CSV/JSON upload not yet implemented — use generate_synthetic=True")

    except Exception as e:
        raise HTTPException(500, f"Data ingestion failed: {str(e)}")


@router.get("/graph-data")
async def get_graph_data(limit: int = 200):
    """Get graph data for visualization."""
    nodes = neo4j_client.run_query(
        """
        MATCH (c:Company)
        RETURN c.id AS id, c.name AS name, c.industry AS industry,
               c.annual_revenue AS revenue, c.employee_count AS employees,
               c.is_fraud AS is_fraud,
               coalesce(c.risk_score, 0) AS risk_score,
               coalesce(c.risk_band, 'Monitor') AS risk_band,
               coalesce(c.community_id, 0) AS community_id,
               coalesce(c.pagerank, 0) AS pagerank,
               coalesce(c.betweenness_centrality, 0) AS betweenness,
               coalesce(c.gnn_fraud_probability, 0) AS gnn_prob,
               labels(c)[0] AS type
        LIMIT $limit
        """,
        {"limit": limit}
    )

    edges = neo4j_client.run_query(
        """
        MATCH (c1:Company)-[r:SUPPLIES_TO]->(c2:Company)
        RETURN c1.id AS source, c2.id AS target,
               r.amount AS amount, type(r) AS rel_type
        LIMIT $limit
        """,
        {"limit": limit * 3}
    )

    # Also get SHARES_DIRECTOR edges
    dir_edges = neo4j_client.run_query(
        """
        MATCH (c1:Company)-[r:SHARES_DIRECTOR]->(c2:Company)
        RETURN DISTINCT c1.id AS source, c2.id AS target, 'SHARES_DIRECTOR' AS rel_type
        LIMIT $limit
        """,
        {"limit": limit}
    )

    return {
        "nodes": nodes,
        "edges": edges + dir_edges
    }
