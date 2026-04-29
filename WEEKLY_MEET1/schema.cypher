// ---- Create Constraints ----
CREATE CONSTRAINT city_name_unique IF NOT EXISTS FOR (c:City) REQUIRE c.name IS UNIQUE;
CREATE CONSTRAINT hotel_id_unique IF NOT EXISTS FOR (h:Hotel) REQUIRE h.id IS UNIQUE;
CREATE CONSTRAINT restaurant_id_unique IF NOT EXISTS FOR (r:Restaurant) REQUIRE r.id IS UNIQUE;
CREATE CONSTRAINT attraction_id_unique IF NOT EXISTS FOR (a:Attraction) REQUIRE a.id IS UNIQUE;
CREATE CONSTRAINT cuisine_name_unique IF NOT EXISTS FOR (c:Cuisine) REQUIRE c.name IS UNIQUE;

// ---- Create Data ----
// Cities
MERGE (c:City {name: 'Paris'}) SET c.country='France', c.population=2161000;
MERGE (c:City {name: 'New York'}) SET c.country='USA', c.population=8419000;

// Cuisines
MERGE (c:Cuisine {name:'French'});
MERGE (c:Cuisine {name:'Italian'});
MERGE (c:Cuisine {name:'American'});

// Hotels
MERGE (h:Hotel {id: 'h1'}) SET h.name = 'The Ritz', h.address = '15 Place Vendôme', h.rating = 5.0, h.priceRange = '$$$$';
MERGE (h:Hotel {id: 'h2'}) SET h.name = 'The Plaza', h.address = '768 5th Ave', h.rating = 4.8, h.priceRange = '$$$$';

// Restaurants
MERGE (r:Restaurant {id: 'r1'}) SET r.name = 'Le Bernardin', r.address = '155 W 51st St', r.rating = 4.9, r.priceRange = '$$$$';
MERGE (r:Restaurant {id: 'r2'}) SET r.name = "L'Ambroisie", r.address = '9 Place des Vosges', r.rating = 4.8, r.priceRange = '$$$$';

// Attractions
MERGE (a:Attraction {id: 'a1'}) SET a.name = 'Eiffel Tower', a.type = 'Monument', a.description = 'Iron lattice tower', a.admissionFee = 25.0;
MERGE (a:Attraction {id: 'a2'}) SET a.name = 'Louvre Museum', a.type = 'Museum', a.description = 'World largest art museum', a.admissionFee = 17.0;
MERGE (a:Attraction {id: 'a3'}) SET a.name = 'Central Park', a.type = 'Park', a.description = 'Urban park in NYC', a.admissionFee = 0.0;

// ---- Create Relationships ----
MATCH (h:Hotel {id: 'h1'}), (c:City {name: 'Paris'}) MERGE (h)-[:LOCATED_IN]->(c);
MATCH (h:Hotel {id: 'h2'}), (c:City {name: 'New York'}) MERGE (h)-[:LOCATED_IN]->(c);

MATCH (r:Restaurant {id: 'r1'}), (c:City {name: 'New York'}) MERGE (r)-[:LOCATED_IN]->(c);
MATCH (r:Restaurant {id: 'r2'}), (c:City {name: 'Paris'}) MERGE (r)-[:LOCATED_IN]->(c);

MATCH (a:Attraction {id: 'a1'}), (c:City {name: 'Paris'}) MERGE (a)-[:LOCATED_IN]->(c);
MATCH (a:Attraction {id: 'a2'}), (c:City {name: 'Paris'}) MERGE (a)-[:LOCATED_IN]->(c);
MATCH (a:Attraction {id: 'a3'}), (c:City {name: 'New York'}) MERGE (a)-[:LOCATED_IN]->(c);

// Has Attraction
MATCH (c:City {name: 'Paris'}), (a:Attraction {id: 'a1'}) MERGE (c)-[:HAS_ATTRACTION]->(a);
MATCH (c:City {name: 'Paris'}), (a:Attraction {id: 'a2'}) MERGE (c)-[:HAS_ATTRACTION]->(a);
MATCH (c:City {name: 'New York'}), (a:Attraction {id: 'a3'}) MERGE (c)-[:HAS_ATTRACTION]->(a);

// Serves Cuisine
MATCH (r:Restaurant {id: 'r1'}), (c:Cuisine {name: 'French'}) MERGE (r)-[:SERVES_CUISINE]->(c);
MATCH (r:Restaurant {id: 'r2'}), (c:Cuisine {name: 'French'}) MERGE (r)-[:SERVES_CUISINE]->(c);

// Near To
MATCH (h:Hotel {id: 'h1'}), (a:Attraction {id: 'a2'}) MERGE (h)-[:NEAR_TO {distance: 1.2}]->(a);
MATCH (a:Attraction {id: 'a2'}), (h:Hotel {id: 'h1'}) MERGE (a)-[:NEAR_TO {distance: 1.2}]->(h);
