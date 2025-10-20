import yaml
from pathlib import Path
from typing import Dict
from .models import MappingConfig


class ConfigLoader:
    """Loads and validates YAML mapping configurations"""

    def __init__(self, config_dir: Path):
        self.config_dir = Path(config_dir)
        self._configs: Dict[str, MappingConfig] = {}

    def load_config(self, config_file: str) -> MappingConfig:
        """Load and validate a single config file"""
        config_path = self.config_dir / config_file

        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        try:
            with open(config_path, 'r') as f:
                raw_config = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid config in {config_file}: YAML syntax error - {e}")

        try:
            config = MappingConfig(**raw_config)
            return config
        except Exception as e:
            raise ValueError(f"Invalid config in {config_file}: {e}")

    def load_all_configs(self) -> Dict[str, MappingConfig]:
        """Load all YAML files in config directory"""
        for config_file in self.config_dir.glob("*.yaml"):
            endpoint_id = config_file.stem
            self._configs[endpoint_id] = self.load_config(config_file.name)
        return self._configs

    def get_config_for_endpoint(self, v2_path: str, method: str) -> MappingConfig:
        """Retrieve config for a specific V2 endpoint"""
        for config in self._configs.values():
            if config.endpoint.v2_path == v2_path and config.endpoint.v2_method == method:
                return config
        raise KeyError(f"No config found for {method} {v2_path}")