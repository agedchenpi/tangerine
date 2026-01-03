-- Regression test configurations for generic import system
-- Creates 17 test scenarios covering all file types and import strategies
-- All tables use RT_ prefix in feeds schema and are created dynamically on first run
-- Config names exclude REGRESSION_ prefix since datasettype='RegressionTest' identifies them
-- Filenames use convention: DescriptiveName_Date.ext (descriptive part first, date at end)

-- Ensure reference data exists
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM dba.tdatasource WHERE sourcename = 'RegressionTest') THEN
        INSERT INTO dba.tdatasource (sourcename, description, createdby)
        VALUES ('RegressionTest', 'Automated regression test data source', 'system');
    END IF;

    IF NOT EXISTS (SELECT 1 FROM dba.tdatasettype WHERE typename = 'RegressionTest') THEN
        INSERT INTO dba.tdatasettype (typename, description, createdby)
        VALUES ('RegressionTest', 'Automated regression test dataset type', 'system');
    END IF;
END $$;

-- =============================================================================
-- CSV TEST CONFIGURATIONS (6 tests)
-- =============================================================================

-- Test 1: CSV Strategy 1 - Auto-add columns
CALL dba.pimportconfigi(
    'CSV_Strategy1_AutoAddColumns',
    'RegressionTest',
    'RegressionTest',
    '/app/data/regression/csv',
    '/app/data/regression/archive',
    'Strategy1_Products_.*\.csv',
    'CSV',
    'filename',
    '0',
    'filename',
    '1',
    'yyyyMMddTHHmmss',
    '_',
    'feeds.rt_csv_strategy1_products',
    1,
    TRUE
);

-- Test 2: CSV Strategy 2 - Ignore extra columns (uses same table as Strategy 1)
CALL dba.pimportconfigi(
    'CSV_Strategy2_IgnoreExtraColumns',
    'RegressionTest',
    'RegressionTest',
    '/app/data/regression/csv',
    '/app/data/regression/archive',
    'Strategy2_Products_.*\.csv',
    'CSV',
    'filename',
    '0',
    'filename',
    '1',
    'yyyyMMddTHHmmss',
    '_',
    'feeds.rt_csv_strategy1_products',
    2,
    TRUE
);

-- Test 3: CSV Strategy 3 - Strict validation
CALL dba.pimportconfigi(
    'CSV_Strategy3_StrictValidation',
    'RegressionTest',
    'RegressionTest',
    '/app/data/regression/csv',
    '/app/data/regression/archive',
    'Strategy3_Orders_.*\.csv',
    'CSV',
    'filename',
    '0',
    'filename',
    '1',
    'yyyyMMddTHHmmss',
    '_',
    'feeds.rt_csv_strategy3_orders',
    3,
    TRUE
);

-- Test 4: CSV Metadata from filename
CALL dba.pimportconfigi(
    'CSV_MetadataFromFilename',
    'RegressionTest',
    'RegressionTest',
    '/app/data/regression/csv',
    '/app/data/regression/archive',
    'MetadataFilename_.*\.csv',
    'CSV',
    'filename',
    '0',
    'filename',
    '1',
    'yyyyMMddTHHmmss',
    '_',
    'feeds.rt_csv_metadata',
    1,
    TRUE
);

-- Test 5: CSV Empty file
CALL dba.pimportconfigi(
    'CSV_EmptyFile',
    'RegressionTest',
    'RegressionTest',
    '/app/data/regression/csv',
    '/app/data/regression/archive',
    'EmptyFile_.*\.csv',
    'CSV',
    'static',
    'EmptyTest',
    'static',
    '2026-01-01',
    'yyyy-MM-dd',
    '_',
    'feeds.rt_csv_empty',
    1,
    TRUE
);

-- Test 6: CSV Malformed data
CALL dba.pimportconfigi(
    'CSV_MalformedData',
    'RegressionTest',
    'RegressionTest',
    '/app/data/regression/csv',
    '/app/data/regression/archive',
    'MalformedData_.*\.csv',
    'CSV',
    'static',
    'MalformedTest',
    'static',
    '2026-01-01',
    'yyyy-MM-dd',
    '_',
    'feeds.rt_csv_malformed',
    2,
    TRUE
);

-- =============================================================================
-- XLS TEST CONFIGURATIONS (3 tests - PLACEHOLDER - Will need binary files)
-- =============================================================================

-- Test 7: XLS Strategy 1 - Inventory
CALL dba.pimportconfigi(
    'XLS_Strategy1_Inventory',
    'RegressionTest',
    'RegressionTest',
    '/app/data/regression/xls',
    '/app/data/regression/archive',
    'Strategy1_Inventory_.*\.xls',
    'XLS',
    'static',
    'InventoryReport',
    'filename',
    '1',
    'yyyyMMddTHHmmss',
    '_',
    'feeds.rt_xls_strategy1_inventory',
    1,
    TRUE
);

