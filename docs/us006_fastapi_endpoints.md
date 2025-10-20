# User Story 006: FastAPI V2 Endpoints

## Story
As a developer, I want to create FastAPI V2 endpoints that integrate the orchestrator, transformer, and response builder to serve complete V2 API responses.

## Acceptance Criteria
- [ ] FastAPI app loads all mapping configs on startup
- [ ] V2 endpoints dynamically registered from configs
- [ ] Request parameters extracted (path, query, body)
- [ ] Orchestrator called to fetch V1 data
- [ ] ResponseBuilder constructs V2 response
- [ ] Proper error handling with HTTP status codes
- [ ] Request correlation logging implemented
- [ ] Health check endpoint exists
- [ ] Integration tests cover end-to-end flow

## Technical Details

### Main FastAPI App (backend/src/adapter/main.py)

```python
from fastapi import FastAPI, Request, HTTPException, Path, Query
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
from pathlib import Path as FilePath
from typing import Dict, Any
import json
from uuid import uuid4

from .config_loader import ConfigLoader
from .orchestrator import V1Orchestrator, V1OrchestratorError
from .response_builder import V2ResponseBuilder, ResponseBuilderError
from .models import MappingConfig

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'
)
logger = logging.getLogger(__name__)


# Global state
config_loader: ConfigLoader
orchestrator: V1Orchestrator
response_builder: V2ResponseBuilder
endpoint_configs: Dict[str, MappingConfig] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown logic"""
    global config_loader, orchestrator, response_builder, endpoint_configs
    
    # Startup
    logger.info("Starting Insurance API Adapter...")
    
    # Load configurations
    config_dir = FilePath(__file__).parent.parent.parent / "configs"
    config_loader = ConfigLoader(config_dir)
    endpoint_configs = config_loader.load_all_configs()
    
    logger.info(f"Loaded {len(endpoint_configs)} endpoint configurations")
    
    # Initialize orchestrator
    v1_base_url = "http://localhost:8001"  # TODO: Load from env
    orchestrator = V1Orchestrator(v1_base_url=v1_base_url)
    
    # Initialize response builder
    response_builder = V2ResponseBuilder()
    
    # Register dynamic endpoints
    register_v2_endpoints(app, endpoint_configs)
    
    logger.info("Insurance API Adapter started successfully")
    
    yield
    
    # Shutdown
    await orchestrator.close()
    logger.info("Insurance API Adapter shut down")


app = FastAPI(
    title="Insurance API V2 Adapter",
    description="V1 to V2 API adapter for Life & ILP insurance products",
    version="0.1.0",
    lifespan=lifespan
)


def register_v2_endpoints(app: FastAPI, configs: Dict[str, MappingConfig]):
    """Dynamically register V2 endpoints from configs"""
    
    for endpoint_id, config in configs.items():
        path = config.endpoint.v2_path
        method = config.endpoint.v2_method.lower()
        
        # Create endpoint handler
        async def endpoint_handler(request: Request, config=config):
            return await handle_v2_request(request, config)
        
        # Register route
        app.add_api_route(
            path=path,
            endpoint=endpoint_handler,
            methods=[method],
            name=f"{method}_{endpoint_id}",
            response_model=None
        )
        
        logger.info(f"Registered endpoint: {method.upper()} {path}")


async def handle_v2_request(request: Request, config: MappingConfig) -> JSONResponse:
    """Handle a V2 API request"""
    
    request_id = str(uuid4())
    
    # Extract all parameters
    try:
        v2_params = await extract_v2_params(request, config)
    except Exception as e:
        logger.error(
            "Failed to extract request parameters",
            extra={"request_id": request_id, "error": str(e)}
        )
        return JSONResponse(
            status_code=400,
            content={
                "error": "Invalid request parameters",
                "code": "INVALID_REQUEST",
                "request_id": request_id
            }
        )
    
    logger.info(
        f"Processing V2 request: {config.endpoint.v2_method} {config.endpoint.v2_path}",
        extra={
            "request_id": request_id,
            "params": v2_params
        }
    )
    
    try:
        # Orchestrate V1 calls
        v1_responses = await orchestrator.orchestrate(config, v2_params)
        
        # Build V2 response
        v2_response = response_builder.build_response(config, v1_responses)
        
        logger.info(
            "V2 request completed successfully",
            extra={
                "request_id": request_id,
                "v1_calls": list(v1_responses.keys())
            }
        )
        
        # Add request ID to response headers
        return JSONResponse(
            content=v2_response,
            headers={"X-Request-ID": request_id}
        )
        
    except V1OrchestratorError as e:
        logger.error(
            f"V1 orchestration failed: {e}",
            extra={
                "request_id": request_id,
                "status_code": e.status_code,
                "details": e.details
            }
        )
        
        error_messages = {
            404: "Resource not found in legacy system",
            502: "Legacy system error",
            504: "Legacy system timeout"
        }
        
        return JSONResponse(
            status_code=e.status_code,
            content={
                "error": error_messages.get(e.status_code, "API error"),
                "code": f"V1_ERROR_{e.status_code}",
                "request_id": request_id,
                "details": e.details
            }
        )
        
    except ResponseBuilderError as e:
        logger.error(
            f"Response building failed: {e}",
            extra={"request_id": request_id}
        )
        
        return JSONResponse(
            status_code=500,
            content={
                "error": "Failed to transform response",
                "code": "TRANSFORMATION_ERROR",
                "request_id": request_id
            }
        )
        
    except Exception as e:
        logger.exception(
            f"Unexpected error: {e}",
            extra={"request_id": request_id}
        )
        
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "code": "INTERNAL_ERROR",
                "request_id": request_id
            }
        )


async def extract_v2_params(request: Request, config: MappingConfig) -> Dict[str, Any]:
    """Extract all parameters from V2 request"""
    params = {}
    
    # Path parameters
    params.update(request.path_params)
    
    # Query parameters
    params.update(dict(request.query_params))
    
    # Body parameters (if POST/PUT/PATCH)
    if request.method in ["POST", "PUT", "PATCH"]:
        try:
            body = await request.json()
            params.update(body)
        except json.JSONDecodeError:
            pass  # No body or invalid JSON
    
    return params


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "insurance-api-adapter",
        "version": "0.1.0",
        "endpoints_loaded": len(endpoint_configs)
    }


@app.get("/")
async def root():
    """Root endpoint with API info"""
    return {
        "service": "Insurance API V2 Adapter",
        "version": "0.1.0",
        "endpoints": [
            {
                "path": config.endpoint.v2_path,
                "method": config.endpoint.v2_method
            }
            for config in endpoint_configs.values()
        ]
    }
```

