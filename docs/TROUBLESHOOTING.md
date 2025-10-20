# Troubleshooting Guide

## Common Issues

### 1. Qwen Model Not Responding

**Symptoms**: Config generation hangs or times out

**Solutions**:
- Verify Ollama is running: `ollama list`
- Check Qwen model is installed: `ollama pull qwen:7b`
- Increase timeout in `config-generator/src/generator/qwen_client.py`
- Verify model is loaded: `ollama show qwen:7b`

### 2. Config Validation Errors

**Symptoms**: Generated configs fail to load, validation errors in logs

**Solutions**:
- Validate YAML syntax: `yamllint config.yaml`
- Check required fields match schema in `backend/src/adapter/models.py`
- Review Pydantic validation errors in backend logs
- Ensure `approved` and `edited` fields are present in field mappings
- Verify V2 paths don't start with `.` (use `policyNumber` not `.policyNumber`)

### 3. V1 API Connection Errors

**Symptoms**: 502 or 504 errors from V2 endpoints, "Connection refused" in logs

**Solutions**:
- Verify V1 API is accessible: `curl http://v1-api-url/health`
- Check `V1_API_BASE_URL` environment variable
- Review network/firewall settings
- Start mock V1 API for testing: `uvicorn tests.mock_v1_server:mock_v1_app --port 8001`
- Check orchestrator logs for detailed HTTP errors

### 4. Transform Errors

**Symptoms**: 500 errors with "transformation failed", undefined variables

**Solutions**:
- Check Jinja2 syntax in transform expressions
- Verify field paths exist in V1 responses
- Review logs for specific transformation errors
- Test transformations manually: `{{ first_name }} {{ last_name }}`
- Ensure context variables are available (use V1 response field names)

### 5. Frontend Can't Connect to Backend

**Symptoms**: CORS errors, network errors, connection warning in UI

**Solutions**:
- Verify backend is running on correct port (8000)
- Check `NEXT_PUBLIC_API_BASE` in frontend `.env.local`
- Ensure CORS middleware configured in backend (`adapter/main.py`)
- Test backend health: `curl http://localhost:8000/health`

### 6. Empty or Invalid Responses

**Symptoms**: V2 responses with null values, empty objects

**Solutions**:
- Check V1 API responses: `curl http://localhost:8001/api/v1/endpoint`
- Verify field mappings point to correct V1 fields
- Review `v1_path` values in configuration
- Check transformation context in debug logs

### 7. Configuration Not Loading

**Symptoms**: Endpoints not registered, "No config found" errors

**Solutions**:
- Restart backend server to reload configs
- Check config files are in correct directory (`backend/configs/`)
- Verify YAML syntax is valid
- Check file permissions on config directory
- Review startup logs for config loading errors

## Debug Mode

Enable debug logging:

```bash
# Backend
export LOG_LEVEL=DEBUG
cd backend
uvicorn adapter.main:app --reload

# View structured logs
tail -f logs/adapter.log | jq  # if using structured JSON logging
```

Debug information includes:
- Config loading details
- V1 API request/response details
- Transformation context and results
- Request correlation IDs

## Performance Issues

### Slow V2 Response Times

**Symptoms**: V2 endpoints taking >2 seconds to respond

**Solutions**:
- Check V1 API response times: `time curl http://v1-api/endpoint`
- Monitor concurrent V1 calls in orchestrator
- Consider caching V1 responses (not implemented in v1)
- Review V1 API performance and capacity

### High Memory Usage

**Symptoms**: Backend consuming excessive memory with large configs

**Solutions**:
- Monitor config file sizes
- Review number of field mappings per config
- Consider breaking large configs into smaller ones
- Monitor V1 response sizes

### Frontend Performance

**Symptoms**: Slow loading of mapping configurations

**Solutions**:
- Check backend `/configs` endpoint response time
- Monitor number of configurations loaded
- Use pagination for large config lists (future enhancement)

## Configuration Issues

### Invalid YAML Syntax

