# Quick Reference - V1→V2 API Adapter

## 🚀 Start Services (3 Terminals)

```bash
# Terminal 1: Mock V1 API
cd backend && uvicorn tests.mock_v1_server:mock_v1_app --port 8001

# Terminal 2: V2 Backend
cd backend/src && python3 -m uvicorn adapter.main:app --reload --port 8000

# Terminal 3: Frontend
cd frontend && npm run dev -- --turbo
```

## 🌐 Service URLs

- **Frontend UI**: http://localhost:3000
- **V2 API & Docs**: http://localhost:8000/docs
- **Mock V1 API**: http://localhost:8001

## 📁 Create Config File

**Location**: `backend/configs/my-endpoint.yaml`

```yaml
version: "1.0"
endpoint:
  path: "/api/v2/customer/{customerId}"
  method: "GET"

v1_calls:
  - name: "get_customer"
    url: "http://localhost:8001/api/v1/customer/{customerId}"
    method: "GET"

field_mappings:
  - v2_path: "fullName"
    source: "get_customer"
    transform: "{{ first_name }} {{ last_name }}"
    approved: false
    edited: false
```

## 🔧 Field Mapping Types

| Type | Example |
|------|---------|
| **Direct** | `v1_path: "customer_age"` |
| **Transform** | `transform: "{{ first_name }} {{ last_name }}"` |
| **Stub** | `source: "stub"` + `stub_value: "active"` |

## 🧪 Test Your API

```bash
# Test V2 endpoint
curl http://localhost:8000/api/v2/customer/CUST001

# Expected response
{"fullName": "Jane Smith", "age": 42, "email": "jane@example.com"}
```

## 🎯 Available Mock V1 Endpoints

```bash
curl http://localhost:8001/api/v1/customer/CUST001
curl http://localhost:8001/api/v1/policy/POL123
curl http://localhost:8001/api/v1/coverage?policy_id=POL123
curl http://localhost:8001/api/v1/beneficiaries?policy_id=POL123
```

## 🐛 Quick Debug

```bash
# Check health
curl http://localhost:8000/health
curl http://localhost:8001/health

# View configs
curl http://localhost:8000/configs

# Enable debug logs
export LOG_LEVEL=DEBUG
```

## 🔄 Workflow

1. Create YAML config in `backend/configs/`
2. Restart backend to load config
3. Test V2 endpoint with curl
4. Refine via web UI at http://localhost:3000
5. Export final config as YAML

## 📚 More Help

- **Full Guide**: [GETTING_STARTED.md](GETTING_STARTED.md)
- **Troubleshooting**: [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- **Architecture**: [README.md](../README.md)