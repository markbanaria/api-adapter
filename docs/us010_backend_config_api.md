# User Story 010: Backend Config Management API

## Story
As a frontend developer, I want REST API endpoints to list, view, and update mapping configurations so that the UI can interact with configs.

## Acceptance Criteria
- [ ] GET /configs - List all config IDs
- [ ] GET /configs/{id} - Get specific config
- [ ] PUT /configs/{id} - Update config
- [ ] Configs served from YAML files
- [ ] CORS enabled for frontend
- [ ] Validation on config updates
- [ ] Error handling for missing configs

## Technical Details

### Config API Routes (backend/src/adapter/api/config_routes.py)

```python
from fastapi import APIRouter, HTTPException
from pathlib import Path
from typing import List
import yaml
from pydantic import ValidationError

from ..models import MappingConfig
from ..config_loader import ConfigLoader

router = APIRouter(prefix="/configs", tags=["configs"])

# Global config loader instance
config_loader: ConfigLoader = None


def init_config_routes(config_dir: Path):
    """Initialize config loader with directory"""
    global config_loader
    config_loader = ConfigLoader(config_dir)


@router.get("", response_model=List[str])
async def list_configs():
    """List all available config IDs"""
    if not config_loader:
        raise HTTPException(status_code=500, detail="Config loader not initialized")
    
    config_files = list(config_loader.config_dir.glob("*.yaml"))
    config_ids = [f.stem for f in config_files]
    
    return sorted(config_ids)


@router.get("/{config_id}", response_model=MappingConfig)
async def get_config(config_id: str):
    """Get a specific config by ID"""
    if not config_loader:
        raise HTTPException(status_code=500, detail="Config loader not initialized")
    
    try:
        config = config_loader.load_config(f"{config_id}.yaml")
        return config
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Config '{config_id}' not found")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid config: {e}")


@router.put("/{config_id}", response_model=MappingConfig)
async def update_config(config_id: str, config: MappingConfig):
    """Update a config"""
    if not config_loader:
        raise HTTPException(status_code=500, detail="Config loader not initialized")
    
    config_path = config_loader.config_dir / f"{config_id}.yaml"
    
    # Validate config
    try:
        validated_config = MappingConfig(**config.model_dump())
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=f"Invalid config: {e}")
    
    # Save to file
    with open(config_path, 'w') as f:
        yaml.dump(validated_config.model_dump(), f, default_flow_style=False, sort_keys=False)
    
    return validated_config


@router.delete("/{config_id}")
async def delete_config(config_id: str):
    """Delete a config"""
    if not config_loader:
        raise HTTPException(status_code=500, detail="Config loader not initialized")
    
    config_path = config_loader.config_dir / f"{config_id}.yaml"
    
    if not config_path.exists():
        raise HTTPException(status_code=404, detail=f"Config '{config_id}' not found")
    
    config_path.unlink()
    
    return {"message": f"Config '{config_id}' deleted successfully"}
```

### Update Main App (backend/src/adapter/main.py)

Add to the main.py file:

```python
from fastapi.middleware.cors import CORSMiddleware
from .api.config_routes import router as config_router, init_config_routes

# After app creation, add CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Next.js dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In the lifespan startup section, initialize config routes
@asynccontextmanager
async def lifespan(app: FastAPI):
    # ... existing startup code ...
    
    # Initialize config API routes
    init_config_routes(config_dir)
    
    yield
    
    # ... existing shutdown code ...

# Include config routes
app.include_router(config_router)
```

### Tests (backend/tests/test_config_api.py)

```python
import pytest
from fastapi.testclient import TestClient
from pathlib import Path
import yaml

from adapter.main import app
from adapter.api.config_routes import init_config_routes


@pytest.fixture
def test_config_dir(tmp_path):
    """Create test config directory with sample config"""
    config_dir = tmp_path / "configs"
    config_dir.mkdir()
    
    # Create a test config
    test_config = {
        "version": "1.0",
        "endpoint": {
            "v2_path": "/api/v2/test",
            "v2_method": "GET"
        },
        "v1_calls": [
            {
                "name": "get_test",
                "endpoint": "/api/v1/test",
                "method": "GET"
            }
        ],
        "field_mappings": [
            {
                "v2_path": "field1",
                "source": "get_test",
                "v1_path": "old_field1"
            }
        ]
    }
    
    config_file = config_dir / "test_config.yaml"
    with open(config_file, 'w') as f:
        yaml.dump(test_config, f)
    
    return config_dir


@pytest.fixture
def client(test_config_dir):
    """Create test client with initialized config routes"""
    init_config_routes(test_config_dir)
    with TestClient(app) as client:
        yield client


def test_list_configs(client):
    """Test listing all configs"""
    response = client.get("/configs")
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert "test_config" in data


def test_get_config(client):
    """Test getting a specific config"""
    response = client.get("/configs/test_config")
    
    assert response.status_code == 200
    data = response.json()
    assert data["endpoint"]["v2_path"] == "/api/v2/test"
    assert len(data["v1_calls"]) == 1
    assert len(data["field_mappings"]) == 1


def test_get_config_not_found(client):
    """Test getting a non-existent config"""
    response = client.get("/configs/nonexistent")
    
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_update_config(client):
    """Test updating a config"""
    # Get existing config
    response = client.get("/configs/test_config")
    config = response.json()
    
    # Modify it
    config["field_mappings"].append({
        "v2_path": "field2",
        "source": "get_test",
        "v1_path": "old_field2"
    })
    
    # Update
    response = client.put("/configs/test_config", json=config)
    
    assert response.status_code == 200
    updated = response.json()
    assert len(updated["field_mappings"]) == 2


def test_update_config_invalid(client):
    """Test updating with invalid config"""
    invalid_config = {
        "version": "1.0",
        # Missing required fields
    }
    
    response = client.put("/configs/test_config", json=invalid_config)
    
    assert response.status_code == 400
    assert "invalid" in response.json()["detail"].lower()


def test_delete_config(client, test_config_dir):
    """Test deleting a config"""
    # Create a config to delete
    delete_config = {
        "version": "1.0",
        "endpoint": {"v2_path": "/delete", "v2_method": "GET"},
        "v1_calls": [{"name": "test", "endpoint": "/test", "method": "GET"}],
        "field_mappings": [{"v2_path": "f", "source": "test", "v1_path": "f"}]
    }
    
    delete_file = test_config_dir / "to_delete.yaml"
    with open(delete_file, 'w') as f:
        yaml.dump(delete_config, f)
    
    # Delete it
    response = client.delete("/configs/to_delete")
    
    assert response.status_code == 200
    assert "deleted" in response.json()["message"].lower()
    
    # Verify it's gone
    assert not delete_file.exists()


def test_delete_config_not_found(client):
    """Test deleting a non-existent config"""
    response = client.delete("/configs/nonexistent")
    
    assert response.status_code == 404
```

## Testing Checklist
- [ ] GET /configs returns list of config IDs
- [ ] GET /configs/{id} returns config JSON
- [ ] GET /configs/{id} returns 404 for missing config
- [ ] PUT /configs/{id} updates config file
- [ ] PUT /configs/{id} validates config schema
- [ ] PUT /configs/{id} returns 400 for invalid config
- [ ] DELETE /configs/{id} removes config file
- [ ] DELETE /configs/{id} returns 404 for missing config
- [ ] CORS headers present in responses

## Definition of Done
- Config API routes implemented
- CORS middleware configured
- All CRUD operations working
- Config validation on updates
- Error handling for all edge cases
- Unit tests passing
- API documented with OpenAPI/Swagger