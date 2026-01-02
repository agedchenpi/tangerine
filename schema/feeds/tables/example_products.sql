-- Example products table for demonstrating ETL framework
-- Created by Example ETL job

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_tables WHERE schemaname = 'feeds' AND tablename = 'example_products') THEN
        CREATE TABLE feeds.example_products (
            example_productsid SERIAL PRIMARY KEY,
            datasetid INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            product_name VARCHAR(255) NOT NULL,
            unit_price NUMERIC(10, 2) NOT NULL,
            stock_quantity INTEGER NOT NULL,
            product_status VARCHAR(50) NOT NULL,
            source_created_at TIMESTAMP NOT NULL,
            created_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            created_by VARCHAR(50) NOT NULL,
            modified_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            modified_by VARCHAR(50) NOT NULL,
            CONSTRAINT fk_example_products_dataset FOREIGN KEY (datasetid) REFERENCES dba.tdataset(datasetid)
        );

        COMMENT ON TABLE feeds.example_products IS 'Example products table for ETL framework demonstration';
        COMMENT ON COLUMN feeds.example_products.example_productsid IS 'Primary key - auto-incrementing ID';
        COMMENT ON COLUMN feeds.example_products.datasetid IS 'Foreign key to dba.tdataset - tracks which ETL run loaded this data';
        COMMENT ON COLUMN feeds.example_products.product_id IS 'Product identifier from source system';
        COMMENT ON COLUMN feeds.example_products.product_name IS 'Product name';
        COMMENT ON COLUMN feeds.example_products.unit_price IS 'Product unit price';
        COMMENT ON COLUMN feeds.example_products.stock_quantity IS 'Stock quantity';
        COMMENT ON COLUMN feeds.example_products.product_status IS 'Product status (active/inactive)';
        COMMENT ON COLUMN feeds.example_products.source_created_at IS 'Creation timestamp from source system';
        COMMENT ON COLUMN feeds.example_products.created_date IS 'ETL load timestamp';
        COMMENT ON COLUMN feeds.example_products.created_by IS 'ETL user who loaded the data';

        -- Create index on datasetid for dataset-based queries
        CREATE INDEX idx_example_products_datasetid ON feeds.example_products(datasetid);

        -- Create index on product_id for lookups
        CREATE INDEX idx_example_products_product_id ON feeds.example_products(product_id);

        -- Create index on created_date for time-based queries
        CREATE INDEX idx_example_products_created_date ON feeds.example_products(created_date);
    END IF;
END $$;

-- Grant permissions
GRANT SELECT ON feeds.example_products TO app_ro;
GRANT SELECT, INSERT, UPDATE, DELETE ON feeds.example_products TO app_rw;
GRANT ALL ON feeds.example_products TO admin;