-- Test 8: XLS Metadata from content
CALL dba.pimportconfigi(
    'XLS_MetadataFromContent',
    'RegressionTest',
    'RegressionTest',
    '/app/data/regression/xls',
    '/app/data/regression/archive',
    'MetadataContent_.*\.xls',
    'XLS',
    'file_content',
    'category',
    'static',
    '2026-01-02',
    'yyyy-MM-dd',
    '_',
    'feeds.rt_xls_metadata',
    2,
    TRUE
);

-- Test 9: XLS Multiple sheets
CALL dba.pimportconfigi(
    'XLS_MultipleSheets',
    'RegressionTest',
    'RegressionTest',
    '/app/data/regression/xls',
    '/app/data/regression/archive',
    'MultipleSheets_.*\.xls',
    'XLS',
    'static',
    'MultipleSheetsTest',
    'static',
    '2026-01-02',
    'yyyy-MM-dd',
    '_',
    'feeds.rt_xls_multisheet',
    1,
    TRUE
);

-- =============================================================================
-- XLSX TEST CONFIGURATIONS (3 tests - PLACEHOLDER - Will need binary files)
-- =============================================================================

-- Test 10: XLSX Strategy 2 - Sales
CALL dba.pimportconfigi(
    'XLSX_Strategy2_Sales',
    'RegressionTest',
    'RegressionTest',
    '/app/data/regression/xlsx',
    '/app/data/regression/archive',
    'Strategy2_Sales_.*\.xlsx',
    'XLSX',
    'filename',
    '0',
    'filename',
    '1',
    'yyyyMMddTHHmmss',
    '_',
    'feeds.rt_xlsx_strategy2_sales',
    2,
    TRUE
);

-- Test 11: XLSX Date from content
CALL dba.pimportconfigi(
    'XLSX_DateFromContent',
    'RegressionTest',
    'RegressionTest',
    '/app/data/regression/xlsx',
    '/app/data/regression/archive',
    'DateContent_.*\.xlsx',
    'XLSX',
    'static',
    'DateContentTest',
    'file_content',
    'report_date',
    'yyyy-MM-dd',
    '_',
    'feeds.rt_xlsx_datecontent',
    1,
    TRUE
);

-- Test 12: XLSX Large file
CALL dba.pimportconfigi(
    'XLSX_LargeFile',
    'RegressionTest',
    'RegressionTest',
    '/app/data/regression/xlsx',
    '/app/data/regression/archive',
    'LargeFile_.*\.xlsx',
    'XLSX',
    'static',
    'LargeFileTest',
    'static',
    '2026-01-03',
    'yyyy-MM-dd',
    '_',
    'feeds.rt_xlsx_large',
    1,
    TRUE
);

-- =============================================================================
-- JSON TEST CONFIGURATIONS (3 tests)
-- =============================================================================

-- Test 13: JSON Array format
CALL dba.pimportconfigi(
    'JSON_ArrayFormat',
    'RegressionTest',
    'RegressionTest',
    '/app/data/regression/json',
    '/app/data/regression/archive',
    'ArrayFormat_.*\.json',
    'JSON',
    'static',
    'JSONArrayTest',
    'filename',
    '1',
    'yyyyMMddTHHmmss',
    '_',
    'feeds.rt_json_array',
    1,
    TRUE
);

-- Test 14: JSON Object format
CALL dba.pimportconfigi(
    'JSON_ObjectFormat',
    'RegressionTest',
    'RegressionTest',
    '/app/data/regression/json',
    '/app/data/regression/archive',
    'ObjectFormat_.*\.json',
    'JSON',
    'static',
    'JSONObjectTest',
    'static',
    '2026-01-04',
    'yyyy-MM-dd',
    '_',
    'feeds.rt_json_object',
    1,
    TRUE
);

-- Test 15: JSON Nested objects
CALL dba.pimportconfigi(
    'JSON_NestedObjects',
    'RegressionTest',
    'RegressionTest',
    '/app/data/regression/json',
    '/app/data/regression/archive',
    'NestedObjects_.*\.json',
    'JSON',
    'static',
    'JSONNestedTest',
    'static',
    '2026-01-04',
    'yyyy-MM-dd',
    '_',
    'feeds.rt_json_nested',
    1,
    TRUE
);

-- =============================================================================
-- XML TEST CONFIGURATIONS (2 tests)
-- =============================================================================

-- Test 16: XML Structured format
CALL dba.pimportconfigi(
    'XML_StructuredFormat',
    'RegressionTest',
    'RegressionTest',
    '/app/data/regression/xml',
    '/app/data/regression/archive',
    'StructuredXML_.*\.xml',
    'XML',
    'static',
    'XMLStructuredTest',
    'filename',
    '1',
    'yyyyMMddTHHmmss',
    '_',
    'feeds.rt_xml_structured',
    1,
    TRUE
);

-- Test 17: XML Blob format
CALL dba.pimportconfigi(
    'XML_BlobFormat',
    'RegressionTest',
    'RegressionTest',
    '/app/data/regression/xml',
    '/app/data/regression/archive',
    'BlobXML_.*\.xml',
    'XML',
    'static',
    'XMLBlobTest',
    'static',
    '2026-01-05',
    'yyyy-MM-dd',
    '_',
    'feeds.rt_xml_blob',
    1,
    TRUE
);
