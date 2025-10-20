# Getting Started - Creating Your First V2 API

This guide walks you through setting up the Insurance API V1→V2 Adapter and creating your first V2 API endpoint configuration.

## Prerequisites

- Python 3.11+
- Node.js 18+
- Git

## Quick Setup

### 1. Start All Services

You need three services running simultaneously:

#### Terminal 1: Mock V1 API (Port 8001)
```bash
cd backend
source venv/bin/activate  # if using virtual environment
uvicorn tests.mock_v1_server:mock_v1_app --port 8001
```

Expected output:
```
INFO:     Uvicorn running on http://127.0.0.1:8001 (Press CTRL+C to quit)
INFO:     Application startup complete.
```

#### Terminal 2: V2 Adapter Backend (Port 8000)
```bash
cd backend/src
python3 -m uvicorn adapter.main:app --reload --port 8000
```

Expected output:
```
Starting Insurance API Adapter...
Loaded X endpoint configurations
Insurance API Adapter started successfully
INFO:     Uvicorn running on http://127.0.0.1:8000
```

#### Terminal 3: Frontend UI (Port 3000)
```bash
cd frontend
npm run dev -- --turbo
```

Expected output:
```
▲ Next.js 15.5.6 (Turbopack)
- Local:        http://localhost:3000
✓ Ready in 704ms
```

### 2. Verify Services

Test each service:

```bash
# Test Mock V1 API
curl http://localhost:8001/health
# Expected: {"status":"healthy","service":"mock-v1-api"}

# Test V2 Backend
curl http://localhost:8000/health
# Expected: {"status":"healthy","service":"insurance-api-adapter",...}

# Test Frontend (open in browser)
open http://localhost:3000
```

## Creating Your First V2 API

### Step 1: Understand Available V1 Endpoints

The mock V1 API provides these endpoints:

```bash
# View all available endpoints
curl http://localhost:8001/

# Test individual endpoints
curl http://localhost:8001/api/v1/customer/CUST001
curl http://localhost:8001/api/v1/policy/POL123
curl http://localhost:8001/api/v1/coverage?policy_id=POL123
```

### Step 2: Create Your Configuration File

Create `backend/configs/customer-info.yaml`:

```yaml
version: "1.0"
endpoint:
  path: "/api/v2/customer/{customerId}"
  method: "GET"
  description: "Get enhanced customer information"

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

  - v2_path: "age"
    source: "get_customer"
    v1_path: "customer_age"
    approved: false
    edited: false

  - v2_path: "email"
    source: "get_customer"
    v1_path: "email_address"
    approved: false
    edited: false

  - v2_path: "status"
    source: "stub"
    stub_value: "active"
    approved: false
    edited: false
```

### Step 3: Restart Backend to Load Config

Stop the backend (Ctrl+C) and restart:

```bash
cd backend/src
python3 -m uvicorn adapter.main:app --reload --port 8000
```

You should see:
```
Loaded 1 endpoint configurations
Registered endpoint: GET /api/v2/customer/{customerId}
```

### Step 4: Test Your New V2 Endpoint

```bash
curl http://localhost:8000/api/v2/customer/CUST001
```

Expected response:
```json
{
  "fullName": "Jane Smith",
  "age": 42,
  "email": "jane@example.com",
  "status": "active"
}
```

### Step 5: Manage via Web UI

1. Open http://localhost:3000
2. You'll see your new "customer-info" configuration
3. Click on it to view detailed field mappings
4. Edit mappings, approve/reject them
5. Export final configuration as YAML

## Configuration File Structure

### Basic Structure
```yaml
version: "1.0"                    # Configuration schema version
endpoint:                         # V2 endpoint definition
  path: "/api/v2/endpoint/{id}"   # URL path with parameters
  method: "GET"                   # HTTP method
  description: "Description"      # Endpoint description

v1_calls:                         # V1 APIs to call
  - name: "call_name"            # Reference name
    url: "http://v1-api/..."     # V1 endpoint URL
    method: "GET"                # HTTP method

field_mappings:                   # How to map V1 → V2 fields
  - v2_path: "fieldName"         # V2 response field name
    source: "call_name"          # Which V1 call to use
    v1_path: "v1_field"          # Direct field mapping
    # OR
    transform: "{{ template }}"   # Jinja2 transformation
    # OR
    stub_value: "value"          # Static value
    approved: false              # UI approval status
    edited: false                # UI edit status
```

