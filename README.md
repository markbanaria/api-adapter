# Insurance API V1→V2 Adapter

A FastAPI-based adapter that transforms legacy V1 insurance APIs into modern V2 APIs using AI-generated configuration mappings.

## Architecture

```
┌─────────────┐
│   Next.js   │  ← Mapping Viewer UI (Port 3000)
│  Frontend   │
└──────┬──────┘
       │ HTTP
┌──────▼────────────┐
│  FastAPI Server   │  ← V2 API Adapter (Port 8000)
│  ┌────────────┐   │
│  │ Endpoints  │   │  ← Dynamic V2 API routes
│  └─────┬──────┘   │
│        │          │
│  ┌─────▼──────┐   │
│  │   Config   │   │  ← YAML Configuration Loader
│  │  Loader    │   │
│  └─────┬──────┘   │
│        │          │
│  ┌─────▼──────┐   │
│  │Orchestrator│   │  ← Calls multiple V1 APIs
│  └────────────┘   │
└───────────────────┘
       │ HTTP
┌──────▼──────┐
│ Legacy V1   │  ← Existing Insurance APIs (Port 8001)
│    APIs     │
└─────────────┘

┌─────────────┐
│  Qwen 7B    │  ← Offline Config Generator
│  CLI Tool   │     (Generates YAML mappings)
└─────────────┘
```

## Features

✅ **Dynamic API Transformation**: Convert V1 insurance APIs to V2 format using YAML configs
✅ **AI-Generated Mappings**: Use Qwen 7B to automatically generate field mappings
✅ **Jinja2 Transformations**: Advanced field combinations and data transformations
✅ **Multi-Endpoint Orchestration**: Combine data from multiple V1 APIs into single V2 response
✅ **Web-Based Config Manager**: Review and approve AI-generated mappings via UI
✅ **Request Correlation**: Full traceability with request IDs and structured logging
✅ **CORS & OpenAPI**: Production-ready with auto-generated API documentation

## Quick Start

### Prerequisites

- **Python 3.11+**
- **Node.js 18+**
- **Ollama with Qwen 7B model** (for config generation)

### Installation

```bash
# Clone repository
git clone <repo-url>
cd insurance-api-adapter

# Install backend dependencies
cd backend
pip install -e ".[dev]"

# Install config generator
cd ../config-generator
pip install -e ".[dev]"

# Install frontend dependencies
cd ../frontend
npm install
```

### Running the System

#### 1. Start Mock V1 API (for testing):
```bash
cd backend
uvicorn tests.mock_v1_server:mock_v1_app --port 8001
```

#### 2. Start V2 Adapter API:
```bash
cd backend
uvicorn adapter.main:app --reload
```

#### 3. Start Frontend UI:
```bash
cd frontend
npm run dev
```

#### 4. Access the System:
- **Mapping Viewer UI**: http://localhost:3000
- **V2 API Endpoints**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Mock V1 API**: http://localhost:8001

## Usage Examples

### Test V2 API Endpoints

```bash
# Get customer information (field combination scenario)
curl http://localhost:8000/api/v2/insured/CUST001
# Returns: {"fullName": "Jane Smith", "age": 42, "email": "jane@example.com"}

# Get policy information (simple rename scenario)
curl http://localhost:8000/api/v2/policies/POL123
# Returns: {"policyNumber": "POL123", "status": "active"}
```

### Generate New Mapping Configuration

```bash
cd config-generator
generate-config \
  --v2-spec specs/v2/policies-endpoint.json \
  --v1-spec specs/v1/complete-v1-api.json \
  --endpoint "/api/v2/policies/{policyId}" \
  --output ../backend/configs/policies.yaml
```

### Manage Configurations via UI

1. Open http://localhost:3000
2. View list of all mapping configurations with statistics
3. Click on a configuration to see detailed field mappings
4. Edit field mappings and approve/reject individual mappings
5. Export approved configurations as YAML

## Configuration Management API

```bash
# List all configurations
curl http://localhost:8000/configs

# Get specific configuration
curl http://localhost:8000/configs/example-field-combination

# Update configuration (approve mappings)
curl -X PUT http://localhost:8000/configs/example-field-combination \
  -H "Content-Type: application/json" \
  -d @updated-config.json

# Export as YAML
curl http://localhost:8000/configs/example-field-combination/export
```

## Testing

```bash
# Run backend tests
cd backend && pytest

# Run frontend tests
cd frontend && npm test

# Run end-to-end tests
cd backend && pytest tests/test_e2e.py

# Start mock V1 API for testing
uvicorn tests.mock_v1_server:mock_v1_app --port 8001
```

## Environment Configuration

### Backend (.env)
```bash
V1_API_BASE_URL=http://localhost:8001  # Mock V1 API for testing
CONFIG_DIR=./configs                   # Directory containing YAML configs
LOG_LEVEL=INFO                         # Logging level
```

### Frontend (.env.local)
```bash
NEXT_PUBLIC_API_BASE=http://localhost:8000  # Backend API URL
```

## Troubleshooting

### Common Issues

**Qwen Model Not Found**
```bash
ollama pull qwen:7b
```

**Config Validation Errors**
Check YAML syntax and ensure all required fields match the schema.

**CORS Errors**
Verify frontend origin is allowed in backend CORS middleware.

**V1 API Connection Errors**
- Check `V1_API_BASE_URL` environment variable
- Verify V1 API accessibility: `curl http://v1-api-url/health`

### Debug Mode
```bash
export LOG_LEVEL=DEBUG
uvicorn adapter.main:app --reload
```

## Documentation

- **User Stories**: [docs/](docs/)
- **API Documentation**: http://localhost:8000/docs (auto-generated)
- **Architecture Details**: [docs/project_scope_doc.md](docs/project_scope_doc.md)

## License

MIT License