### Integration Tests (backend/tests/test_integration.py)

```python
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from pathlib import Path
import yaml

from adapter.main import app


@pytest.fixture
def test_config(tmp_path):
    """Create a test config file"""
    config_yaml = """
version: "1.0"
endpoint:
  v2_path: "/api/v2/policies/{policyId}"
  v2_method: "GET"

v1_calls:
  - name: "get_policy"
    endpoint: "/api/v1/policy/{id}"
    method: "GET"
    params:
      path:
        - v2_param: "policyId"
          v1_param: "id"
          location: "path"

field_mappings:
  - v2_path: "policyNumber"
    source: "get_policy"
    v1_path: "policy_num"
  
  - v2_path: "insured.name"
    source: "get_policy"
    transform: "{{ get_policy.first_name }} {{ get_policy.last_name }}"
  
  - v2_path: "status"
    source: "get_policy"
    v1_path: "policy_status"

metadata:
  generated_at: "2025-10-19T10:00:00Z"
  confidence_score: 0.95
"""
    
    config_dir = tmp_path / "configs"
    config_dir.mkdir()
    config_file = config_dir / "get_policy.yaml"
    config_file.write_text(config_yaml)
    
    return config_dir


@pytest.fixture
def client(test_config, monkeypatch):
    """Create test client with mocked config directory"""
    # Mock the config directory path
    monkeypatch.setenv("CONFIG_DIR", str(test_config))
    
    with TestClient(app) as client:
        yield client


def test_health_check(client):
    """Test health check endpoint"""
    response = client.get("/health")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "endpoints_loaded" in data


def test_root_endpoint(client):
    """Test root endpoint returns API info"""
    response = client.get("/")
    
    assert response.status_code == 200
    data = response.json()
    assert "service" in data
    assert "endpoints" in data


@patch('adapter.main.orchestrator')
async def test_v2_endpoint_success(mock_orchestrator, client):
    """Test successful V2 request flow"""
    
    # Mock V1 responses
    mock_orchestrator.orchestrate = AsyncMock(return_value={
        "get_policy": {
            "policy_num": "POL12345",
            "first_name": "John",
            "last_name": "Doe",
            "policy_status": "active"
        }
    })
    
    response = client.get("/api/v2/policies/POL12345")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["policyNumber"] == "POL12345"
    assert data["insured"]["name"] == "John Doe"
    assert data["status"] == "active"
    
    # Check request ID header
    assert "X-Request-ID" in response.headers


@patch('adapter.main.orchestrator')
async def test_v2_endpoint_404_error(mock_orchestrator, client):
    """Test V2 endpoint with V1 404 error"""
    from adapter.orchestrator import V1OrchestratorError
    
    mock_orchestrator.orchestrate = AsyncMock(
        side_effect=V1OrchestratorError("Not found", status_code=404)
    )
    
    response = client.get("/api/v2/policies/INVALID")
    
    assert response.status_code == 404
    data = response.json()
    
    assert "error" in data
    assert data["code"] == "V1_ERROR_404"
    assert "request_id" in data


@patch('adapter.main.orchestrator')
async def test_v2_endpoint_500_error(mock_orchestrator, client):
    """Test V2 endpoint with V1 500 error (mapped to 502)"""
    from adapter.orchestrator import V1OrchestratorError
    
    mock_orchestrator.orchestrate = AsyncMock(
        side_effect=V1OrchestratorError("Server error", status_code=502)
    )
    
    response = client.get("/api/v2/policies/POL123")
    
    assert response.status_code == 502
    data = response.json()
    
    assert data["code"] == "V1_ERROR_502"


@patch('adapter.main.orchestrator')
async def test_v2_endpoint_timeout(mock_orchestrator, client):
    """Test V2 endpoint with V1 timeout"""
    from adapter.orchestrator import V1OrchestratorError
    
    mock_orchestrator.orchestrate = AsyncMock(
        side_effect=V1OrchestratorError("Timeout", status_code=504)
    )
    
    response = client.get("/api/v2/policies/POL123")
    
    assert response.status_code == 504
    data = response.json()
    
    assert data["code"] == "V1_ERROR_504"
```

## Testing Checklist
- [ ] Health check returns 200
- [ ] Root endpoint lists all registered endpoints
- [ ] V2 endpoint successfully processes request
- [ ] Path parameters extracted correctly
- [ ] Query parameters extracted correctly
- [ ] Response includes request ID header
- [ ] 404 errors handled and mapped correctly
- [ ] 502 errors handled correctly
- [ ] 504 timeout errors handled correctly
- [ ] Transformation errors return 500
- [ ] All responses include proper error codes

## Definition of Done
- FastAPI app loads configs on startup
- V2 endpoints dynamically registered
- Complete request flow working (orchestrate → transform → respond)
- Error handling complete with proper status codes
- Request correlation logging in place
- Integration tests passing
- Health check endpoint functional