### Field Mapping Types

#### 1. Direct Mapping
```yaml
- v2_path: "policyNumber"
  source: "get_policy"
  v1_path: "policy_num"
```

#### 2. Jinja2 Transformation
```yaml
- v2_path: "fullName"
  source: "get_customer"
  transform: "{{ first_name }} {{ last_name }}"
```

#### 3. Stub Values
```yaml
- v2_path: "version"
  source: "stub"
  stub_value: "2.0"
```

#### 4. Multi-Source Transformation
```yaml
v1_calls:
  - name: "get_policy"
    url: "http://localhost:8001/api/v1/policy/{id}"
  - name: "get_customer"
    url: "http://localhost:8001/api/v1/customer/{customerId}"

field_mappings:
  - v2_path: "summary"
    source: "get_policy"
    transform: "Policy {{ get_policy.policy_num }} for {{ get_customer.first_name }}"
```

## Advanced Examples

### Multi-Call Configuration
```yaml
version: "1.0"
endpoint:
  path: "/api/v2/complete-policy/{policyId}"
  method: "GET"

v1_calls:
  - name: "get_policy"
    url: "http://localhost:8001/api/v1/policy/{policyId}"
    method: "GET"
  - name: "get_coverage"
    url: "http://localhost:8001/api/v1/coverage"
    method: "GET"
    params:
      policy_id: "{policyId}"
  - name: "get_beneficiaries"
    url: "http://localhost:8001/api/v1/beneficiaries"
    method: "GET"
    params:
      policy_id: "{policyId}"

field_mappings:
  - v2_path: "policyNumber"
    source: "get_policy"
    v1_path: "policy_num"
  - v2_path: "coverageAmount"
    source: "get_coverage"
    v1_path: "amount"
  - v2_path: "beneficiaryCount"
    source: "get_beneficiaries"
    transform: "{{ get_beneficiaries | length }}"
```

### Complex Transformations
```yaml
field_mappings:
  # Array processing
  - v2_path: "beneficiaryNames"
    source: "get_beneficiaries"
    transform: "{{ get_beneficiaries | map(attribute='beneficiary_name') | list }}"

  # Conditional logic
  - v2_path: "riskLevel"
    source: "get_policy"
    transform: "{% if policy_details.premium_amount > 1000 %}high{% else %}standard{% endif %}"

  # Date formatting
  - v2_path: "createdDate"
    source: "get_policy"
    transform: "{{ created_timestamp | strftime('%Y-%m-%d') }}"
```

## Troubleshooting

### Common Issues

#### 1. Configuration Not Loading
```bash
# Check config directory
ls backend/configs/

# Validate YAML syntax
yamllint backend/configs/your-config.yaml

# Check backend startup logs
```

#### 2. V1 API Connection Errors
```bash
# Test V1 endpoint directly
curl http://localhost:8001/api/v1/customer/CUST001

# Check V1_API_BASE_URL environment variable
echo $V1_API_BASE_URL
```

#### 3. Transformation Errors
```bash
# Test Jinja2 template
python3 -c "
from jinja2 import Environment
env = Environment()
template = env.from_string('{{ first_name }} {{ last_name }}')
print(template.render(first_name='John', last_name='Doe'))
"
```

#### 4. Frontend Connection Issues
- Verify CORS settings in backend
- Check `NEXT_PUBLIC_API_BASE` in frontend `.env.local`
- Test backend health endpoint

### Debug Mode

Enable detailed logging:
```bash
export LOG_LEVEL=DEBUG
cd backend/src
python3 -m uvicorn adapter.main:app --reload --port 8000
```

## Next Steps

1. **Create More Endpoints**: Add configurations for policies, coverage, etc.
2. **Use AI Generation**: Set up Qwen for automatic config generation
3. **Customize UI**: Modify frontend for your specific needs
4. **Deploy**: Set up production environment

## Reference

- **API Documentation**: http://localhost:8000/docs
- **Frontend UI**: http://localhost:3000
- **Mock V1 API**: http://localhost:8001
- **Troubleshooting Guide**: [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- **Architecture Overview**: [README.md](../README.md)