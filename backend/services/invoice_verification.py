import hashlib
import json
from typing import Dict, List, Optional
from database.neo4j_client import neo4j_client

class InvoiceVerificationService:
    """
    Handles Multi-Tier Supply Chain Fraud (Phantom Invoice) detection.
    Validates invoices against PO/GRN documents, generates fingerprints to detect
    duplicates across the network, and monitors cash collection/anomalies in SCF.
    """

    def generate_fingerprint(self, supplier_id: str, buyer_id: str, amount: float, date: str) -> str:
        """
        Create a cryptographic hash fingerprint of an invoice to detect duplicates
        across multiple lenders.
        """
        payload = f"{supplier_id}_{buyer_id}_{amount:.2f}_{date}"
        return hashlib.sha256(payload.encode()).hexdigest()

    def ingest_invoice(self, data: Dict) -> Dict:
        """
        Create an Invoice node in Neo4j and link it to Supplier and Buyer.
        Data must contain: id, supplier_id, buyer_id, amount, date.
        """
        fingerprint = self.generate_fingerprint(
            data["supplier_id"], data["buyer_id"], float(data["amount"]), data["date"]
        )

        query = """
        MATCH (s:Company {id: $supplier_id})
        MATCH (b:Company {id: $buyer_id})
        MERGE (i:Invoice {id: $invoice_id})
        SET i.amount = $amount,
            i.date = $date,
            i.fingerprint = $fingerprint,
            i.status = 'Ingested'
        MERGE (s)-[:ISSUED]->(i)
        MERGE (i)-[:BILLED_TO]->(b)
        RETURN i.id AS invoice_id, i.fingerprint AS fingerprint
        """
        
        result = neo4j_client.run_write(query, {
            "supplier_id": data["supplier_id"],
            "buyer_id": data["buyer_id"],
            "invoice_id": data["id"],
            "amount": float(data["amount"]),
            "date": data["date"],
            "fingerprint": fingerprint
        })
        
        if not result:
            return {"error": "Supplier or Buyer not found"}
        
        # Check for duplicates across the network immediately
        duplicates = self.check_duplicate_fingerprint(fingerprint, data["id"])
        
        return {
            "invoice_id": data["id"],
            "fingerprint": fingerprint,
            "duplicate_detected": len(duplicates) > 0,
            "duplicate_invoices": duplicates
        }

    def check_duplicate_fingerprint(self, fingerprint: str, exclude_invoice_id: str = None) -> List[str]:
        """
        Find other invoices in the system with the exact same fingerprint.
        """
        query = """
        MATCH (i:Invoice {fingerprint: $fingerprint})
        WHERE i.id <> $exclude_id
        RETURN i.id AS duplicate_id
        """
        result = neo4j_client.run_query(query, {
            "fingerprint": fingerprint,
            "exclude_id": exclude_invoice_id or ""
        })
        return [r["duplicate_id"] for r in result]

    def link_document(self, invoice_id: str, doc_type: str, doc_id: str, date: str) -> Dict:
        """
        Link a Purchase Order (PO) or Goods Receipt Note (GRN) to an invoice.
        doc_type should be 'PO' or 'GRN'.
        """
        label = "PO" if doc_type.upper() == "PO" else "GRN"
        
        query = f"""
        MATCH (i:Invoice {{id: $invoice_id}})
        MERGE (d:{label} {{id: $doc_id}})
        SET d.date = $date, d.type = '{label}'
        MERGE (d)-[:VALIDATES]->(i)
        RETURN d.id AS doc_id, d.type AS doc_type
        """
        result = neo4j_client.run_write(query, {
            "invoice_id": invoice_id,
            "doc_id": doc_id,
            "date": date
        })
        return result[0] if result else {"error": "Invoice not found"}

    def verify_invoice(self, invoice_id: str) -> Dict:
        """
        Verifies an invoice by checking:
        1. PO match
        2. GRN match
        3. Fingerprint uniqueness (no duplicates)
        """
        query = """
        MATCH (i:Invoice {id: $invoice_id})
        OPTIONAL MATCH (po:PO)-[:VALIDATES]->(i)
        OPTIONAL MATCH (grn:GRN)-[:VALIDATES]->(i)
        MATCH (s:Company)-[:ISSUED]->(i)-[:BILLED_TO]->(b:Company)
        RETURN i.id AS invoice_id,
               i.amount AS amount,
               i.date AS date,
               i.fingerprint AS fingerprint,
               s.name AS supplier_name,
               b.name AS buyer_name,
               po.id IS NOT NULL AS has_po,
               grn.id IS NOT NULL AS has_grn
        """
        result = neo4j_client.run_query(query, {"invoice_id": invoice_id})
        if not result:
            return {"error": "Invoice not found"}
            
        r = result[0]
        duplicates = self.check_duplicate_fingerprint(r["fingerprint"], invoice_id)
        
        # Determine Phantom Risk Score
        risk_score = 0
        if duplicates:
            risk_score += 100
        if not r["has_po"]:
            risk_score += 30
        if not r["has_grn"]:
            risk_score += 40
            
        is_phantom = risk_score >= 70
        
        return {
            "invoice_id": invoice_id,
            "amount": r["amount"],
            "date": r["date"],
            "supplier": r["supplier_name"],
            "buyer": r["buyer_name"],
            "has_po": r["has_po"],
            "has_grn": r["has_grn"],
            "duplicate_count": len(duplicates),
            "duplicate_refs": duplicates,
            "phantom_risk_score": min(risk_score, 100),
            "is_phantom": is_phantom
        }

    def get_all_invoices(self) -> List[Dict]:
        """
        Returns all tracked invoices with their validation status.
        """
        query = """
        MATCH (s:Company)-[:ISSUED]->(i:Invoice)-[:BILLED_TO]->(b:Company)
        OPTIONAL MATCH (po:PO)-[:VALIDATES]->(i)
        OPTIONAL MATCH (grn:GRN)-[:VALIDATES]->(i)
        RETURN i.id AS id,
               i.amount AS amount,
               i.date AS date,
               i.fingerprint AS fingerprint,
               s.name AS supplier,
               b.name AS buyer,
               po.id IS NOT NULL AS has_po,
               grn.id IS NOT NULL AS has_grn
        ORDER BY i.date DESC
        LIMIT 100
        """
        results = neo4j_client.run_query(query)
        
        # Append duplicate information
        for r in results:
            dupes = self.check_duplicate_fingerprint(r["fingerprint"], r["id"])
            r["duplicate_count"] = len(dupes)
            
            risk = 0
            if len(dupes) > 0: risk += 100
            if not r["has_po"]: risk += 30
            if not r["has_grn"]: risk += 40
            r["is_phantom"] = risk >= 70
            
        return results

invoice_verification_engine = InvoiceVerificationService()
