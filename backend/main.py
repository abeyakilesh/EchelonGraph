"""EchelonGraph – Multi-Tier Supply Chain Fraud Intelligence Platform"""
import time
import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from database.neo4j_client import neo4j_client
from routers import ingestion, analytics, risk, ml_router, advanced, auth, invoices

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("echelon")


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        neo4j_client.connect()
        neo4j_client.create_constraints()
        logger.info(" Neo4j connected")
    except Exception as e:
        logger.warning(f" Neo4j not available: {e}")
    yield
    try:
        neo4j_client.close()
    except Exception:
        pass


app = FastAPI(
    title="EchelonGraph",
    description="Multi-Tier Supply Chain Fraud Intelligence Platform",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request timing middleware
@app.middleware("http")
async def timing_middleware(request: Request, call_next):
    start = time.time()
    try:
        response = await call_next(request)
        elapsed = round((time.time() - start) * 1000, 1)
        response.headers["X-Response-Time"] = f"{elapsed}ms"
        return response
    except Exception as e:
        logger.error(f"Unhandled error: {e}")
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})


# Register routers
app.include_router(auth.router)
app.include_router(ingestion.router, tags=["Data Ingestion"])
app.include_router(analytics.router, tags=["Graph Analytics"])
app.include_router(risk.router, tags=["Risk & Intelligence"])
app.include_router(ml_router.router, tags=["Machine Learning"])
app.include_router(advanced.router, tags=["Advanced Features"])
app.include_router(invoices.router)


@app.get("/")
async def root():
    return {
        "service": "EchelonGraph",
        "version": "2.0.0",
        "status": "operational",
        "docs": "/docs"
    }


@app.get("/health")
async def health():
    return {"status": "healthy"}
