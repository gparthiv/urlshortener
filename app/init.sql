CREATE TABLE IF NOT EXISTS urls (
    id SERIAL PRIMARY KEY,
    long_url TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


-- creates urls Table with 3 columns: id, long_url, created_at
-- we choose sql db ie postgreSQL over noSQL as we need unique shortcodes and the ACID properties of RDBMS ensures that
