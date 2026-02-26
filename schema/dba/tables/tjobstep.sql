CREATE TABLE dba.tjobstep (
    jobstepid    SERIAL PRIMARY KEY,
    jobrunid     INT NOT NULL REFERENCES dba.tjobrun(jobrunid) ON DELETE CASCADE,
    step_name    VARCHAR(50) NOT NULL,
    step_order   SMALLINT NOT NULL,
    display_name VARCHAR(100) NOT NULL,
    started_at   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    status       VARCHAR(20) NOT NULL DEFAULT 'running'
                 CHECK (status IN ('pending','running','success','failed','skipped')),
    records_in   INT,
    records_out  INT,
    step_runtime FLOAT,
    log_run_uuid VARCHAR(36),
    message      TEXT
);
CREATE INDEX ix_tjobstep_jobrunid ON dba.tjobstep(jobrunid);
