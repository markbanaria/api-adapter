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