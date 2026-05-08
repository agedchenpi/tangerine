-- Far Side daily comics scraped from thefarside.com
CREATE TABLE IF NOT EXISTS feeds.tfarside (
    farside_id      SERIAL PRIMARY KEY,
    comic_date      DATE NOT NULL,
    position        SMALLINT NOT NULL,              -- 1-5 (order on the page)
    image_url       TEXT NOT NULL,                   -- CDN URL on featureassets.amuniversal.com
    alt_text        TEXT,                            -- visible text from the comic
    caption         TEXT,                            -- figcaption joke/description text
    local_filename  TEXT,                            -- e.g. farside_20260506_1.jpg
    created_date    TIMESTAMP DEFAULT NOW(),
    created_by      TEXT DEFAULT 'etl_user',
    UNIQUE (comic_date, position)
);

GRANT SELECT, INSERT, UPDATE, DELETE ON feeds.tfarside TO app_rw;
GRANT SELECT ON feeds.tfarside TO app_ro;
GRANT USAGE, SELECT ON SEQUENCE feeds.tfarside_farside_id_seq TO app_rw;

CREATE INDEX IF NOT EXISTS idx_tfarside_date ON feeds.tfarside (comic_date DESC);
