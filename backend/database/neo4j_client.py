from neo4j import GraphDatabase
from config import settings


class Neo4jClient:
    """Neo4j driver wrapper for graph operations."""

    def __init__(self):
        self._driver = None

    def connect(self):
        self._driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password)
        )

    def close(self):
        if self._driver:
            self._driver.close()

    @property
    def driver(self):
        if not self._driver:
            self.connect()
        return self._driver

    def run_query(self, query: str, parameters: dict = None):
        with self.driver.session() as session:
            result = session.run(query, parameters or {})
            return [record.data() for record in result]

    def run_write(self, query: str, parameters: dict = None):
        with self.driver.session() as session:
            result = session.execute_write(
                lambda tx: tx.run(query, parameters or {}).data()
            )
            return result

    def clear_database(self):
        """Remove all nodes and relationships."""
        self.run_write("MATCH (n) DETACH DELETE n")

    def create_constraints(self):
        """Create uniqueness constraints for node types."""
        constraints = [
            "CREATE CONSTRAINT IF NOT EXISTS FOR (c:Company) REQUIRE c.id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (d:Director) REQUIRE d.id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (b:BankAccount) REQUIRE b.id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (i:Invoice) REQUIRE i.id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (po:PO) REQUIRE po.id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (grn:GRN) REQUIRE grn.id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (g:GSTIN) REQUIRE g.number IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (p:PAN) REQUIRE p.number IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (a:Address) REQUIRE a.id IS UNIQUE",
        ]
        for c in constraints:
            try:
                self.run_query(c)
            except Exception:
                pass  # Constraint may already exist


neo4j_client = Neo4jClient()
