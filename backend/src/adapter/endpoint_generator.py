from typing import Dict, Any, Callable, List
import logging
from fastapi import APIRouter, HTTPException, Request, Path, Query, Body, Depends
from fastapi.routing import APIRoute
import re
import inspect
from .models import MappingConfig
from .orchestrator import V1Orchestrator, V1OrchestratorError
from .response_builder import V2ResponseBuilder, ResponseBuilderError

logger = logging.getLogger(__name__)


class EndpointGenerator:
    """Generates FastAPI endpoints dynamically from mapping configurations"""

    def __init__(self, orchestrator: V1Orchestrator):
        self.orchestrator = orchestrator
        self.response_builder = V2ResponseBuilder()
        self.router = APIRouter()

    def _extract_path_params(self, path: str) -> List[str]:
        """Extract path parameter names from a FastAPI path"""
        return re.findall(r'\{([^}]+)\}', path)

    def _create_endpoint_function(self, config: MappingConfig) -> Callable:
        """Create an async function for handling the V2 endpoint with proper signature"""

        path_params = self._extract_path_params(config.endpoint.v2_path)

        if len(path_params) == 1:
            # Single path parameter - create function with explicit parameter
            param_name = path_params[0]

            async def endpoint_handler(**kwargs):
                # Extract path parameter from kwargs (FastAPI injects it)
                path_value = kwargs.get(param_name)
                v2_params = {param_name: path_value}

                return await self._handle_request(config, v2_params)

            # Create proper function signature for FastAPI
            param = inspect.Parameter(
                param_name,
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
                annotation=str,
                default=Path(..., description=f"Path parameter: {param_name}")
            )
            endpoint_handler.__signature__ = inspect.Signature([param])

        elif len(path_params) > 1:
            # Multiple path parameters
            async def endpoint_handler(**kwargs):
                v2_params = {param: kwargs.get(param) for param in path_params}
                return await self._handle_request(config, v2_params)

            # Create proper function signature for FastAPI
            params = [
                inspect.Parameter(
                    param,
                    inspect.Parameter.POSITIONAL_OR_KEYWORD,
                    annotation=str,
                    default=Path(..., description=f"Path parameter: {param}")
                )
                for param in path_params
            ]
            endpoint_handler.__signature__ = inspect.Signature(params)

        else:
            # No path parameters
            async def endpoint_handler(request: Request):
                query_params = dict(request.query_params)
                body_params = {}

                # Handle body for POST/PUT/PATCH
                if config.endpoint.v2_method in ["POST", "PUT", "PATCH"]:
                    try:
                        body = await request.json()
                        if isinstance(body, dict):
                            body_params = body
                    except Exception:
                        pass

                v2_params = {}
                v2_params.update(query_params)
                v2_params.update(body_params)

                return await self._handle_request(config, v2_params)

        return endpoint_handler

    async def _handle_request(self, config: MappingConfig, v2_params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle the actual request processing"""
        try:
            logger.info(
                f"Processing {config.endpoint.v2_method} {config.endpoint.v2_path}",
                extra={
                    "v2_params": v2_params,
                    "config_version": config.version
                }
            )

            # Orchestrate V1 API calls
            v1_responses = await self.orchestrator.orchestrate(config, v2_params)

            # Build V2 response
            v2_response = self.response_builder.build_response(config, v1_responses)

            logger.info(
                f"Successfully processed {config.endpoint.v2_method} {config.endpoint.v2_path}",
                extra={"response_fields": list(v2_response.keys())}
            )

            return v2_response

        except V1OrchestratorError as e:
            logger.error(
                f"V1 orchestration failed for {config.endpoint.v2_path}: {e}",
                extra={"status_code": e.status_code, "details": e.details}
            )
            raise HTTPException(
                status_code=e.status_code,
                detail={
                    "error": str(e),
                    "type": "orchestration_error",
                    "details": e.details
                }
            )
        except ResponseBuilderError as e:
            logger.error(
                f"Response building failed for {config.endpoint.v2_path}: {e}"
            )
            raise HTTPException(
                status_code=500,
                detail={
                    "error": str(e),
                    "type": "response_building_error"
                }
            )
        except Exception as e:
            logger.error(
                f"Unexpected error in {config.endpoint.v2_path}: {e}",
                exc_info=True
            )
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "Internal server error",
                    "type": "unexpected_error"
                }
            )

    def register_endpoint(self, config: MappingConfig) -> None:
        """Register a single V2 endpoint from config"""
        try:
            path = config.endpoint.v2_path
            method = config.endpoint.v2_method.lower()

            # Create the endpoint handler
            handler = self._create_endpoint_function(config)

            # Add route to router
            self.router.add_api_route(
                path=path,
                endpoint=handler,
                methods=[method.upper()],
                name=f"v2_{method}_{path.replace('/', '_').replace('{', '').replace('}', '')}",
                summary=f"V2 API: {method.upper()} {path}",
                description=f"Generated endpoint from config. Orchestrates {len(config.v1_calls)} V1 API calls.",
                tags=["v2-api"]
            )

            logger.info(f"Registered endpoint: {method.upper()} {path}")

        except Exception as e:
            logger.error(f"Failed to register endpoint from config: {e}", exc_info=True)
            raise

    def register_all_endpoints(self, configs: Dict[str, MappingConfig]) -> None:
        """Register all V2 endpoints from configs"""
        logger.info(f"Registering {len(configs)} V2 endpoints")

        for config_id, config in configs.items():
            try:
                self.register_endpoint(config)
            except Exception as e:
                logger.error(f"Failed to register endpoint for config '{config_id}': {e}")
                continue

        logger.info(f"Successfully registered {len(self.router.routes)} V2 endpoints")

    def get_router(self) -> APIRouter:
        """Get the router with all registered endpoints"""
        return self.router

    def clear_endpoints(self) -> None:
        """Clear all registered endpoints (useful for reloading)"""
        self.router = APIRouter()
        logger.info("Cleared all registered endpoints")