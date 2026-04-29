from neo4j import GraphDatabase

URI = "bolt://localhost:7687"
AUTH = ("neo4j", "daksh123")


def load_schema(session):
    with open("schema.cypher", "r") as f:
        # Split on ; but we also want to avoid splitting mid-string or comment if it were complex,
        # but for this simple file, splitting on ';' that ends a query is fine.
        content = f.read()
        
    # Split queries by looking for ';'
    queries = [q.strip() for q in content.split(";") if q.strip()]
        
    for query in queries:
        session.run(query)
    
    print("Schema loaded successfully from schema.cypher!")


# ---- Main ----
if __name__ == "__main__":
    with GraphDatabase.driver(URI, auth=AUTH) as driver:
        with driver.session() as session:
            # We use auto-commit transaction (session.run) directly 
            # because Neo4j doesn't allow mixing schema updates (Constraints) 
            # and Write updates (Merge) in the same explicit transaction function.
            load_schema(session)