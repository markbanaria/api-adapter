from fastapi import APIRouter, HTTPException
from pathlib import Path
from typing import List, Dict, Any
import yaml
from pydantic import ValidationError
import logging

from ..models import MappingConfig
from ..config_loader import ConfigLoader

router = APIRouter(prefix="/configs", tags=["configs"])

# Global config loader instance
config_loader: ConfigLoader = None
endpoint_configs: Dict[str, MappingConfig] = {}

logger = logging.getLogger(__name__)


def init_config_routes(config_dir_path: str, configs: Dict[str, MappingConfig]):
    """Initialize config loader with directory and loaded configs"""
    global config_loader, endpoint_configs
    config_loader = ConfigLoader(Path(config_dir_path))
    endpoint_configs = configs


@router.get("", response_model=Dict[str, Any])
async def get_configs():
    """Get all mapping configurations summary"""
    logger.info("get_configs called")

    if not config_loader:
        logger.error("Config loader not initialized")
        raise HTTPException(status_code=500, detail="Config loader not initialized")

    logger.info(f"Config loader directory: {config_loader.config_dir}")

    # Reload configs from filesystem to catch any newly created ones
    try:
        logger.info("Attempting to load all configs from filesystem")
        current_configs = config_loader.load_all_configs()
        logger.info(f"Successfully loaded {len(current_configs)} configs: {list(current_configs.keys())}")
    except Exception as e:
        logger.error(f"Failed to load configs: {e}")
        current_configs = {}

    configs = []
    for config_id, config in current_configs.items():
        logger.info(f"Processing config: {config_id}")
        # Calculate stats
        approved_count = sum(1 for mapping in config.field_mappings if mapping.approved)
        total_count = len(config.field_mappings)

        configs.append({
            "id": config_id,
            "endpoint": f"{config.endpoint.v2_method} {config.endpoint.v2_path}",
            "total_mappings": total_count,
            "approved_mappings": approved_count,
            "confidence_score": config.metadata.confidence_score if config.metadata else 0.0,
            "generated_at": config.metadata.generated_at if config.metadata else None,
            "v1_calls_count": len(config.v1_calls),
            "has_ambiguous": bool(config.metadata and config.metadata.ambiguous_mappings)
        })

    logger.info(f"Returning {len(configs)} config summaries")
    return {"success": True, "data": configs}


@router.get("/{config_id}", response_model=Dict[str, Any])
async def get_config(config_id: str):
    """Get a specific config by ID"""
    logger.info(f"get_config called for config_id: {config_id}")

    if not config_loader:
        logger.error("Config loader not initialized")
        raise HTTPException(status_code=500, detail="Config loader not initialized")

    logger.info(f"Config loader directory: {config_loader.config_dir}")

    # Try to reload configs to catch newly created ones
    try:
        logger.info("Attempting to load all configs from filesystem")
        current_configs = config_loader.load_all_configs()
        logger.info(f"Successfully loaded {len(current_configs)} configs: {list(current_configs.keys())}")
        if config_id in current_configs:
            logger.info(f"Found config {config_id} in filesystem")
            return {"success": True, "data": current_configs[config_id].dict()}
        else:
            logger.warning(f"Config {config_id} not found in filesystem configs")
    except Exception as e:
        logger.error(f"Failed to load configs from filesystem: {e}")

    # Fallback to in-memory configs
    logger.info(f"Checking in-memory configs: {list(endpoint_configs.keys())}")
    if config_id in endpoint_configs:
        logger.info(f"Found config {config_id} in memory")
        return {"success": True, "data": endpoint_configs[config_id].dict()}

    logger.error(f"Configuration {config_id} not found anywhere")
    return {"success": False, "error": "Configuration not found"}


@router.put("/{config_id}", response_model=Dict[str, Any])
async def update_config(config_id: str, updated_config: dict):
    """Update a config"""
    if not config_loader:
        raise HTTPException(status_code=500, detail="Config loader not initialized")

    if config_id not in endpoint_configs:
        return {"success": False, "error": "Configuration not found"}

    try:
        # Update the configuration
        endpoint_configs[config_id] = MappingConfig(**updated_config)

        # Save to file (optional - for persistence)
        config_file = Path(config_loader.config_dir) / f"{config_id}.yaml"
        if config_file.exists():
            try:
                with open(config_file, 'w') as f:
                    yaml.dump(updated_config, f, default_flow_style=False)
            except ImportError:
                # PyYAML not available, skip file save
                pass

        return {"success": True, "message": "Configuration updated successfully"}
    except Exception as e:
        return {"success": False, "error": f"Invalid configuration: {str(e)}"}


@router.delete("/{config_id}")
async def delete_config(config_id: str):
    """Delete a config"""
    if not config_loader:
        raise HTTPException(status_code=500, detail="Config loader not initialized")

    if config_id not in endpoint_configs:
        return {"success": False, "error": "Configuration not found"}

    try:
        # Remove from memory
        del endpoint_configs[config_id]

        # Remove from file if it exists
        config_file = Path(config_loader.config_dir) / f"{config_id}.yaml"
        if config_file.exists():
            config_file.unlink()

        return {"success": True, "message": f"Configuration '{config_id}' deleted successfully"}
    except Exception as e:
        return {"success": False, "error": f"Failed to delete configuration: {str(e)}"}


@router.get("/{config_id}/export")
async def export_config_yaml(config_id: str):
    """Export configuration as YAML"""
    if not config_loader:
        raise HTTPException(status_code=500, detail="Config loader not initialized")

    if config_id not in endpoint_configs:
        return {"success": False, "error": "Configuration not found"}

    try:
        config_dict = endpoint_configs[config_id].dict()
        yaml_content = yaml.dump(config_dict, default_flow_style=False)
        return yaml_content
    except ImportError:
        # PyYAML not available, return simple error
        return {"success": False, "error": "YAML export not available"}