-- Initialize PostgreSQL database with book metadata

CREATE TABLE IF NOT EXISTS books (
    id SERIAL PRIMARY KEY,
    title VARCHAR(512) NOT NULL,
    author VARCHAR(256) NOT NULL,
    isbn VARCHAR(20) UNIQUE,
    publication_date DATE,
    genre VARCHAR(100),
    rating DECIMAL(3, 2) CHECK (rating >= 0 AND rating <= 5),
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create index for faster queries
CREATE INDEX idx_books_genre ON books(genre);
CREATE INDEX idx_books_author ON books(author);
CREATE INDEX idx_books_rating ON books(rating);

-- No sample data - ready for your own books
-- Use the API endpoints to add your books:
-- POST /add_book - Add book metadata
-- POST /upload_pdf - Upload and index PDF files
-- POST /upload_text - Upload and index text content

-- Create trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_books_updated_at BEFORE UPDATE ON books
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
