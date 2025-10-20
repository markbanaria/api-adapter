import pytest
from unittest.mock import AsyncMock, patch
import httpx
from adapter.orchestrator import V1Orchestrator, V1OrchestratorError
from adapter.models import V1ApiCall, ParamMapping, MappingConfig, EndpointConfig, FieldMapping


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
async def test_build_v1_url_missing_path_param(orchestrator, simple_v1_call):
    """Test URL building with missing required path parameter"""
    v2_params = {}  # Missing policyId

    with pytest.raises(V1OrchestratorError) as exc_info:
        orchestrator._build_v1_url(simple_v1_call, v2_params)

    assert exc_info.value.status_code == 400
    assert "Missing required path parameter" in str(exc_info.value)


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
async def test_build_query_params_optional_missing(orchestrator):
    """Test query parameter mapping with optional missing params"""
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

    v2_params = {"term": "life insurance"}  # Missing limit
    query_params = orchestrator._build_query_params(v1_call, v2_params)

    assert query_params == {"search_term": "life insurance"}


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
async def test_build_body(orchestrator):
    """Test request body building"""
    v1_call = V1ApiCall(
        name="create_policy",
        endpoint="/api/v1/policy",
        method="POST",
        params={
            "body": [
                ParamMapping(v2_param="customerName", v1_param="customer_name", location="body"),
                ParamMapping(v2_param="policyType", v1_param="type", location="body")
            ]
        }
    )

    v2_params = {"customerName": "John Doe", "policyType": "whole_life"}
    body = orchestrator._build_body(v1_call, v2_params)

    assert body == {"customer_name": "John Doe", "type": "whole_life"}


@pytest.mark.asyncio
async def test_build_body_no_body_params(orchestrator):
    """Test request body building when no body params configured"""
    v1_call = V1ApiCall(
        name="get_policy",
        endpoint="/api/v1/policy",
        method="GET"
    )

    v2_params = {"policyId": "POL123"}
    body = orchestrator._build_body(v1_call, v2_params)

    assert body is None


@pytest.mark.asyncio
async def test_execute_v1_call_success(orchestrator, simple_v1_call):
    """Test successful V1 API call"""
    from unittest.mock import Mock

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"policy_num": "POL123", "status": "active"}
    mock_response.elapsed.total_seconds.return_value = 0.05
    mock_response.raise_for_status.return_value = None

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
async def test_execute_v1_call_400_error(orchestrator, simple_v1_call):
    """Test V1 API 400 error handling (passes through status code)"""
    mock_response = AsyncMock()
    mock_response.status_code = 400
    mock_response.text = "Bad request"

    with patch.object(orchestrator.client, 'request', return_value=mock_response):
        with pytest.raises(V1OrchestratorError) as exc_info:
            await orchestrator.execute_v1_call(
                simple_v1_call,
                {"policyId": "POL123"},
                "req_123"
            )

    assert exc_info.value.status_code == 400


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
async def test_execute_v1_call_502_error(orchestrator, simple_v1_call):
    """Test V1 API 502 error handling (mapped to 502)"""
    mock_response = AsyncMock()
    mock_response.status_code = 502
    mock_response.text = "Bad gateway"

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
async def test_execute_v1_call_network_error(orchestrator, simple_v1_call):
    """Test V1 API network error handling"""
    with patch.object(orchestrator.client, 'request', side_effect=httpx.RequestError("Network error")):
        with pytest.raises(V1OrchestratorError) as exc_info:
            await orchestrator.execute_v1_call(
                simple_v1_call,
                {"policyId": "POL123"},
                "req_123"
            )

    assert exc_info.value.status_code == 502
    assert "network error" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_orchestrate_single_call(orchestrator):
    """Test orchestrating a single V1 call"""
    config = MappingConfig(
        version="1.0",
        endpoint=EndpointConfig(v2_path="/api/v2/policy/{policyId}", v2_method="GET"),
        v1_calls=[
            V1ApiCall(
                name="get_policy",
                endpoint="/api/v1/policy/{id}",
                method="GET",
                params={"path": [ParamMapping(v2_param="policyId", v1_param="id", location="path")]}
            )
        ],
        field_mappings=[
            FieldMapping(v2_path="policyNumber", source="get_policy", v1_path="policy_num")
        ]
    )

    from unittest.mock import Mock

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"policy_num": "POL123", "status": "active"}
    mock_response.elapsed.total_seconds.return_value = 0.05
    mock_response.raise_for_status.return_value = None

    with patch.object(orchestrator.client, 'request', return_value=mock_response):
        result = await orchestrator.orchestrate(config, {"policyId": "POL123"})

    assert "get_policy" in result
    assert result["get_policy"]["policy_num"] == "POL123"


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
        field_mappings=[
            FieldMapping(v2_path="policyNumber", source="get_policy", v1_path="policy_num"),
            FieldMapping(v2_path="coverageAmount", source="get_coverage", v1_path="amount")
        ]
    )

    from unittest.mock import Mock

    mock_policy_response = Mock()
    mock_policy_response.status_code = 200
    mock_policy_response.json.return_value = {"policy_num": "POL123"}
    mock_policy_response.elapsed.total_seconds.return_value = 0.05
    mock_policy_response.raise_for_status.return_value = None

    mock_coverage_response = Mock()
    mock_coverage_response.status_code = 200
    mock_coverage_response.json.return_value = {"amount": 100000}
    mock_coverage_response.elapsed.total_seconds.return_value = 0.03
    mock_coverage_response.raise_for_status.return_value = None

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
        field_mappings=[
            FieldMapping(v2_path="field1", source="call1", v1_path="data")
        ]
    )

    mock_error_response = AsyncMock()
    mock_error_response.status_code = 500
    mock_error_response.text = "Error"

    with patch.object(orchestrator.client, 'request', return_value=mock_error_response):
        with pytest.raises(V1OrchestratorError):
            await orchestrator.orchestrate(config, {})


