"""Pydantic models for API request/response schemas."""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date, datetime


# ── Node Models ──────────────────────────────────────────────

class CompanyCreate(BaseModel):
    id: str
    name: str
    incorporation_date: Optional[date] = None
    industry: Optional[str] = None
    annual_revenue: Optional[float] = 0
    employee_count: Optional[int] = 0
    gstin: Optional[str] = None
    pan: Optional[str] = None
    address_id: Optional[str] = None


class DirectorCreate(BaseModel):
    id: str
    name: str
    pan: Optional[str] = None


class BankAccountCreate(BaseModel):
    id: str
    bank_name: str
    account_number: str
    company_id: str


class InvoiceCreate(BaseModel):
    id: str
    amount: float
    date: date
    from_company_id: str
    to_company_id: str
    gstin: Optional[str] = None


class TransactionCreate(BaseModel):
    id: str
    amount: float
    date: date
    from_account_id: str
    to_account_id: str


# ── Upload Payload ───────────────────────────────────────────

class DataUploadPayload(BaseModel):
    companies: List[CompanyCreate] = []
    directors: List[DirectorCreate] = []
    bank_accounts: List[BankAccountCreate] = []
    invoices: List[InvoiceCreate] = []
    transactions: List[TransactionCreate] = []
    director_company_links: List[dict] = []  # [{director_id, company_id}]
    address_company_links: List[dict] = []   # [{address_id, company_id}]


# ── Response Models ──────────────────────────────────────────

class CompanyResponse(BaseModel):
    id: str
    name: str
    incorporation_date: Optional[str] = None
    industry: Optional[str] = None
    annual_revenue: Optional[float] = 0
    employee_count: Optional[int] = 0


class CompanyDetail(CompanyResponse):
    degree_centrality: float = 0
    betweenness_centrality: float = 0
    pagerank: float = 0
    clustering_coefficient: float = 0
    community_id: int = -1
    circularity_index: float = 0
    shell_risk_score: float = 0
    risk_score: Optional[float] = None
    risk_band: Optional[str] = None
    gnn_probability: Optional[float] = None
    top_risk_drivers: List[dict] = []


class RiskScoreResponse(BaseModel):
    company_id: str
    company_name: str
    network_risk: float = 0
    transaction_anomaly: float = 0
    identity_overlap: float = 0
    gnn_probability: float = 0
    compliance_flags: float = 0
    composite_score: float = 0
    risk_band: str = "Monitor"
    top_drivers: List[dict] = []


class CircularPathResponse(BaseModel):
    path_id: int
    origin_company_id: str
    path_nodes: List[str]
    cycle_length: int
    total_amount: float


class ClusterResponse(BaseModel):
    cluster_id: int
    companies: List[dict]
    avg_shell_risk: float
    shared_directors: int
    shared_addresses: int


class CommunityRiskResponse(BaseModel):
    community_id: int
    company_count: int
    avg_risk_score: float
    high_risk_count: int
    risk_band: str


class PropagationResult(BaseModel):
    source_company_id: str
    affected_companies: List[dict]
    total_risk_increase: float


class GraphData(BaseModel):
    nodes: List[dict]
    edges: List[dict]
