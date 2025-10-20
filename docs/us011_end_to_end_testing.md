# User Story 011: End-to-End Testing & Documentation

## Story
As a developer, I want comprehensive end-to-end tests and documentation so that the entire system works together and future developers can understand and maintain it.

## Acceptance Criteria
- [ ] End-to-end test covering full flow (config generation → adapter → response)
- [ ] Mock V1 API server for testing
- [ ] All 7 scenarios tested end-to-end
- [ ] README with setup instructions
- [ ] Architecture documentation
- [ ] API documentation (OpenAPI/Swagger)
- [ ] Troubleshooting guide

## Technical Details

### Mock V1 API Server (backend/tests/mock_v1_server.py)

```python
from fastapi import FastAPI, HTTPException
from typing import Optional

# Mock V1 API for testing
mock_v1_app = FastAPI(title="Mock V1 API")


@mock_v1_app.get("/api/v1/policy/{id}")
async def get_policy(id: str):
    """Mock policy endpoint"""
    if id == "INVALID":
        raise HTTPException(status_code=404, detail="Policy not found")
    
    return {
        "policy_num": id,
        "policy_status": "active",
        "first_name": "John",
        "last_name": "Doe",
        "policy_details": {
            "type": "whole_life",
            "premium_amount": 500
        }
    }


@mock_v1_app.get("/api/v1/policy")
async def get_policy_by_param(policy_id: str):
    """Mock policy by query param"""
    return {
        "policy_num": policy_id,
        "policy_status": "active"
    }


@mock_v1_app.get("/api/v1/customer/{customerId}")
async def get_customer(customerId: str):
    """Mock customer endpoint"""
    return {
        "first_name": "Jane",
        "last_name": "Smith",
        "customer_age": 42,
        "email_address": "jane@example.com"
    }


@mock_v1_app.get("/api/v1/coverage")
async def get_coverage(policy_id: str):
    """Mock coverage endpoint"""
    return {
        "amount": 500000,
        "type": "whole_life"
    }


@mock_v1_app.get("/api/v1/coverage/{id}")
async def get_coverage_by_id(id: str):
    """Mock coverage by path param"""
    return {
        "amount": 1000000,
        "type": "term_life"
    }


@mock_v1_app.get("/api/v1/beneficiaries")
async def get_beneficiaries(policy_id: str):
    """Mock beneficiaries endpoint"""
    return [
        {"beneficiary_name": "Alice Doe", "relation": "spouse"},
        {"beneficiary_name": "Bob Doe", "relation": "child"}
    ]


@mock_v1_app.get("/api/v1/policy/search")
async def search_policies(
    customer_id: Optional[str] = None,
    type: Optional[str] = None,
    status: Optional[str] = None
):
    """Mock policy search endpoint"""
    return [
        {"policy_num": "POL001", "policy_type": "whole_life"},
        {"policy_num": "POL002", "policy_type": "term_life"}
    ]
```

### E2E Test Suite (backend/tests/test_e2e.py)

