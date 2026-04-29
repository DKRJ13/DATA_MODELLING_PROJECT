"""
STEP 5 (OPTIONAL): Load the Merged RDF Graph into Neo4j
=======================================================
Prerequisites:
  1. Install Neo4j Desktop: https://neo4j.com/download/
  2. Create a new database in Neo4j Desktop
  3. Install the neosemantics (n10s) plugin:
     - In Neo4j Desktop → your project → Add Plugin → neosemantics
  4. Start the database and set password to "password" (or update NEO4J_PASSWORD below)
  5. Install: pip install neo4j

Then run:
  python neo4j_loader.py

What this does:
  - Initializes neosemantics (n10s) on your Neo4j database
  - Imports the merged_output.ttl directly into Neo4j as native graph nodes/relationships
  - After loading, open Neo4j Browser and run: MATCH (n) RETURN n LIMIT 100
"""

from pathlib import Path
from neo4j import GraphDatabase

# ─────────────────────────────────────────────────────────────
#  ⚙ CONFIGURATION — update these to match your Neo4j setup
# ─────────────────────────────────────────────────────────────
NEO4J_URI      = "bolt://localhost:7687"
NEO4J_USER     = "neo4j"
NEO4J_PASSWORD = "password"   # Change this to your actual password

BASE_DIR    = Path(__file__).parent
TTL_FILE    = BASE_DIR / "output" / "merged_output.ttl"


def initialize_n10s(session):
    """Initialize the neosemantics (n10s) plugin on the Neo4j database."""
    print("[1] Initializing neosemantics (n10s) plugin...")

    # Create uniqueness constraint required by n10s
    session.run("CREATE CONSTRAINT n10s_unique_uri IF NOT EXISTS FOR (r:Resource) REQUIRE r.uri IS UNIQUE")

    # Initialize the graphconfig for RDF import
    session.run("""
        CALL n10s.graphconfig.init({
            handleVocabUris: 'MAP',
            handleMultival: 'ARRAY',
            keepLangTag: false,
            handleRDFTypes: 'NODES'
        })
    """)
    print("   ✓ n10s initialized")


def import_rdf(session, ttl_path: Path):
    """Import the merged Turtle file into Neo4j via n10s."""
    print(f"\n[2] Importing {ttl_path.name} into Neo4j...")

    # n10s needs a URL, so we use file:// protocol
    file_url = ttl_path.resolve().as_uri()

    result = session.run(
        "CALL n10s.rdf.import.fetch($url, 'Turtle')",
        url=file_url
    )
    summary = result.single()
    if summary:
        print(f"   ✓ Imported: {summary}")
    else:
        print("   ✓ Import complete")


def verify_import(session):
    """Run a quick verification query to confirm the import worked."""
    print("\n[3] Verifying import...")

    # Count all nodes
    result = session.run("MATCH (n) RETURN count(n) AS total")
    total = result.single()["total"]
    print(f"   Total nodes in Neo4j: {total}")

    # Find all patients
    result = session.run("""
        MATCH (p:ns0__Patient)
        RETURN p.ns0__fullName AS name, p.ns0__sourceHospital AS hospital
        LIMIT 10
    """)
    records = list(result)
    if records:
        print("\n   Patients in Neo4j:")
        for r in records:
            print(f"   → {r['name']} ({r['hospital']})")

    # Find interaction risks
    result = session.run("""
        MATCH (p:ns0__Patient)-[:ns0__hasInteractionRisk]->(risk)
        RETURN p.ns0__fullName AS patient, risk.uri AS interaction
    """)
    risks = list(result)
    if risks:
        print("\n   ⚠ Flagged Drug Interactions:")
        for r in risks:
            print(f"   🚨 {r['patient']} → {r['interaction'].split('#')[-1]}")


def print_cypher_hints():
    """Print some useful Cypher queries to run in Neo4j Browser."""
    print("\n" + "=" * 60)
    print("  Neo4j Browser Queries to try:")
    print("=" * 60)
    print("""
  // See the full graph (limit 50 nodes)
  MATCH (n) RETURN n LIMIT 50

  // Find all Patients
  MATCH (p:ns0__Patient) RETURN p

  // Find patients and their conditions
  MATCH (p:ns0__Patient)-[:ns0__hasCondition]->(d)
  RETURN p.ns0__fullName, d.uri

  // Find flagged drug interactions
  MATCH (p:ns0__Patient)-[:ns0__hasInteractionRisk]->(risk)
  RETURN p.ns0__fullName AS Patient, risk.uri AS Risk
    """)


def main():
    print("=" * 60)
    print("  Neo4j RDF Loader (via neosemantics / n10s)")
    print("=" * 60)

    if not TTL_FILE.exists():
        print("❌ merged_output.ttl not found. Please run ingest.py first.")
        return

    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        with driver.session() as session:
            initialize_n10s(session)
            import_rdf(session, TTL_FILE)
            verify_import(session)
        driver.close()
        print_cypher_hints()
        print("\n✅ Neo4j loading complete! Open Neo4j Browser to explore the graph.")

    except Exception as e:
        print(f"\n❌ Error connecting to Neo4j: {e}")
        print("\nTroubleshooting:")
        print("  1. Make sure Neo4j Desktop is running")
        print("  2. Check that NEO4J_PASSWORD in this script matches your database password")
        print("  3. Ensure the neosemantics (n10s) plugin is installed")
        print("\nNote: The SPARQL queries in sparql_queries.py work WITHOUT Neo4j.")


if __name__ == "__main__":
    main()
