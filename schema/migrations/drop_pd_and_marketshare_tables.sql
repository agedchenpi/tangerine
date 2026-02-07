-- Drop PD Statistics and Market Share tables
-- These feeds are being removed from the system

-- Drop PD Statistics table
DROP TABLE IF EXISTS feeds.newyorkfed_pd_statistics CASCADE;

-- Drop Market Share table
DROP TABLE IF EXISTS feeds.newyorkfed_market_share CASCADE;

-- Verify tables are gone
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_tables WHERE schemaname = 'feeds' AND tablename = 'newyorkfed_pd_statistics') AND
       NOT EXISTS (SELECT 1 FROM pg_tables WHERE schemaname = 'feeds' AND tablename = 'newyorkfed_market_share') THEN
        RAISE NOTICE 'Tables dropped successfully';
    ELSE
        RAISE EXCEPTION 'Failed to drop tables';
    END IF;
END $$;
