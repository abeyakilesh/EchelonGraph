import sys
import os
import random
import uuid
import datetime

# Add project root to python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.neo4j_client import neo4j_client
from services.invoice_verification import invoice_verification_engine

def seed_invoices(cli_mode=False):
    """
    Creates some dummy POs, GRNs, and Invoices to test Multi-Tier Supply Chain Fraud.
    We will find a simple supply chain sequence in the DB to attach them to.
    """
    if cli_mode:
        print("Connecting to Neo4j...")
        neo4j_client.connect()
    
    # 1. Find a multi-tier supply chain: A -> B -> C -> D
    print("Finding supply chain paths...")
    query = """
    MATCH path = (a:Company)-[:SUPPLIES_TO]->(b:Company)-[:SUPPLIES_TO]->(c:Company)
    RETURN a.id AS tier1, b.id AS tier2, c.id AS tier3
    LIMIT 1
    """
    res = neo4j_client.run_query(query)
    
    if not res:
        print("Could not find a supply chain path in DB. Make sure data is seeded first.")
        if cli_mode:
            neo4j_client.close()
        return False
        
    tier1 = res[0]["tier1"]
    tier2 = res[0]["tier2"]
    tier3 = res[0]["tier3"]
    
    print(f"Using Supply Chain: {tier1} -> {tier2} -> {tier3}")
    
    # Scenario 1: A valid, fully-backed invoice from Tier1 to Tier2
    print("\n[Scenario 1] Creating Valid Invoice...")
    valid_inv_id = f"INV-VAL-{random.randint(1000, 9999)}"
    invoice_verification_engine.ingest_invoice({
        "id": valid_inv_id,
        "supplier_id": tier1,
        "buyer_id": tier2,
        "amount": 250000,
        "date": "2024-03-01"
    })
    invoice_verification_engine.link_document(valid_inv_id, "PO", f"PO-{random.randint(1000,9999)}", "2024-02-15")
    invoice_verification_engine.link_document(valid_inv_id, "GRN", f"GRN-{random.randint(1000,9999)}", "2024-03-05")
    print(f"Created Valid Invoice: {valid_inv_id}")
    
    # Scenario 2: A phantom invoice (no GRN, no PO) from Tier2 to Tier3
    print("\n[Scenario 2] Creating Phantom Invoice...")
    phantom_inv_id = f"INV-PHA-{random.randint(1000, 9999)}"
    invoice_verification_engine.ingest_invoice({
        "id": phantom_inv_id,
        "supplier_id": tier2,
        "buyer_id": tier3,
        "amount": 1800000, # Large amount anomaly
        "date": "2024-03-10"
    })
    # We do NOT link PO or GRN
    print(f"Created Phantom Invoice: {phantom_inv_id}")
    
    # Scenario 3: Duplicate invoice financing
    # Tier1 submits an invoice to Lender A (Buyer Tier2)
    # Tier1 submits the SAME invoice (slightly modified ID) to Lender B
    print("\n[Scenario 3] Creating Duplicate Fingerprint Invoices...")
    base_amount = 450000
    base_date = "2024-03-12"
    
    dup1_id = f"INV-A-{random.randint(1000, 9999)}"
    invoice_verification_engine.ingest_invoice({
        "id": dup1_id,
        "supplier_id": tier1,
        "buyer_id": tier2,
        "amount": base_amount,
        "date": base_date
    })
    invoice_verification_engine.link_document(dup1_id, "PO", f"PO-{random.randint(1000,9999)}", "2024-03-05")
    
    dup2_id = f"INV-B-{random.randint(1000, 9999)}"
    invoice_verification_engine.ingest_invoice({
        "id": dup2_id,
        "supplier_id": tier1,
        "buyer_id": tier2,
        "amount": base_amount, # Exact same amount, date, supplier, buyer
        "date": base_date
    })
    invoice_verification_engine.link_document(dup2_id, "PO", f"PO-{random.randint(1000,9999)}", "2024-03-05")
    
    print(f"Created Duplicate Invoices: {dup1_id}, {dup2_id}")
    
    print("\nSeeding Complete! You can test Phantom Detection now.")
    if cli_mode:
        neo4j_client.close()
    return True

if __name__ == "__main__":
    seed_invoices(cli_mode=True)
