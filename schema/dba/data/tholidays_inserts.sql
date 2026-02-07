-- Populate tholidays table with US Federal Holidays
-- This file is referenced by init.sh and must exist for successful database rebuild

-- Insert US Federal Holidays for 2024-2026
-- Using ON CONFLICT to make this script idempotent
INSERT INTO dba.tholidays (holiday_date, holiday_name)
VALUES
    -- 2024 Holidays
    ('2024-01-01', 'New Year''s Day'),
    ('2024-01-15', 'Martin Luther King Jr. Day'),
    ('2024-02-19', 'Presidents'' Day'),
    ('2024-05-27', 'Memorial Day'),
    ('2024-07-04', 'Independence Day'),
    ('2024-09-02', 'Labor Day'),
    ('2024-11-28', 'Thanksgiving Day'),
    ('2024-12-25', 'Christmas Day'),

    -- 2025 Holidays
    ('2025-01-01', 'New Year''s Day'),
    ('2025-01-20', 'Martin Luther King Jr. Day'),
    ('2025-02-17', 'Presidents'' Day'),
    ('2025-05-26', 'Memorial Day'),
    ('2025-07-04', 'Independence Day'),
    ('2025-09-01', 'Labor Day'),
    ('2025-11-27', 'Thanksgiving Day'),
    ('2025-12-25', 'Christmas Day'),

    -- 2026 Holidays
    ('2026-01-01', 'New Year''s Day'),
    ('2026-01-19', 'Martin Luther King Jr. Day'),
    ('2026-02-16', 'Presidents'' Day'),
    ('2026-05-25', 'Memorial Day'),
    ('2026-07-04', 'Independence Day'),
    ('2026-09-07', 'Labor Day'),
    ('2026-11-26', 'Thanksgiving Day'),
    ('2026-12-25', 'Christmas Day')
ON CONFLICT (holiday_date) DO NOTHING;

-- Note: When July 4th or Christmas fall on Saturday, Friday is typically observed
-- When they fall on Sunday, Monday is typically observed
-- This table stores the actual holiday date; business day logic handles observance
