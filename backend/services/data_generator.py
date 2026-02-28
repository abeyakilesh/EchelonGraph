"""
Synthetic data generator for EchelonGraph MVP.
Generates 1000 companies, 50 shell clusters, 30 circular fraud loops, 10 normal communities.
"""
import random
import string
import uuid
from datetime import date, timedelta
from typing import List, Dict, Tuple

import numpy as np

# ── Helpers ──────────────────────────────────────────────────

INDUSTRIES = [
    "Manufacturing", "IT Services", "Logistics", "Construction",
    "Pharmaceuticals", "Textiles", "Agriculture", "Chemicals",
    "Electronics", "Automotive", "Retail", "Finance"
]

CITIES = [
    "Mumbai", "Delhi", "Bangalore", "Chennai", "Kolkata",
    "Hyderabad", "Pune", "Ahmedabad", "Jaipur", "Lucknow",
    "Surat", "Nagpur", "Indore", "Bhopal", "Chandigarh"
]

BANK_NAMES = [
    "State Bank of India", "HDFC Bank", "ICICI Bank", "Axis Bank",
    "Punjab National Bank", "Bank of Baroda", "Kotak Mahindra Bank",
    "IndusInd Bank", "Yes Bank", "Federal Bank"
]

FIRST_NAMES = [
    "Rajesh", "Suresh", "Amit", "Priya", "Deepak", "Mohan",
    "Sanjay", "Anita", "Vikram", "Kiran", "Ravi", "Sunita",
    "Arun", "Neha", "Prakash", "Geeta", "Rahul", "Pooja",
    "Manoj", "Kavita"
]

LAST_NAMES = [
    "Sharma", "Patel", "Singh", "Kumar", "Agarwal", "Gupta",
    "Jain", "Mehta", "Shah", "Reddy", "Rao", "Verma",
    "Iyer", "Nair", "Desai", "Chopra", "Kapoor", "Malhotra"
]


def _uid(prefix: str = "") -> str:
    return f"{prefix}{uuid.uuid4().hex[:12]}"


def _random_date(start_year=2018, end_year=2025) -> date:
    start = date(start_year, 1, 1)
    end = date(end_year, 12, 31)
    delta = (end - start).days
    return start + timedelta(days=random.randint(0, delta))


def _pan() -> str:
    return ''.join(random.choices(string.ascii_uppercase, k=5)) + \
           ''.join(random.choices(string.digits, k=4)) + \
           random.choice(string.ascii_uppercase)


def _gstin(state_code="27") -> str:
    return state_code + _pan() + random.choice(string.digits) + "Z" + \
           random.choice(string.ascii_uppercase + string.digits)


# ── Generator ────────────────────────────────────────────────

