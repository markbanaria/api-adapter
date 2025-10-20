from fastapi import FastAPI, Request, HTTPException, Path, Query
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
from pathlib import Path as FilePath
from typing import Dict, Any
import json
from uuid import uuid4
import os

from .config_loader import ConfigLoader
from .orchestrator import V1Orchestrator, V1OrchestratorError
from .response_builder import V2ResponseBuilder, ResponseBuilderError
from .endpoint_generator import EndpointGenerator
from .models import MappingConfig
from .api.config_routes import router as config_router, init_config_routes
from .api.generate_routes import router as generate_router
from .api.spec_routes import router as spec_router
from .file_watcher import ConfigFileWatcher

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
endpoint_generator: EndpointGenerator
endpoint_configs: Dict[str, MappingConfig] = {}
file_watcher: ConfigFileWatcher = None


async def reload_configs():
    """Reload all configurations and regenerate endpoints"""
    global endpoint_configs, endpoint_generator, app

    try:
        logger.info("Reloading configurations...")

        # Load all configs
        new_configs = config_loader.load_all_configs()

        # Clear existing endpoints
        endpoint_generator.clear_endpoints()

        # Register new endpoints
        endpoint_generator.register_all_endpoints(new_configs)

        # Update global state
        endpoint_configs.clear()
        endpoint_configs.update(new_configs)

        # Update the FastAPI app router
        # Remove old router and add new one
        app.router.routes = [route for route in app.router.routes
                           if not hasattr(route, 'tags') or 'v2-api' not in (route.tags or [])]
        app.include_router(endpoint_generator.get_router())

        logger.info(f"Successfully reloaded {len(new_configs)} configurations")

    except Exception as e:
        logger.error(f"Failed to reload configurations: {e}", exc_info=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown logic"""
    global config_loader, orchestrator, response_builder, endpoint_generator, endpoint_configs, file_watcher

    # Startup
    logger.info("Starting Insurance API Adapter...")

    # Initialize configuration loader (configs loaded on demand)
    config_dir = os.getenv("CONFIG_DIR", str(FilePath(__file__).parent.parent.parent / "configs"))
    logger.info(f"Config directory resolved to: {config_dir}")
    config_loader = ConfigLoader(FilePath(config_dir))

    # Load existing configurations if any exist
    try:
        endpoint_configs = config_loader.load_all_configs()
        logger.info(f"Loaded {len(endpoint_configs)} endpoint configurations")
    except Exception:
        logger.info("No existing configurations found - starting fresh")
        endpoint_configs = {}

    # Initialize orchestrator
    v1_base_url = os.getenv("V1_BASE_URL", "http://localhost:8001")
    orchestrator = V1Orchestrator(v1_base_url=v1_base_url)

    # Initialize response builder
    response_builder = V2ResponseBuilder()

    # Initialize endpoint generator and register V2 endpoints
    endpoint_generator = EndpointGenerator(orchestrator)
    endpoint_generator.register_all_endpoints(endpoint_configs)

    # Include the V2 API router
    app.include_router(endpoint_generator.get_router())

    # Initialize config API routes
    init_config_routes(config_dir, endpoint_configs)

    # Start file watcher for automatic config reloading
    file_watcher = ConfigFileWatcher(FilePath(config_dir), reload_configs)
    file_watcher.start()

    logger.info("Insurance API Adapter started successfully")

    yield

    # Shutdown
    if file_watcher:
        file_watcher.stop()
    await orchestrator.close()
    logger.info("Insurance API Adapter shut down")


app = FastAPI(
    title="Insurance API V2 Adapter",
    description="V1 to V2 API adapter for Life & ILP insurance products",
    version="0.1.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include config routes
app.include_router(config_router)
app.include_router(generate_router)
app.include_router(spec_router)


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