```python
import pytest
from fastapi.testclient import TestClient
import uvicorn
from multiprocessing import Process
import time
import httpx

from adapter.main import app as adapter_app
from .mock_v1_server import mock_v1_app


@pytest.fixture(scope="module")
def v1_server():
    """Start mock V1 API server"""
    def run_server():
        uvicorn.run(mock_v1_app, host="127.0.0.1", port=8001, log_level="error")
    
    proc = Process(target=run_server, daemon=True)
    proc.start()
    time.sleep(2)  # Wait for server to start
    
    yield "http://127.0.0.1:8001"
    
    proc.terminate()
    proc.join()


@pytest.fixture
def adapter_client(v1_server, tmp_path):
    """Create adapter client with test configs"""
    # Create test config
    config_dir = tmp_path / "configs"
    config_dir.mkdir()
    
    # ... create test configs ...
    
    with TestClient(adapter_app) as client:
        yield client


def test_scenario1_simple_rename(adapter_client, v1_server):
    """E2E test for scenario 1: simple field rename"""
    # Make request to V2 endpoint
    response = adapter_client.get("/api/v2/policies/POL123")
    
    assert response.status_code == 200
    data = response.json()
    
    # Verify V2 response structure
    assert data["policyNumber"] == "POL123"
    assert data["status"] == "active"
    
    # Verify request ID header
    assert "X-Request-ID" in response.headers


def test_scenario2_field_combination(adapter_client, v1_server):
    """E2E test for scenario 2: field combination"""
    response = adapter_client.get("/api/v2/insured/CUST001")
    
    assert response.status_code == 200
    data = response.json()
    
    # Verify combined field
    assert data["fullName"] == "Jane Smith"
    assert data["age"] == 42
    assert data["email"] == "jane@example.com"


def test_scenario3_param_shift(adapter_client, v1_server):
    """E2E test for scenario 3: query param to path param"""
    response = adapter_client.get("/api/v2/coverage/POL123")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["coverageAmount"] == 500000
    assert data["coverageType"] == "whole_life"


def test_scenario5_multi_endpoint(adapter_client, v1_server):
    """E2E test for scenario 5: multiple V1 endpoints"""
    response = adapter_client.get("/api/v2/complete-policy/POL123")
    
    assert response.status_code == 200
    data = response.json()
    
    # Data from first V1 endpoint
    assert data["policyNumber"] == "POL123"
    assert data["status"] == "active"
    
    # Data from second V1 endpoint
    assert data["coverageAmount"] == 1000000
    
    # Data from third V1 endpoint
    assert len(data["beneficiaries"]) == 2
    assert data["beneficiaries"][0]["name"] == "Alice Doe"


def test_error_handling_404(adapter_client, v1_server):
    """E2E test for 404 error handling"""
    response = adapter_client.get("/api/v2/policies/INVALID")
    
    assert response.status_code == 404
    data = response.json()
    
    assert "error" in data
    assert data["code"] == "V1_ERROR_404"
    assert "request_id" in data


def test_request_logging(adapter_client, v1_server, caplog):
    """E2E test for request correlation logging"""
    import logging
    caplog.set_level(logging.INFO)
    
    response = adapter_client.get("/api/v2/policies/POL123")
    
    assert response.status_code == 200
    
    # Verify logs contain request tracking
    logs = caplog.text
    assert "request_id" in logs.lower()
    assert "v1_call" in logs.lower()
```

### Root README.md

```markdown
# Insurance API V1→V2 Adapter

A FastAPI-based adapter that transforms legacy V1 insurance APIs into modern V2 APIs using AI-generated configuration mappings.

## Architecture

```
┌─────────────┐
│   Next.js   │  ← Mapping Viewer UI
│  Frontend   │
└──────┬──────┘
       │
┌──────▼────────────┐
│  FastAPI Server   │  ← V2 API Adapter
│  ┌────────────┐   │
│  │ Endpoints  │   │
│  └─────┬──────┘   │
│        │          │
│  ┌─────▼──────┐   │
│  │   Config   │   │  ← YAML Configs
│  │  Loader    │   │
│  └─────┬──────┘   │
│        │          │
│  ┌─────▼──────┐   │
│  │Orchestrator│   │  → Calls V1 APIs
│  └────────────┘   │
└───────────────────┘

┌─────────────┐
│  Qwen 7B    │  ← Offline Config Generator
│  CLI Tool   │
└─────────────┘
```

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- Ollama with Qwen 7B model

### Installation

```bash
# Clone repository
git clone <repo-url>
cd insurance-api-adapter

# Install backend
cd backend
pip install -e ".[dev]"

# Install config generator
cd ../config-generator
pip install -e ".[dev]"

# Install frontend
cd ../frontend
npm install
```

### Running the System

1. **Start Mock V1 API** (for testing):
```bash
cd backend
uvicorn tests.mock_v1_server:mock_v1_app --port 8001
```

2. **Generate Configs** (one-time):
```bash
cd config-generator
generate-config \
  --v2-spec specs/v2/scenario1-simple-rename.json \
  --v1-spec specs/v1/complete-v1-api.json \
  --endpoint "/api/v2/policies/{policyId}" \
  --output ../backend/configs/scenario1.yaml
