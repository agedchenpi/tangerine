-- NewYorkFed Reference Data
-- Inserts data source and dataset types for Federal Reserve Bank of New York Markets API
-- This file is sourced during initial database setup via init.sh

DO $$
BEGIN
    -- Insert NewYorkFed data source if it doesn't exist
    IF NOT EXISTS (SELECT 1 FROM dba.tdatasource WHERE sourcename = 'NewYorkFed') THEN
        INSERT INTO dba.tdatasource (sourcename, description, createdby)
        VALUES (
            'NewYorkFed',
            'Federal Reserve Bank of New York Markets API - Reference rates, SOMA holdings, repo operations, and market data',
            'admin'
        );
        RAISE NOTICE 'Created data source: NewYorkFed';
    END IF;

    -- Insert NewYorkFed dataset types if they don't exist
    INSERT INTO dba.tdatasettype (typename, description, createdby) VALUES
        ('ReferenceRates', 'Reference rates: SOFR, EFFR, OBFR, TGCR, BGCR', 'admin'),
        ('AgencyMBS', 'Agency mortgage-backed securities operations', 'admin'),
        ('FXSwaps', 'Central bank liquidity swaps and foreign exchange operations', 'admin'),
        ('GuideSheets', 'Guide sheet publications: FR 2004SI, WI, F-Series', 'admin'),
        ('PDStatistics', 'Primary dealer statistics and survey results', 'admin'),
        ('MarketShare', 'Primary dealer market share data', 'admin'),
        ('RepoOperations', 'Repo and reverse repo operations', 'admin'),
        ('SecuritiesLending', 'Securities lending operations', 'admin'),
        ('SOMAHoldings', 'System Open Market Account holdings', 'admin'),
        ('TreasuryOperations', 'Treasury securities operations', 'admin')
    ON CONFLICT (typename) DO NOTHING;

    RAISE NOTICE 'NewYorkFed reference data setup complete';
END $$;
