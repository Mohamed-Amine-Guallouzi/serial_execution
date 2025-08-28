# config_loader.py
import yaml
import os
from typing import Any, Dict, Optional

class ConfigLoader:
    def __init__(self, config_path: str = 'config.yml'):
        self.config_path = config_path
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        try:
            with open(self.config_path, 'r') as file:
                return yaml.safe_load(file) or {}
        except FileNotFoundError:
            raise Exception(f"Config file not found: {self.config_path}")
        except yaml.YAMLError as e:
            raise Exception(f"Error parsing config file: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by dot notation key"""
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def get_int(self, key: str, default: int = 0) -> int:
        """Get integer configuration value"""
        value = self.get(key, default)
        return int(value) if value is not None else default
    
    def get_bool(self, key: str, default: bool = False) -> bool:
        """Get boolean configuration value"""
        value = self.get(key, default)
        if isinstance(value, bool):
            return value
        return str(value).lower() in ('true', '1', 'yes', 'y')
    
    def get_list(self, key: str, default: list = None) -> list:
        """Get list configuration value"""
        if default is None:
            default = []
        value = self.get(key, default)
        return value if isinstance(value, list) else default

# Global config instance
config = ConfigLoader()