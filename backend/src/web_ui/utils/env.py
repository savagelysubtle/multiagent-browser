"""
Environment Variable Loader for Web-UI Application.

This module provides intelligent environment variable loading with support for:
- Multiple environment files (.env.development, .env)
- Environment-specific configuration
- Proper fallback mechanisms
- Comprehensive logging
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set

from ..utils.logging_config import get_logger

logger = get_logger(__name__)


class EnvironmentLoader:
    """
    Intelligent environment variable loader.

    Loads environment variables from multiple sources with proper precedence:
    1. System environment variables (highest priority)
    2. Development environment file (.env.development)
    3. Production environment file (.env)
    4. Default values (lowest priority)
    """

    def __init__(self, project_root: Optional[Path] = None):
        """Initialize the environment loader.

        Args:
            project_root: Root directory of the project. If None, auto-detects.
        """
        self.project_root = project_root or self._detect_project_root()
        self.loaded_files: List[Path] = []
        self.loaded_variables: Set[str] = set()

    def _detect_project_root(self) -> Path:
        """Detect the project root directory by looking for known files."""
        current_path = Path.cwd()

        # Look for common project markers
        markers = ['pyproject.toml', '.env', '.env.development', 'backend/', 'frontend/']

        for marker in markers:
            if (current_path / marker).exists():
                return current_path

        # Fallback to current directory
        return current_path

    def _find_env_files(self) -> List[Path]:
        """Find available environment files in priority order."""
        env_files = []

        # Development file (highest priority after system env)
        dev_file = self.project_root / '.env.development'
        if dev_file.exists():
            env_files.append(dev_file)

        # Production file (fallback)
        prod_file = self.project_root / '.env'
        if prod_file.exists():
            env_files.append(prod_file)

        return env_files

    def _load_env_file(self, env_file: Path) -> Dict[str, str]:
        """Load environment variables from a specific file.

        Args:
            env_file: Path to the environment file

        Returns:
            Dictionary of loaded variables
        """
        loaded_vars = {}

        try:
            with open(env_file, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()

                    # Skip empty lines and comments
                    if not line or line.startswith('#'):
                        continue

                    # Parse key=value pairs
                    if '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip().strip('"\'')  # Remove quotes

                        # Only load if not already set by system environment
                        if key not in os.environ and key not in self.loaded_variables:
                            os.environ[key] = value
                            loaded_vars[key] = value
                            self.loaded_variables.add(key)

        except Exception as e:
            logger.warning(f"Failed to load environment file {env_file}: {e}")

        return loaded_vars

    def load_environment(self, verbose: bool = True) -> Dict[str, Dict[str, str]]:
        """
        Load environment variables from all available sources.

        Args:
            verbose: Whether to log detailed information about loaded variables

        Returns:
            Dictionary mapping source names to loaded variables
        """
        all_loaded = {
            'system': {},
            'development': {},
            'production': {}
        }

        # 1. System environment variables (already loaded, just catalog)
        system_vars = {}
        for key, value in os.environ.items():
            if key not in self.loaded_variables:
                system_vars[key] = value
                self.loaded_variables.add(key)

        if system_vars:
            all_loaded['system'] = system_vars
            if verbose:
                logger.info(f"Loaded {len(system_vars)} system environment variables")

        # 2. Environment files
        env_files = self._find_env_files()

        for i, env_file in enumerate(env_files):
            if env_file.name == '.env.development':
                source_name = 'development'
            else:
                source_name = 'production'

            loaded_vars = self._load_env_file(env_file)
            all_loaded[source_name] = loaded_vars

            if loaded_vars:
                self.loaded_files.append(env_file)
                if verbose:
                    logger.info(f"Loaded {len(loaded_vars)} variables from {env_file.name}")

        # 3. Log summary
        total_loaded = len(self.loaded_variables)
        if verbose:
            logger.info(f"Environment loading complete. Total: {total_loaded} variables")
            if self.loaded_files:
                logger.info(f"Loaded files: {[f.name for f in self.loaded_files]}")

        return all_loaded

    def get_env_var(self, key: str, default: str = None) -> str:
        """Get an environment variable with optional default.

        Args:
            key: Environment variable name
            default: Default value if variable not found

        Returns:
            Environment variable value or default
        """
        return os.getenv(key, default)

    def require_env_var(self, key: str) -> str:
        """Get a required environment variable, raising an error if not found.

        Args:
            key: Environment variable name

        Returns:
            Environment variable value

        Raises:
            ValueError: If the environment variable is not set
        """
        value = os.getenv(key)
        if value is None:
            raise ValueError(f"Required environment variable '{key}' is not set")
        return value

    def get_loaded_files(self) -> List[Path]:
        """Get list of successfully loaded environment files."""
        return self.loaded_files.copy()

    def is_variable_loaded(self, key: str) -> bool:
        """Check if a variable was loaded from environment files."""
        return key in self.loaded_variables


# Global instance for convenience
_env_loader: Optional[EnvironmentLoader] = None


def get_env_loader(project_root: Optional[Path] = None) -> EnvironmentLoader:
    """Get or create the global environment loader instance."""
    global _env_loader
    if _env_loader is None:
        _env_loader = EnvironmentLoader(project_root)
    return _env_loader


def load_environment_variables(project_root: Optional[Path] = None, verbose: bool = True) -> Dict[str, Dict[str, str]]:
    """
    Convenience function to load environment variables.

    Args:
        project_root: Project root directory (auto-detected if None)
        verbose: Whether to log detailed information

    Returns:
        Dictionary of loaded variables by source
    """
    loader = get_env_loader(project_root)
    return loader.load_environment(verbose=verbose)


def get_env_var(key: str, default: str = None) -> str:
    """Get an environment variable with optional default."""
    return get_env_loader().get_env_var(key, default)


def require_env_var(key: str) -> str:
    """Get a required environment variable."""
    return get_env_loader().require_env_var(key)


def get_loaded_env_files() -> List[Path]:
    """Get list of loaded environment files."""
    return get_env_loader().get_loaded_files()