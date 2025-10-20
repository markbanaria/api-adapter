# User Story 004: V1 API Orchestrator

## Story
As a developer, I want an orchestrator that can make multiple V1 API calls based on config and collect responses, so that V2 endpoints can aggregate data from multiple V1 sources.

## Acceptance Criteria
- [ ] Orchestrator can make multiple V1 API calls (sequential or parallel)
- [ ] Handles path parameters, query parameters, and body parameters
- [ ] Maps V2 parameters to V1 parameters correctly
- [ ] Collects all V1 responses in a structured format
- [ ] Handles HTTP errors with proper status code mapping
- [ ] Implements timeout handling
- [ ] Logs all V1 API calls with request IDs
- [ ] Unit tests cover success and error scenarios

## Technical Details

### V1 Orchestrator (backend/src/adapter/orchestrator.py)

```python
from typing import Dict, Any, List, Optional
import httpx
import logging
from uuid import uuid4
from .models import MappingConfig, V1ApiCall, ParamMapping

logger = logging.getLogger(__name__)


class V1OrchestratorError(Exception):
    """Raised when V1 API orchestration fails"""
    def __init__(self, message: str, status_code: int, details: Optional[Dict] = None):
        super().__init__(message)
        self.status_code = status_code
        self.details = details or {}


class V1Orchestrator:
    """Orchestrates calls to V1 APIs based on mapping configuration"""
    
    def __init__(
        self,
        v1_base_url: str,
        timeout: float = 30.0,
        max_retries: int = 0
    ):
        self.v1_base_url = v1_base_url.rstrip('/')
        self.timeout = timeout
        self.client = httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=True
        )
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()
    
    def _build_v1_url(
        self,
        v1_call: V1ApiCall,
        v2_params: Dict[str, Any]
    ) -> str:
        """
        Build complete V1 URL with path parameters substituted
        
        Args:
            v1_call: V1 API call configuration
            v2_params: V2 request parameters (path, query, body combined)
            
        Returns:
            Complete V1 URL
        """
        url = v1_call.endpoint
        
        # Substitute path parameters
        if v1_call.params and 'path' in v1_call.params:
            for param_map in v1_call.params['path']:
                v2_value = v2_params.get(param_map.v2_param)
                if v2_value is None:
                    raise V1OrchestratorError(
                        f"Missing required path parameter: {param_map.v2_param}",
                        status_code=400
                    )
                # Replace {param} or :param style placeholders
                url = url.replace(f"{{{param_map.v1_param}}}", str(v2_value))
                url = url.replace(f":{param_map.v1_param}", str(v2_value))
        
        return f"{self.v1_base_url}{url}"
    
    def _build_query_params(
        self,
        v1_call: V1ApiCall,
        v2_params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Build query parameters for V1 request"""
        query_params = {}
        
        if v1_call.params and 'query' in v1_call.params:
            for param_map in v1_call.params['query']:
                # Check if this V2 param is being shifted from path to query
                if param_map.location == "path":
                    # It's in the V2 path but needs to be in V1 query
                    v2_value = v2_params.get(param_map.v2_param)
                else:
                    v2_value = v2_params.get(param_map.v2_param)
                
                if v2_value is not None:
                    query_params[param_map.v1_param] = v2_value
        
        return query_params
    
    def _build_body(
        self,
        v1_call: V1ApiCall,
        v2_params: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Build request body for V1 request"""
        if v1_call.params and 'body' in v1_call.params:
            body = {}
            for param_map in v1_call.params['body']:
                v2_value = v2_params.get(param_map.v2_param)
                if v2_value is not None:
                    body[param_map.v1_param] = v2_value
            return body
        return None
    
    async def execute_v1_call(
        self,
        v1_call: V1ApiCall,
        v2_params: Dict[str, Any],
        request_id: str
    ) -> Dict[str, Any]:
        """
        Execute a single V1 API call
        
        Args:
            v1_call: V1 API call configuration
            v2_params: V2 request parameters
            request_id: Unique request ID for logging
            
        Returns:
            V1 API response data
            
        Raises:
            V1OrchestratorError: If V1 call fails
        """
        url = self._build_v1_url(v1_call, v2_params)
        query_params = self._build_query_params(v1_call, v2_params)
        body = self._build_body(v1_call, v2_params)
        
        log_data = {
            "request_id": request_id,
            "v1_call_name": v1_call.name,
            "method": v1_call.method,
            "url": url,
            "query_params": query_params
        }
        
        logger.info(f"Executing V1 call: {v1_call.name}", extra=log_data)
        
        try:
            response = await self.client.request(
                method=v1_call.method,
                url=url,
                params=query_params,
                json=body
            )
            
            # Map V1 HTTP errors to appropriate status codes
            if response.status_code == 404:
                raise V1OrchestratorError(
                    f"Resource not found in V1 API: {v1_call.name}",
                    status_code=404,
                    details={"v1_response": response.text}
                )
            elif response.status_code >= 500:
                raise V1OrchestratorError(
                    f"V1 API server error: {v1_call.name}",
                    status_code=502,
                    details={"v1_status": response.status_code, "v1_response": response.text}
                )
            elif response.status_code >= 400:
                raise V1OrchestratorError(
                    f"V1 API client error: {v1_call.name}",
                    status_code=response.status_code,
                    details={"v1_response": response.text}
                )
            
            response.raise_for_status()
            data = response.json()
            
            logger.info(
                f"V1 call successful: {v1_call.name}",
                extra={**log_data, "status": response.status_code, "duration_ms": response.elapsed.total_seconds() * 1000}
            )
            
            return data
            
        except httpx.TimeoutException:
            logger.error(f"V1 call timeout: {v1_call.name}", extra=log_data)
            raise V1OrchestratorError(
                f"V1 API timeout: {v1_call.name}",
                status_code=504
            )
        except httpx.RequestError as e:
            logger.error(f"V1 call network error: {v1_call.name}", extra={**log_data, "error": str(e)})
            raise V1OrchestratorError(
                f"V1 API network error: {v1_call.name}",
                status_code=502,
                details={"error": str(e)}
            )
    
    async def orchestrate(
        self,
        config: MappingConfig,
        v2_params: Dict[str, Any]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Orchestrate all V1 API calls for a V2 request
        
        Args:
            config: Mapping configuration
            v2_params: V2 request parameters (combined path, query, body)
            
        Returns:
            Dict of {v1_call_name: response_data}
            
        Raises:
            V1OrchestratorError: If any V1 call fails
        """
        request_id = str(uuid4())
        v1_responses = {}
        
        logger.info(
            f"Orchestrating V1 calls for {config.endpoint.v2_method} {config.endpoint.v2_path}",
            extra={"request_id": request_id, "v1_call_count": len(config.v1_calls)}
        )
        
        # Execute V1 calls sequentially (can be parallelized later if needed)
        for v1_call in config.v1_calls:
            try:
                response_data = await self.execute_v1_call(v1_call, v2_params, request_id)
                v1_responses[v1_call.name] = response_data
            except V1OrchestratorError:
                # Fail fast - if any V1 call fails, the entire V2 request fails
                raise
        
        logger.info(
            f"All V1 calls successful",
            extra={"request_id": request_id, "v1_calls_completed": len(v1_responses)}
        )
        
        return v1_responses
```