class SyntheticDataGenerator:
    """Generate realistic synthetic supply-chain data with embedded fraud patterns."""

    def __init__(self, seed: int = 42):
        random.seed(seed)
        np.random.seed(seed)

        self.companies: List[Dict] = []
        self.directors: List[Dict] = []
        self.bank_accounts: List[Dict] = []
        self.invoices: List[Dict] = []
        self.transactions: List[Dict] = []
        self.director_company_links: List[Dict] = []
        self.address_company_links: List[Dict] = []
        self.addresses: List[Dict] = []

        # Track fraud labels
        self.shell_company_ids: set = set()
        self.circular_company_ids: set = set()
        self.fraud_labels: Dict[str, bool] = {}

    def generate_all(self) -> Dict:
        """Generate the complete synthetic dataset."""
        self._generate_addresses(80)
        self._generate_directors(250)
        self._generate_normal_communities(13, companies_per=50)
        self._generate_shell_clusters(20)
        self._generate_circular_loops(15)
        self._fill_remaining_companies()
        self._generate_bank_accounts()
        self._generate_supply_chain_invoices()
        self._generate_transactions()
        self._assign_fraud_labels()

        return {
            "companies": self.companies,
            "directors": self.directors,
            "bank_accounts": self.bank_accounts,
            "invoices": self.invoices,
            "transactions": self.transactions,
            "director_company_links": self.director_company_links,
            "address_company_links": self.address_company_links,
            "addresses": self.addresses,
            "fraud_labels": self.fraud_labels,
            "stats": {
                "total_companies": len(self.companies),
                "total_directors": len(self.directors),
                "shell_companies": len(self.shell_company_ids),
                "circular_fraud_companies": len(self.circular_company_ids),
                "total_invoices": len(self.invoices),
                "total_transactions": len(self.transactions),
            }
        }

    def _generate_addresses(self, count: int):
        for i in range(count):
            self.addresses.append({
                "id": _uid("ADDR-"),
                "line1": f"{random.randint(1,999)} {random.choice(['MG Road','Industrial Area','Tech Park','Commerce St','Station Rd'])}",
                "city": random.choice(CITIES),
                "state": "Maharashtra",
                "pincode": str(random.randint(100000, 999999)),
            })

    def _generate_directors(self, count: int):
        for i in range(count):
            self.directors.append({
                "id": _uid("DIR-"),
                "name": f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}",
                "pan": _pan(),
            })

    def _create_company(self, shell: bool = False, recent: bool = False) -> Dict:
        cid = _uid("COMP-")
        inc_date = _random_date(2023, 2025) if recent else _random_date(2015, 2024)
        emp = 0 if shell else random.randint(10, 5000)
        revenue = random.uniform(50_000_000, 500_000_000) if shell else random.uniform(1_000_000, 100_000_000)

        company = {
            "id": cid,
            "name": f"{'Shell ' if shell else ''}{random.choice(['Global','Prime','Apex','Star','Nova','Delta','Sigma','Alpha','Omega','Zeta'])} "
                    f"{random.choice(['Enterprises','Solutions','Industries','Trading','Corp','Ltd','Infra','Tech'])}",
            "incorporation_date": str(inc_date),
            "industry": random.choice(INDUSTRIES),
            "annual_revenue": round(revenue, 2),
            "employee_count": emp,
            "gstin": _gstin(),
            "pan": _pan(),
        }
        self.companies.append(company)
        return company

    def _generate_normal_communities(self, num_communities: int, companies_per: int):
        """Generate normal legitimate trading communities."""
        for comm_idx in range(num_communities):
            community_companies = []
            for _ in range(companies_per):
                c = self._create_company()
                community_companies.append(c)

            # Assign 1-2 directors per company (minimal overlap)
            for c in community_companies:
                num_dirs = random.randint(1, 2)
                dirs = random.sample(self.directors[:150], num_dirs)
                for d in dirs:
                    self.director_company_links.append({
                        "director_id": d["id"],
                        "company_id": c["id"]
                    })

            # Assign unique addresses
            for c in community_companies:
                addr = random.choice(self.addresses)
                self.address_company_links.append({
                    "address_id": addr["id"],
                    "company_id": c["id"]
                })

    def _generate_shell_clusters(self, num_clusters: int):
        """Generate shell company clusters with suspicious patterns."""
        companies_per_cluster = random.choices(range(3, 8), k=num_clusters)

        for cluster_idx in range(num_clusters):
            cluster_size = companies_per_cluster[cluster_idx]
            cluster_companies = []

            # Shared address for cluster (>5 entities)
            shared_addr = random.choice(self.addresses[:20])

            # Shared directors (director overlap)
            shared_dirs = random.sample(self.directors[150:], min(3, len(self.directors[150:])))

            for _ in range(cluster_size):
                c = self._create_company(shell=True, recent=True)
                cluster_companies.append(c)
                self.shell_company_ids.add(c["id"])

                # All share same address
                self.address_company_links.append({
                    "address_id": shared_addr["id"],
                    "company_id": c["id"]
                })

                # All share same directors
                for d in shared_dirs:
                    self.director_company_links.append({
                        "director_id": d["id"],
                        "company_id": c["id"]
                    })

    def _generate_circular_loops(self, num_loops: int):
        """Generate circular transaction loops (3-7 hops)."""
        available_companies = [c for c in self.companies if c["id"] not in self.circular_company_ids]

        for loop_idx in range(num_loops):
            loop_length = random.randint(3, 7)
            if len(available_companies) < loop_length:
                # Create new companies for the loop
                loop_companies = [self._create_company() for _ in range(loop_length)]
            else:
                loop_companies = random.sample(available_companies, loop_length)
                available_companies = [c for c in available_companies if c not in loop_companies]

            # Create circular invoices: A→B→C→...→A
            base_amount = random.uniform(100_000, 10_000_000)
            for i in range(loop_length):
                from_c = loop_companies[i]
                to_c = loop_companies[(i + 1) % loop_length]

                # Slight amount variation to make it less obvious
                amount = base_amount * random.uniform(0.95, 1.05)

                self.invoices.append({
                    "id": _uid("INV-"),
                    "amount": round(amount, 2),
                    "date": str(_random_date(2024, 2025)),
                    "from_company_id": from_c["id"],
                    "to_company_id": to_c["id"],
                    "gstin": _gstin(),
                })

                self.circular_company_ids.add(from_c["id"])

    def _fill_remaining_companies(self):
        """Fill up to 1000 companies."""
        current = len(self.companies)
        remaining = max(0, 1000 - current)
        for _ in range(remaining):
            c = self._create_company()
            # Random director and address
            d = random.choice(self.directors)
            self.director_company_links.append({
                "director_id": d["id"],
                "company_id": c["id"]
            })
            addr = random.choice(self.addresses)
            self.address_company_links.append({
                "address_id": addr["id"],
                "company_id": c["id"]
            })

    def _generate_bank_accounts(self):
        """One bank account per company."""
        for c in self.companies:
            self.bank_accounts.append({
                "id": _uid("BA-"),
                "bank_name": random.choice(BANK_NAMES),
                "account_number": ''.join(random.choices(string.digits, k=14)),
                "company_id": c["id"],
            })

    def _generate_supply_chain_invoices(self):
        """Generate normal supply chain invoices between companies."""
        existing_invoice_pairs = {(inv["from_company_id"], inv["to_company_id"]) for inv in self.invoices}

        for _ in range(3000):
            pair = random.sample(self.companies, 2)
            key = (pair[0]["id"], pair[1]["id"])
            if key in existing_invoice_pairs:
                continue
            existing_invoice_pairs.add(key)

            self.invoices.append({
                "id": _uid("INV-"),
                "amount": round(random.uniform(10_000, 5_000_000), 2),
                "date": str(_random_date(2022, 2025)),
                "from_company_id": pair[0]["id"],
                "to_company_id": pair[1]["id"],
                "gstin": _gstin(),
            })

    def _generate_transactions(self):
        """Generate bank transactions corresponding to invoices."""
        ba_map = {ba["company_id"]: ba["id"] for ba in self.bank_accounts}

        for inv in self.invoices:
            from_ba = ba_map.get(inv["from_company_id"])
            to_ba = ba_map.get(inv["to_company_id"])
            if from_ba and to_ba:
                self.transactions.append({
                    "id": _uid("TXN-"),
                    "amount": inv["amount"],
                    "date": inv["date"],
                    "from_account_id": from_ba,
                    "to_account_id": to_ba,
                })

    def _assign_fraud_labels(self):
        """Assign fraud labels for GNN training."""
        for c in self.companies:
            is_fraud = (
                c["id"] in self.shell_company_ids or
                c["id"] in self.circular_company_ids
            )
            self.fraud_labels[c["id"]] = is_fraud