@pytest.mark.asyncio
async def test_orchestrate_second_call_fails(orchestrator):
    """Test that orchestration fails on second call error"""
    config = MappingConfig(
        version="1.0",
        endpoint=EndpointConfig(v2_path="/api/v2/test", v2_method="GET"),
        v1_calls=[
            V1ApiCall(name="call1", endpoint="/v1/call1", method="GET"),
            V1ApiCall(name="call2", endpoint="/v1/call2", method="GET")
        ],
        field_mappings=[
            FieldMapping(v2_path="field1", source="call1", v1_path="data"),
            FieldMapping(v2_path="field2", source="call2", v1_path="data")
        ]
    )

    from unittest.mock import Mock

    mock_success_response = Mock()
    mock_success_response.status_code = 200
    mock_success_response.json.return_value = {"data": "success"}
    mock_success_response.elapsed.total_seconds.return_value = 0.05
    mock_success_response.raise_for_status.return_value = None

    mock_error_response = AsyncMock()
    mock_error_response.status_code = 404
    mock_error_response.text = "Not found"

    with patch.object(orchestrator.client, 'request', side_effect=[mock_success_response, mock_error_response]):
        with pytest.raises(V1OrchestratorError) as exc_info:
            await orchestrator.orchestrate(config, {})

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_close_client(orchestrator):
    """Test closing the HTTP client"""
    with patch.object(orchestrator.client, 'aclose') as mock_close:
        await orchestrator.close()
        mock_close.assert_called_once()


@pytest.mark.asyncio
async def test_base_url_normalization():
    """Test that base URL trailing slash is removed"""
    orchestrator1 = V1Orchestrator("http://api.example.com/")
    orchestrator2 = V1Orchestrator("http://api.example.com")

    assert orchestrator1.v1_base_url == "http://api.example.com"
    assert orchestrator2.v1_base_url == "http://api.example.com"

    await orchestrator1.close()
    await orchestrator2.close()


@pytest.mark.asyncio
async def test_colon_style_path_params(orchestrator):
    """Test URL building with :param style placeholders"""
    v1_call = V1ApiCall(
        name="get_policy",
        endpoint="/api/v1/policy/:policy_id",
        method="GET",
        params={
            "path": [
                ParamMapping(v2_param="policyId", v1_param="policy_id", location="path")
            ]
        }
    )

    v2_params = {"policyId": "POL123"}
    url = orchestrator._build_v1_url(v1_call, v2_params)

    assert url == "http://v1-api.example.com/api/v1/policy/POL123"