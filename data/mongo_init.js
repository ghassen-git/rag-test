// Initialize MongoDB replica set
try {
    rs.status();
    print("Replica set already initialized");
} catch (e) {
    print("Initializing replica set...");
    rs.initiate({
        _id: "rs0",
        members: [{ _id: 0, host: "mongo:27017" }]
    });
    print("Replica set initialized");
}

// Wait for replica set to be ready
sleep(2000);

// Initialize MongoDB with book reviews

db = db.getSiblingDB('books_reviews');

// Create reviews collection
db.createCollection('reviews');

// No sample reviews - ready for your own data
// Reviews will be added via:
// - API endpoint: POST /add_review
// - MongoDB CDC will automatically sync to vector database

// Create indexes for better query performance
db.reviews.createIndex({ book_id: 1 });
db.reviews.createIndex({ rating: 1 });
db.reviews.createIndex({ created_at: -1 });
db.reviews.createIndex({ helpful_count: -1 });

print("MongoDB initialization complete!");
