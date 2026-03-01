# -*- coding: utf-8 -*-
"""
ROMA-01 Trading Analyzer - Configuration Module
"""

import os
import re
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from loguru import logger


class Config(Dict):
    """Configuration object with env var resolution."""
    pass


def load_config(config_path: str) -> Config:
    """
    Load configuration from YAML file.
    
    Args:
        config_path: Path to config file
        
    Returns:
        Config object with resolved environment variables
    """
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    
    with open(path, "r", encoding="utf-8") as f:
        config_dict = yaml.safe_load(f)
    
    # Resolve environment variables
    config = resolve_env_vars(config_dict)
    
    logger.info(f"Loaded configuration from {path}")
    return Config(config)


def resolve_env_vars(config: Any) -> Any:
    """
    Resolve ${ENV_VAR} placeholders in configuration.
    
    Args:
        config: Configuration dict/list/string
        
    Returns:
        Configuration with resolved environment variables
    """
    if isinstance(config, str):
        # Match ${VAR_NAME}
        matches = re.findall(r'\$\{([^}]+)\}', config)
        result = config
        for match in matches:
            env_value = os.getenv(match, "")
            result = result.replace(f"${{{match}}}", env_value)
        return result
    elif isinstance(config, dict):
        return {k: resolve_env_vars(v) for k, v in config.items()}
    elif isinstance(config, list):
        return [resolve_env_vars(item) for item in config]
    else:
        return config


def get_default_config() -> Dict:
    """Get default configuration template."""
    return {
        "system": {
            "scan_interval_minutes": 3,
            "prompt_language": "zh",
        },
        "accounts": [
            {
                "id": "aster-acc-01",
                "name": "Aster Account 01",
                "dex_type": "aster",
                "user": "${ASTER_USER}",
                "signer": "${ASTER_SIGNER}",
                "private_key": "${ASTER_PRIVATE_KEY}",
                "testnet": False,
            }
        ],
        "models": [
            {
                "id": "deepseek-v3.1",
                "provider": "deepseek",
                "api_key": "${DEEPSEEK_API_KEY}",
                "model": "deepseek-chat",
                "temperature": 0.15,
                "max_tokens": 4000,
            }
        ],
        "agents": [
            {
                "id": "deepseek-aster-01",
                "name": "DeepSeek Analyzer",
                "enabled": True,
                "account_id": "aster-acc-01",
                "model_id": "deepseek-v3.1",
                "strategy": {
                    "default_coins": ["BTCUSDT", "ETHUSDT", "SOLUSDT"],
                    "risk_management": {
                        "max_positions": 3,
                        "max_leverage": 10,
                        "max_position_size_pct": 30,
                        "max_total_position_pct": 80,
                        "stop_loss_pct": 3,
                        "take_profit_pct": 10,
                    }
                }
            }
        ]
    }


def create_default_config(output_path: str = "config/roma_config.yaml"):
    """
    Create default configuration file.
    
    Args:
        output_path: Path to write config file
    """
    config = get_default_config()
    
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
    
    logger.info(f"Created default configuration at {path}")
