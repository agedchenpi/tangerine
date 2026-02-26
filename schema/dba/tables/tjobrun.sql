CREATE TABLE dba.tjobrun (
    jobrunid      SERIAL PRIMARY KEY,
    job_name      VARCHAR(100) NOT NULL,
    config_name   VARCHAR(100) NOT NULL,
    run_uuid      VARCHAR(36),
    started_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at  TIMESTAMP,
    status        VARCHAR(20) NOT NULL DEFAULT 'running'
                  CHECK (status IN ('running','success','failed','partial')),
    triggered_by  VARCHAR(50) NOT NULL DEFAULT 'manual',
    dry_run       BOOLEAN NOT NULL DEFAULT FALSE,
    error_message TEXT,
    created_date  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by    VARCHAR(50) NOT NULL DEFAULT 'etl_user'
);
CREATE INDEX ix_tjobrun_started_at ON dba.tjobrun(started_at DESC);
CREATE INDEX ix_tjobrun_status     ON dba.tjobrun(status);
CREATE INDEX ix_tjobrun_job_name   ON dba.tjobrun(job_name);