```

3. **Start Adapter Server**:
```bash
cd backend
uvicorn adapter.main:app --reload
```

4. **Start Frontend**:
```bash
cd frontend
npm run dev
```

5. **Access**:
   - Mapping Viewer: http://localhost:3000
   - V2 API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

## Testing

```bash
# Backend tests
cd backend
pytest

# Frontend tests
cd frontend
npm test

# E2E tests
cd backend
pytest tests/test_e2e.py
```

## Configuration

### Environment Variables

**Backend** (.env):
```
V1_API_BASE_URL=http://localhost:8001
CONFIG_DIR=./configs
LOG_LEVEL=INFO
```

**Frontend** (.env.local):
```
NEXT_PUBLIC_API_BASE=http://localhost:8000
```

## Documentation

- [Scope Document](docs/SCOPE.md)
- [User Stories](docs/user-stories/)
- [API Documentation](http://localhost:8000/docs)

## Troubleshooting

### Qwen Model Not Found

```bash
# Install Qwen model
ollama pull qwen:7b
```

### Config Validation Errors

Check that your YAML config matches the schema in `backend/src/adapter/models.py`.

### CORS Errors

Ensure the backend CORS middleware allows your frontend origin in `backend/src/adapter/main.py`.

## License

MIT
```

### Troubleshooting Guide (docs/TROUBLESHOOTING.md)

```markdown
# Troubleshooting Guide

## Common Issues

### 1. Qwen Model Not Responding

**Symptoms**: Config generation hangs or times out

**Solutions**:
- Verify Ollama is running: `ollama list`
- Check Qwen model is installed: `ollama pull qwen:7b`
- Increase timeout in `config-generator/src/generator/qwen_client.py`

### 2. Config Validation Errors

**Symptoms**: Generated configs fail to load

**Solutions**:
- Validate YAML syntax: `yamllint config.yaml`
- Check required fields match schema
- Review Pydantic validation errors in logs

### 3. V1 API Connection Errors

**Symptoms**: 502 or 504 errors from V2 endpoints

**Solutions**:
- Verify V1 API is accessible: `curl http://v1-api-url/health`
- Check V1_API_BASE_URL environment variable
- Review network/firewall settings

### 4. Transform Errors

**Symptoms**: 500 errors with "transformation failed"

**Solutions**:
- Check Jinja2 syntax in transform expressions
- Verify field paths exist in V1 responses
- Review logs for specific transformation errors

### 5. Frontend Can't Connect to Backend

**Symptoms**: CORS errors or network errors

**Solutions**:
- Verify backend is running on correct port
- Check NEXT_PUBLIC_API_BASE in frontend .env
- Ensure CORS middleware configured in backend

## Debug Mode

Enable debug logging:

```bash
# Backend
export LOG_LEVEL=DEBUG
uvicorn adapter.main:app --reload

# View structured logs
tail -f logs/adapter.log | jq
```

## Performance Issues

- Check V1 API response times
- Consider caching V1 responses (not implemented in v1)
- Monitor memory usage with large configs

## Getting Help

1. Check logs: `backend/logs/`
2. Review API docs: http://localhost:8000/docs
3. File an issue with logs and config
```

## Testing Checklist
- [ ] All 7 scenarios tested end-to-end
- [ ] Mock V1 server responds correctly
- [ ] Error scenarios tested (404, 500, timeout)
- [ ] Request correlation logging verified
- [ ] README complete with setup instructions
- [ ] Troubleshooting guide covers common issues
- [ ] API documentation generated

## Definition of Done
- E2E test suite passing for all scenarios
- Mock V1 API server implemented
- Comprehensive README created
- Troubleshooting guide documented
- All documentation reviewed and accurate
- System can be set up from scratch following README