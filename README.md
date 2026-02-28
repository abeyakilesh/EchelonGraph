# EchelonGraph: Multi-Tier Supply Chain Fraud Intelligence

EchelonGraph is an enterprise-grade web application designed to detect complex fraud patterns in supply chain finance. It utilizes Graph Neural Networks (GNNs), circular transaction detection, shell clusters analysis, and real-time phantom invoice tracking using Neo4j and a FastAPI backend.

## ⚠️ The Problem: Multi-Tier Supply Chain Fraud
In multi-tier supply chain finance (Tier 1 → Tier 2 → Tier 3), a Tier 1 supplier can fabricate phantom invoices. Each invoice might look legitimate individually, but cross-tier cascading triggers repeated financing, multiplying exposure. **Traditional invoice checks fail** because the fraud becomes visible only through network-level correlation.

## 🎯 The Expected Outcome
To solve this, we needed to build a real-time SCF fraud detection system that:
1. Validates invoices against Purchase Orders (PO) and Goods Receipt Notes (GRN).
2. Maps the buyer-supplier network topology.
3. Detects duplicate invoices across lenders using cryptographic invoice fingerprints.
4. Uses graph feasibility metrics to flag phantom invoices and provides pre-disbursement early warnings.

## 🧠 Why Our Solution Works (The EchelonGraph Advantage)
EchelonGraph solves this problem uniquely through **Graph AI and Topological Mapping rather than isolated rule sets:**

1. **Network-Level Visibility:** Instead of looking at invoices in a tabular format, we ingest every company, invoice, and document into a **Neo4j Graph Database**. By mapping the relationships as edges (`(Company)-[:ISSUED]->(Invoice)-[:VALIDATES]-(PO)`), we can instantly traverse multi-tier dependencies.
2. **Cryptographic Fingerprinting:** We hash incoming invoice parameters. If a Tier 1 supplier attempts to pledge the exact same invoice to Lender A and Lender B, the system calculates the identical hash and instantly flags the collision across the entire network—preventing multi-pledging.
3. **Graph Neural Networks (GNNs):** We don't just use standard rules; we run PageRank and Louvain community detection algorithms on the network. This allows us to detect dense clusters of shell companies and identify circular money flow loops (e.g., A → B → C → A) that are moving fake money to artificially inflate revenue.
4. **Phantom AI Detection:** By combining the topological risk score with missing document flags (Missing PO/GRN), we generate a real-time "Phantom Risk Score" that visually blocks disbursements before the money leaves the bank.

---

## Architecture
- **Frontend:** React + Vite (Minimalist Enterprise Design System)
- **Backend:** FastAPI (Python 3.11)
- **Graph Database:** Neo4j (Enterprise features: APOC + Graph Data Science)
- **Relational Database:** PostgreSQL (for Auth & Audit Trails)

---

##  How to Run the Project Locally

There are two main ways to run this project: **Using Docker (Recommended)** or **Manual Setup**.

### Method 1: The Quick Way (Using Docker Compose)
*This is the recommended method as it automatically provisions the Neo4j Graph Database (with the required GDS machine learning plugins) and the PostgreSQL database.*

**Prerequisites:** You must have [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running on your system.

1. Clone or download/extract the ZIP of this repository.
2. Open your terminal and navigate into the root `EchelonGraph` folder.
3. Run the following command:
   ```bash
   docker-compose up --build
   ```
4. **Access the application:**
   - Frontend Dashboard: `http://localhost:3000`
   - Backend API Docs: `http://localhost:8000/docs`
   - Neo4j Database Browser: `http://localhost:7474` (User: `neo4j`, Pass: `echelon_secret`)

---

### Method 2: Manual Setup (Without Docker)
*If you cannot run Docker, you can run the services manually, but you still need local instances of Neo4j and PostgreSQL running.*

**Prerequisites:** 
- Node.js (v18+)
- Python (3.11+)
- [Neo4j Desktop](https://neo4j.com/download/) (You **must** install the APOC and Graph Data Science plugins for the ML algorithms to work)
- PostgreSQL

#### Step 1: Start the Databases
1. Spin up your local Neo4j database (ensure APOC/GDS are active) running on `bolt://localhost:7687`.
2. Spin up your local PostgreSQL database.

#### Step 2: Start the FastAPI Backend
1. Open a terminal and navigate to the `backend` folder:
   ```bash
   cd backend
   ```
2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Start the backend server:
   ```bash
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

#### Step 3: Start the React Frontend
1. Open a **new** terminal window and navigate to the `frontend` folder:
   ```bash
   cd frontend
   ```
2. Install dependencies:
   ```bash
   npm install
   ```
3. Start the development server:
   ```bash
   npm run dev
   ```
4. Your application will be available at `http://localhost:3000`.

---

##  Generating Data & Using the App

Because the EchelonGraph databases start empty, you need to populate them with a synthetic supply chain network to test the analytics.

1. Open `http://localhost:3000` and login with the default Admin credentials.
2. Look at the bottom-left corner of the sidebar and click the blue **Run Pipeline** button. Wait 4-5 seconds for the engine to build the graph, train the GNNs, and calculate risk scores.
3. Navigate to the **Invoice Verification** tab and click **Generate Samples** to populate the Neo4j system with multi-tier duplicated and phantom invoices.
4. Explore the Investigation Workspace, Heatmaps, and Shell Cluster detection screens!
