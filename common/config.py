"""
Configuration management for Tangerine ETL pipeline.

Uses pydantic-settings for type-safe configuration loading from environment variables.
"""

from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseConfig(BaseSettings):
    """Database connection configuration."""

    model_config = SettingsConfigDict(env_prefix='', case_sensitive=False)

    db_url: str = Field(..., description="PostgreSQL connection URL")
    pool_size: int = Field(10, description="Connection pool size")
    pool_max_overflow: int = Field(20, description="Max overflow connections")
    pool_timeout: int = Field(30, description="Pool connection timeout in seconds")

    @property
    def is_configured(self) -> bool:
        """Check if database is configured."""
        return bool(self.db_url)


class ETLConfig(BaseSettings):
    """ETL application configuration."""

    model_config = SettingsConfigDict(env_prefix='ETL_', case_sensitive=False)

    log_level: str = Field("INFO", description="Logging level (DEBUG, INFO, WARNING, ERROR)")
    log_dir: str = Field("/app/logs", description="Directory for log files")
    enable_db_logging: bool = Field(True, description="Enable database logging to tlogentry")
    enable_file_logging: bool = Field(True, description="Enable file logging")

    # ETL specific settings
    batch_size: int = Field(1000, description="Default batch size for bulk operations")
    retry_attempts: int = Field(3, description="Default number of retry attempts")
    retry_delay: int = Field(5, description="Delay between retries in seconds")

    # API settings
    api_timeout: int = Field(30, description="API request timeout in seconds")
    api_rate_limit: int = Field(100, description="Max API requests per minute")


class Config:
    """
    Global configuration container.

    Usage:
        from common.config import get_config
        config = get_config()
        db_url = config.database.db_url
    """

    def __init__(self):
        self.database = DatabaseConfig()
        self.etl = ETLConfig()

    def __repr__(self) -> str:
        return f"Config(database={self.database.is_configured}, log_level={self.etl.log_level})"


_config_instance: Optional[Config] = None


def get_config() -> Config:
    """
    Get singleton configuration instance.

    Returns:
        Config: Global configuration object
    """
    global _config_instance
    if _config_instance is None:
        _config_instance = Config()
    return _config_instance


def reload_config() -> Config:
    """
    Reload configuration from environment (useful for testing).

    Returns:
        Config: New configuration object
    """
    global _config_instance
    _config_instance = Config()
    return _config_instance