```bash
# Validate YAML syntax
yamllint backend/configs/your-config.yaml

# Check config loading
curl http://localhost:8000/configs/your-config-id
```

### Field Mapping Errors

**Common Issues**:
- Missing `approved` and `edited` fields
- Invalid V2 paths (starting with `.`)
- Incorrect V1 field references
- Malformed Jinja2 templates

**Example Fix**:
```yaml
# ❌ Invalid
field_mappings:
- v2_path: .policyNumber        # Don't start with .
  source: getPolicy
  v1_path: .policy_num          # Don't start with .

# ✅ Correct
field_mappings:
- v2_path: policyNumber
  source: getPolicy
  v1_path: policy_num
  approved: false
  edited: false
```

### Transformation Template Issues

**Common Issues**:
- Undefined variables: `'first_name' is undefined`
- Malformed templates: `{{ unclosed template`
- Incorrect field references

**Example Fix**:
```yaml
# ❌ May fail if context doesn't have these variables
transform: "{{ first_name }} {{ last_name }}"

# ✅ Better - use explicit source reference
transform: "{{ get_customer.first_name }} {{ get_customer.last_name }}"

# ✅ Or ensure transformer flattens context (current implementation)
transform: "{{ first_name }} {{ last_name }}"  # Works with flattened context
```

## Testing and Validation

### Test E2E Flow

```bash
# 1. Start mock V1 API
uvicorn tests.mock_v1_server:mock_v1_app --port 8001

# 2. Start backend
uvicorn adapter.main:app --reload

# 3. Test V2 endpoint
curl http://localhost:8000/api/v2/insured/CUST001

# 4. Check response format
curl http://localhost:8000/api/v2/policies/POL123 | jq .
```

### Validate Configuration

```bash
# Test config loading
python -c "
from adapter.config_loader import ConfigLoader
from pathlib import Path
loader = ConfigLoader(Path('configs'))
config = loader.load_config('your-config.yaml')
print('Config loaded successfully')
"
```

### Test Transformations

```bash
# Test Jinja2 templates
python -c "
from jinja2 import Environment
env = Environment()
template = env.from_string('{{ first_name }} {{ last_name }}')
result = template.render(first_name='John', last_name='Doe')
print(result)
"
```

## Getting Help

### Diagnostic Information to Collect

When reporting issues, include:

1. **Version Information**:
   ```bash
   python --version
   pip list | grep -E "(fastapi|uvicorn|jinja2)"
   ```

2. **Configuration**:
   - Relevant YAML config files
   - Environment variables
   - Error messages and stack traces

3. **Request/Response Examples**:
   ```bash
   # V1 API response
   curl http://localhost:8001/api/v1/customer/CUST001

   # V2 API response
   curl http://localhost:8000/api/v2/insured/CUST001
   ```

4. **Backend Logs**:
   - Startup logs showing config loading
   - Request processing logs with correlation IDs
   - Any error messages or stack traces

### Log Locations

- **Backend Logs**: Console output or log files if configured
- **Frontend Logs**: Browser developer console
- **Config Generator Logs**: Console output during generation

### Support Channels

1. Check this troubleshooting guide first
2. Review API documentation: http://localhost:8000/docs
3. Check user stories and implementation docs in `docs/`
4. File an issue with diagnostic information

## Quick Fixes

### Reset to Working State

```bash
# 1. Stop all services
pkill -f uvicorn

# 2. Restart in correct order
cd backend
uvicorn tests.mock_v1_server:mock_v1_app --port 8001 &
uvicorn adapter.main:app --reload &

cd ../frontend
npm run dev &

# 3. Verify services
curl http://localhost:8001/health  # Mock V1 API
curl http://localhost:8000/health  # V2 Adapter
curl http://localhost:3000         # Frontend
```

### Clear Cache and Restart

```bash
# Backend
rm -rf __pycache__ .pytest_cache
pip install -e . --force-reinstall

# Frontend
rm -rf node_modules .next
npm install
```

This troubleshooting guide covers the most common issues encountered during development and deployment. Keep it updated as new issues are discovered and resolved.