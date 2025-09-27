"""Database configuration and settings."""

import os
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class DatabaseConfig:
    """Configuration class for the database settings."""

    # Database path settings
    db_path: str = "./src/web_ui/data/chroma_db"
    collection_prefix: str = "webui_"

    # Connection settings
    max_connections: int = 10
    connection_timeout: int = 30

    # Feature flags
    enable_telemetry: bool = False
    enable_logging: bool = True
    log_level: str = "INFO"

    # Performance settings
    batch_size: int = 100
    cache_size: int = 1000

    # Security settings
    allow_reset: bool = True
    auto_backup: bool = False
    backup_interval_hours: int = 24

    @classmethod
    def from_env(cls) -> 'DatabaseConfig':
        """Create configuration from environment variables."""
        return cls(
            db_path=os.getenv('CHROMA_DB_PATH', cls.db_path),
            collection_prefix=os.getenv('CHROMA_COLLECTION_PREFIX', cls.collection_prefix),
            max_connections=int(os.getenv('CHROMA_MAX_CONNECTIONS', str(cls.max_connections))),
            connection_timeout=int(os.getenv('CHROMA_CONNECTION_TIMEOUT', str(cls.connection_timeout))),
            enable_telemetry=os.getenv('CHROMA_ENABLE_TELEMETRY', 'false').lower() == 'true',
            enable_logging=os.getenv('CHROMA_ENABLE_LOGGING', 'true').lower() == 'true',
            log_level=os.getenv('CHROMA_LOG_LEVEL', cls.log_level),
            batch_size=int(os.getenv('CHROMA_BATCH_SIZE', str(cls.batch_size))),
            cache_size=int(os.getenv('CHROMA_CACHE_SIZE', str(cls.cache_size))),
            allow_reset=os.getenv('CHROMA_ALLOW_RESET', 'true').lower() == 'true',
            auto_backup=os.getenv('CHROMA_AUTO_BACKUP', 'false').lower() == 'true',
            backup_interval_hours=int(os.getenv('CHROMA_BACKUP_INTERVAL_HOURS', str(cls.backup_interval_hours)))
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            'db_path': self.db_path,
            'collection_prefix': self.collection_prefix,
            'max_connections': self.max_connections,
            'connection_timeout': self.connection_timeout,
            'enable_telemetry': self.enable_telemetry,
            'enable_logging': self.enable_logging,
            'log_level': self.log_level,
            'batch_size': self.batch_size,
            'cache_size': self.cache_size,
            'allow_reset': self.allow_reset,
            'auto_backup': self.auto_backup,
            'backup_interval_hours': self.backup_interval_hours
        }

    def validate(self) -> None:
        """Validate configuration settings."""
        # Ensure database path is valid
        db_path = Path(self.db_path)
        try:
            db_path.parent.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            raise ValueError(f"Invalid database path '{self.db_path}': {e}")

        # Validate numeric settings
        if self.max_connections < 1:
            raise ValueError("max_connections must be at least 1")

        if self.connection_timeout < 1:
            raise ValueError("connection_timeout must be at least 1")

        if self.batch_size < 1:
            raise ValueError("batch_size must be at least 1")

        if self.cache_size < 0:
            raise ValueError("cache_size must be non-negative")

        if self.backup_interval_hours < 1:
            raise ValueError("backup_interval_hours must be at least 1")

        # Validate log level
        valid_log_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if self.log_level.upper() not in valid_log_levels:
            raise ValueError(f"log_level must be one of {valid_log_levels}")


# Environment variable documentation
ENV_VARS_DOCS = {
    'CHROMA_DB_PATH': 'Path to the ChromaDB database directory (default: ./src/web_ui/data/chroma_db)',
    'CHROMA_COLLECTION_PREFIX': 'Prefix for collection names (default: webui_)',
    'CHROMA_MAX_CONNECTIONS': 'Maximum number of connections (default: 10)',
    'CHROMA_CONNECTION_TIMEOUT': 'Connection timeout in seconds (default: 30)',
    'CHROMA_ENABLE_TELEMETRY': 'Enable ChromaDB telemetry (default: false)',
    'CHROMA_ENABLE_LOGGING': 'Enable database logging (default: true)',
    'CHROMA_LOG_LEVEL': 'Logging level (default: INFO)',
    'CHROMA_BATCH_SIZE': 'Batch size for bulk operations (default: 100)',
    'CHROMA_CACHE_SIZE': 'Cache size for collections (default: 1000)',
    'CHROMA_ALLOW_RESET': 'Allow database reset operations (default: true)',
    'CHROMA_AUTO_BACKUP': 'Enable automatic backups (default: false)',
    'CHROMA_BACKUP_INTERVAL_HOURS': 'Backup interval in hours (default: 24)'
}


def get_default_config() -> DatabaseConfig:
    """Get the default database configuration."""
    return DatabaseConfig.from_env()


def create_env_file_template(output_path: Optional[str] = None) -> str:
    """Create a template .env file with database configuration options."""
    template_lines = [
        "# ChromaDB Configuration",
        "# Uncomment and modify the values below as needed",
        ""
    ]

    for env_var, description in ENV_VARS_DOCS.items():
        template_lines.append(f"# {description}")
        template_lines.append(f"# {env_var}=")
        template_lines.append("")

    template_content = "\n".join(template_lines)

    if output_path:
        with open(output_path, 'w') as f:
            f.write(template_content)

    return template_content