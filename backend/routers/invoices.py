from typing import Dict, List
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from services.invoice_verification import invoice_verification_engine
from routers.auth import get_current_user
from database.seed_invoices import seed_invoices

router = APIRouter(prefix="/invoices", tags=["Invoice Verification"])

class InvoiceUpload(BaseModel):
    id: str
    supplier_id: str
    buyer_id: str
    amount: float
    date: str

class DocumentLink(BaseModel):
    invoice_id: str
    doc_type: str
    doc_id: str
    date: str

@router.post("/upload", response_model=Dict)
def upload_invoice(data: InvoiceUpload, user=Depends(get_current_user)):
    """
    Ingest a new invoice and generate its cryptographic fingerprint.
    Checks for duplicates across the network instantly.
    """
    if user.get("role") not in ["admin", "investigator"]:
        raise HTTPException(status_code=403, detail="Not authorized to upload invoices")
        
    result = invoice_verification_engine.ingest_invoice(data.dict())
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

@router.post("/link-document", response_model=Dict)
def link_document(data: DocumentLink, user=Depends(get_current_user)):
    """
    Link a PO or GRN to an existing invoice.
    """
    if user.get("role") not in ["admin", "investigator"]:
        raise HTTPException(status_code=403, detail="Not authorized to link documents")
        
    if data.doc_type not in ["PO", "GRN"]:
        raise HTTPException(status_code=400, detail="Invalid doc_type. Must be PO or GRN.")
        
    result = invoice_verification_engine.link_document(
        data.invoice_id, data.doc_type, data.doc_id, data.date
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

@router.get("/verify/{invoice_id}", response_model=Dict)
def verify_invoice(invoice_id: str, user=Depends(get_current_user)):
    """
    Verify an invoice against its documents and check for duplicate fingerprints.
    """
    result = invoice_verification_engine.verify_invoice(invoice_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result

@router.get("/all", response_model=List[Dict])
def get_all_invoices(user=Depends(get_current_user)):
    """
    Retrieve all tracked invoices with their validation status.
    """
    return invoice_verification_engine.get_all_invoices()

@router.post("/generate-samples", response_model=Dict)
def generate_samples(user=Depends(get_current_user)):
    """
    Generate dummy phantom and duplicate invoices using the DB connection.
    """
    if user.get("role") not in ["admin", "investigator"]:
        raise HTTPException(status_code=403, detail="Not authorized")
        
    try:
        success = seed_invoices(cli_mode=False)
        if not success:
             raise HTTPException(status_code=400, detail="Cannot seed. No existing supply chains found in DB. Make sure to run the main graph analytics pipeline first.")
        return {"status": "success", "message": "Sample invoices created"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
