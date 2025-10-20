import pytest
from fastapi.testclient import TestClient
from pathlib import Path
import yaml
import tempfile
import os

from adapter.main import app
from adapter.api.config_routes import init_config_routes


@pytest.fixture
def test_config_dir():
    """Create test config directory with sample config"""
    with tempfile.TemporaryDirectory() as temp_dir:
        config_dir = Path(temp_dir) / "configs"
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
                    "v1_path": "old_field1",
                    "approved": False,
                    "edited": False
                }
            ]
        }

        config_file = config_dir / "test_config.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(test_config, f)

        yield config_dir


@pytest.fixture
def client(test_config_dir):
    """Create test client with initialized config routes"""
    # Load test config
    from adapter.config_loader import ConfigLoader
    from adapter.models import MappingConfig

    config_loader = ConfigLoader(test_config_dir)
    configs = config_loader.load_all_configs()

    # Initialize config routes
    init_config_routes(str(test_config_dir), configs)

    with TestClient(app) as client:
        yield client


def test_list_configs(client):
    """Test listing all configs"""
    response = client.get("/configs")

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert isinstance(data["data"], list)

    # Find test config
    test_config = next((c for c in data["data"] if c["id"] == "test_config"), None)
    assert test_config is not None
    assert test_config["total_mappings"] == 1
    assert test_config["approved_mappings"] == 0


def test_get_config(client):
    """Test getting a specific config"""
    response = client.get("/configs/test_config")

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["endpoint"]["v2_path"] == "/api/v2/test"
    assert len(data["data"]["v1_calls"]) == 1
    assert len(data["data"]["field_mappings"]) == 1


def test_get_config_not_found(client):
    """Test getting a non-existent config"""
    response = client.get("/configs/nonexistent")

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is False
    assert "not found" in data["error"].lower()


def test_update_config(client):
    """Test updating a config"""
    # Get existing config
    response = client.get("/configs/test_config")
    config = response.json()["data"]

    # Modify it - approve the first mapping
    config["field_mappings"][0]["approved"] = True

    # Update
    response = client.put("/configs/test_config", json=config)

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True

    # Verify the change
    response = client.get("/configs/test_config")
    updated = response.json()["data"]
    assert updated["field_mappings"][0]["approved"] is True


def test_update_config_invalid(client):
    """Test updating with invalid config"""
    invalid_config = {
        "version": "1.0",
        # Missing required fields
    }

    response = client.put("/configs/test_config", json=invalid_config)

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is False
    assert "invalid" in data["error"].lower()


def test_delete_config(client, test_config_dir):
    """Test deleting a config"""
    # Create a config to delete
    delete_config = {
        "version": "1.0",
        "endpoint": {"v2_path": "/delete", "v2_method": "GET"},
        "v1_calls": [{"name": "test", "endpoint": "/test", "method": "GET"}],
        "field_mappings": [{
            "v2_path": "f",
            "source": "test",
            "v1_path": "f",
            "approved": False,
            "edited": False
        }]
    }

    delete_file = test_config_dir / "to_delete.yaml"
    with open(delete_file, 'w') as f:
        yaml.dump(delete_config, f)

    # Delete it
    response = client.delete("/configs/to_delete")

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "deleted" in data["message"].lower()


def test_delete_config_not_found(client):
    """Test deleting a non-existent config"""
    response = client.delete("/configs/nonexistent")

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is False
    assert "not found" in data["error"].lower()


def test_export_config_yaml(client):
    """Test exporting config as YAML"""
    response = client.get("/configs/test_config/export")

    assert response.status_code == 200
    # Should return raw YAML string
    yaml_content = response.text
    assert "endpoint:" in yaml_content
    assert "field_mappings:" in yaml_content
    assert "v1_calls:" in yaml_content


def test_cors_headers(client):
    """Test that CORS headers are present"""
    response = client.options("/configs", headers={"Origin": "http://localhost:3000"})

    assert response.status_code == 200
    assert "access-control-allow-origin" in response.headers