### Unit Tests (backend/tests/test_orchestrator.py)

```python
import pytest
from unittest.mock import AsyncMock, patch
import httpx
from adapter.orchestrator import V1Orchestrator, V1OrchestratorError
from adapter.models import V1ApiCall, ParamMapping, MappingConfig, EndpointConfig


@pytest.fixture
def orchestrator():
    return V1Orchestrator(v1_base_url="http://v1-api.example.com")


@pytest.fixture
def simple_v1_call():
    return V1ApiCall(
        name="get_policy",
        endpoint="/api/v1/policy/{policy_id}",
        method="GET",
        params={
            "path": [
                ParamMapping(v2_param="policyId", v1_param="policy_id", location="path")
            ]
        }
    )


@pytest.mark.asyncio
async def test_build_v1_url(orchestrator, simple_v1_call):
    """Test URL building with path parameter substitution"""
    v2_params = {"policyId": "POL123"}
    
    url = orchestrator._build_v1_url(simple_v1_call, v2_params)
    
    assert url == "http://v1-api.example.com/api/v1/policy/POL123"


@pytest.mark.asyncio
async def test_build_query_params(orchestrator):
    """Test query parameter mapping"""
    v1_call = V1ApiCall(
        name="search",
        endpoint="/api/v1/search",
        method="GET",
        params={
            "query": [
                ParamMapping(v2_param="term", v1_param="search_term", location="query"),
                ParamMapping(v2_param="limit", v1_param="max_results", location="query")
            ]
        }
    )
    
    v2_params = {"term": "life insurance", "limit": 10}
    query_params = orchestrator._build_query_params(v1_call, v2_params)
    
    assert query_params == {"search_term": "life insurance", "max_results": 10}


@pytest.mark.asyncio
async def test_param_location_shift_path_to_query(orchestrator):
    """Test shifting a V2 path param to V1 query param"""
    v1_call = V1ApiCall(
        name="get_policy",
        endpoint="/api/v1/policy",
        method="GET",
        params={
            "query": [
                ParamMapping(v2_param="policyId", v1_param="policy_id", location="path")
            ]
        }
    )
    
    v2_params = {"policyId": "POL123"}
    query_params = orchestrator._build_query_params(v1_call, v2_params)
    
    assert query_params == {"policy_id": "POL123"}


@pytest.mark.asyncio
async def test_execute_v1_call_success(orchestrator, simple_v1_call):
    """Test successful V1 API call"""
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"policy_num": "POL123", "status": "active"}
    mock_response.elapsed.total_seconds.return_value = 0.05
    
    with patch.object(orchestrator.client, 'request', return_value=mock_response):
        result = await orchestrator.execute_v1_call(
            simple_v1_call,
            {"policyId": "POL123"},
            "req_123"
        )
    
    assert result == {"policy_num": "POL123", "status": "active"}


@pytest.mark.asyncio
async def test_execute_v1_call_404_error(orchestrator, simple_v1_call):
    """Test V1 API 404 error handling"""
    mock_response = AsyncMock()
    mock_response.status_code = 404
    mock_response.text = "Not found"
    
    with patch.object(orchestrator.client, 'request', return_value=mock_response):
        with pytest.raises(V1OrchestratorError) as exc_info:
            await orchestrator.execute_v1_call(
                simple_v1_call,
                {"policyId": "INVALID"},
                "req_123"
            )
    
    assert exc_info.value.status_code == 404
    assert "not found" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_execute_v1_call_500_error(orchestrator, simple_v1_call):
    """Test V1 API 500 error handling (mapped to 502)"""
    mock_response = AsyncMock()
    mock_response.status_code = 500
    mock_response.text = "Internal server error"
    
    with patch.object(orchestrator.client, 'request', return_value=mock_response):
        with pytest.raises(V1OrchestratorError) as exc_info:
            await orchestrator.execute_v1_call(
                simple_v1_call,
                {"policyId": "POL123"},
                "req_123"
            )
    
    assert exc_info.value.status_code == 502


@pytest.mark.asyncio
async def test_execute_v1_call_timeout(orchestrator, simple_v1_call):
    """Test V1 API timeout handling"""
    with patch.object(orchestrator.client, 'request', side_effect=httpx.TimeoutException("Timeout")):
        with pytest.raises(V1OrchestratorError) as exc_info:
            await orchestrator.execute_v1_call(
                simple_v1_call,
                {"policyId": "POL123"},
                "req_123"
            )
    
    assert exc_info.value.status_code == 504


@pytest.mark.asyncio
async def test_orchestrate_multiple_calls(orchestrator):
    """Test orchestrating multiple V1 calls"""
    config = MappingConfig(
        version="1.0",
        endpoint=EndpointConfig(v2_path="/api/v2/policy-summary/{policyId}", v2_method="GET"),
        v1_calls=[
            V1ApiCall(
                name="get_policy",
                endpoint="/api/v1/policy/{id}",
                method="GET",
                params={"path": [ParamMapping(v2_param="policyId", v1_param="id", location="path")]}
            ),
            V1ApiCall(
                name="get_coverage",
                endpoint="/api/v1/coverage/{id}",
                method="GET",
                params={"path": [ParamMapping(v2_param="policyId", v1_param="id", location="path")]}
            )
        ],
        field_mappings=[]
    )
    
    mock_policy_response = AsyncMock()
    mock_policy_response.status_code = 200
    mock_policy_response.json.return_value = {"policy_num": "POL123"}
    mock_policy_response.elapsed.total_seconds.return_value = 0.05
    
    mock_coverage_response = AsyncMock()
    mock_coverage_response.status_code = 200
    mock_coverage_response.json.return_value = {"amount": 100000}
    mock_coverage_response.elapsed.total_seconds.return_value = 0.03
    
    with patch.object(orchestrator.client, 'request', side_effect=[mock_policy_response, mock_coverage_response]):
        result = await orchestrator.orchestrate(config, {"policyId": "POL123"})
    
    assert "get_policy" in result
    assert "get_coverage" in result
    assert result["get_policy"]["policy_num"] == "POL123"
    assert result["get_coverage"]["amount"] == 100000


@pytest.mark.asyncio
async def test_orchestrate_fails_on_first_error(orchestrator):
    """Test that orchestration fails fast on first V1 error"""
    config = MappingConfig(
        version="1.0",
        endpoint=EndpointConfig(v2_path="/api/v2/test", v2_method="GET"),
        v1_calls=[
            V1ApiCall(name="call1", endpoint="/v1/call1", method="GET"),
            V1ApiCall(name="call2", endpoint="/v1/call2", method="GET")
        ],
        field_mappings=[]
    )
    
    mock_error_response = AsyncMock()
    mock_error_response.status_code = 500
    mock_error_response.text = "Error"
    
    with patch.object(orchestrator.client, 'request', return_value=mock_error_response):
        with pytest.raises(V1OrchestratorError):
            await orchestrator.orchestrate(config, {})
```

## Testing Checklist
- [ ] URL building with path parameters works
- [ ] Query parameter mapping works
- [ ] Body parameter mapping works
- [ ] Path → Query parameter shift works
- [ ] Successful V1 calls return data
- [ ] 404 errors mapped correctly
- [ ] 500 errors mapped to 502
- [ ] Timeouts mapped to 504
- [ ] Multiple V1 calls orchestrated correctly
- [ ] Orchestration fails fast on first error
- [ ] Request IDs logged for all calls

## Definition of Done
- V1Orchestrator class implemented
- All parameter mappings working
- HTTP error mapping complete
- Request correlation logging in place
- All unit tests passing (>90% coverage)
- Async operations properly handled
