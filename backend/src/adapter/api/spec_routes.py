"""
API routes for OpenAPI specification management
"""

import os
import json
from pathlib import Path
from fastapi import APIRouter, HTTPException, UploadFile, File
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import logging
import yaml

logger = logging.getLogger(__name__)

router = APIRouter()


class SpecFile(BaseModel):
    """OpenAPI specification file info"""
    id: str
    name: str
    path: str
    version: str
    type: str  # 'v1' or 'v2'
    title: Optional[str] = None
    description: Optional[str] = None


class EndpointInfo(BaseModel):
    """Endpoint information extracted from OpenAPI spec"""
    path: str
    method: str
    operationId: Optional[str] = None
    summary: Optional[str] = None
    description: Optional[str] = None
    parameters: Optional[List[Dict]] = None
    requestBody: Optional[Dict] = None
    responses: Optional[Dict] = None


class SpecDetails(BaseModel):
    """Detailed OpenAPI specification with endpoints"""
    id: str
    name: str
    path: str
    version: str
    type: str
    title: Optional[str] = None
    description: Optional[str] = None
    endpoints: List[EndpointInfo]
    content: Dict[str, Any]


def get_specs_directory(spec_type: str) -> Path:
    """Get the directory for V1 or V2 specs"""
    config_gen_path = Path(__file__).parent.parent.parent.parent.parent / "config-generator"
    specs_dir = config_gen_path / "specs" / spec_type

    # Create directory if it doesn't exist
    specs_dir.mkdir(parents=True, exist_ok=True)

    return specs_dir


def parse_openapi_spec(file_path: Path) -> Dict[str, Any]:
    """Parse OpenAPI specification from JSON or YAML file"""
    try:
        content = file_path.read_text()

        if file_path.suffix.lower() in ['.yaml', '.yml']:
            spec = yaml.safe_load(content)
        else:
            spec = json.loads(content)

        return spec
    except Exception as e:
        logger.error(f"Failed to parse OpenAPI spec {file_path}: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to parse OpenAPI spec: {e}")


def extract_endpoints_from_spec(spec: Dict[str, Any]) -> List[EndpointInfo]:
    """Extract endpoint information from OpenAPI specification"""
    endpoints = []

    if 'paths' not in spec:
        return endpoints

    for path, methods in spec['paths'].items():
        for method, details in methods.items():
            # Skip non-HTTP methods (like 'parameters', 'servers', etc.)
            if method.lower() not in ['get', 'post', 'put', 'delete', 'patch', 'options', 'head']:
                continue

            endpoint = EndpointInfo(
                path=path,
                method=method.upper(),
                operationId=details.get('operationId'),
                summary=details.get('summary'),
                description=details.get('description'),
                parameters=details.get('parameters', []),
                requestBody=details.get('requestBody'),
                responses=details.get('responses', {})
            )
            endpoints.append(endpoint)

    return endpoints


@router.get("/specs/list", response_model=List[SpecFile])
async def list_spec_files(spec_type: Optional[str] = None):
    """
    List available OpenAPI specification files
    spec_type: Optional filter for 'v1' or 'v2' specs
    """
    try:
        spec_files = []

        # Get both V1 and V2 specs if no type specified
        types_to_check = [spec_type] if spec_type else ['v1', 'v2']

        for stype in types_to_check:
            specs_dir = get_specs_directory(stype)

            if not specs_dir.exists():
                continue

            # Find all JSON and YAML files
            for file_path in specs_dir.glob('*'):
                if file_path.suffix.lower() not in ['.json', '.yaml', '.yml']:
                    continue

                try:
                    spec = parse_openapi_spec(file_path)

                    spec_file = SpecFile(
                        id=f"{stype}_{file_path.stem}",
                        name=file_path.name,
                        path=str(file_path),
                        version=spec.get('info', {}).get('version', '1.0.0'),
                        type=stype,
                        title=spec.get('info', {}).get('title'),
                        description=spec.get('info', {}).get('description')
                    )
                    spec_files.append(spec_file)
                except Exception as e:
                    logger.warning(f"Failed to process spec file {file_path}: {e}")
                    continue

        logger.info(f"Found {len(spec_files)} spec files")
        return spec_files

    except Exception as e:
        logger.error(f"Failed to list spec files: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list spec files: {e}")


@router.get("/specs/{spec_id}/details", response_model=SpecDetails)
async def get_spec_details(spec_id: str):
    """
    Get detailed information about a specific OpenAPI specification including endpoints
    """
    try:
        # Parse spec_id (format: v1_filename or v2_filename)
        parts = spec_id.split('_', 1)
        if len(parts) != 2 or parts[0] not in ['v1', 'v2']:
            raise HTTPException(status_code=400, detail="Invalid spec ID format")

        spec_type = parts[0]
        filename = parts[1]

        # Find the spec file
        specs_dir = get_specs_directory(spec_type)

        # Try different extensions
        spec_path = None
        for ext in ['.json', '.yaml', '.yml']:
            potential_path = specs_dir / f"{filename}{ext}"
            if potential_path.exists():
                spec_path = potential_path
                break

        if not spec_path:
            raise HTTPException(status_code=404, detail="Specification file not found")

        # Parse the spec
        spec = parse_openapi_spec(spec_path)

        # Extract endpoints
        endpoints = extract_endpoints_from_spec(spec)

        # Build response
        spec_details = SpecDetails(
            id=spec_id,
            name=spec_path.name,
            path=str(spec_path),
            version=spec.get('info', {}).get('version', '1.0.0'),
            type=spec_type,
            title=spec.get('info', {}).get('title'),
            description=spec.get('info', {}).get('description'),
            endpoints=endpoints,
            content=spec
        )

        logger.info(f"Retrieved details for spec {spec_id} with {len(endpoints)} endpoints")
        return spec_details

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get spec details: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get spec details: {e}")


@router.post("/specs/upload")
async def upload_spec_file(
    file: UploadFile = File(...),
    spec_type: str = "v2"
):
    """
    Upload a new OpenAPI specification file
    """
    try:
        if spec_type not in ['v1', 'v2']:
            raise HTTPException(status_code=400, detail="spec_type must be 'v1' or 'v2'")

        # Validate file extension
        if not file.filename.endswith(('.json', '.yaml', '.yml')):
            raise HTTPException(status_code=400, detail="File must be JSON or YAML")

        # Read file content
        content = await file.read()

        # Parse to validate it's valid OpenAPI
        try:
            if file.filename.endswith(('.yaml', '.yml')):
                spec = yaml.safe_load(content.decode('utf-8'))
            else:
                spec = json.loads(content.decode('utf-8'))
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid OpenAPI specification: {e}")

        # Save to specs directory
        specs_dir = get_specs_directory(spec_type)
        file_path = specs_dir / file.filename

        # Save the file
        file_path.write_bytes(content)

        # Extract endpoints
        endpoints = extract_endpoints_from_spec(spec)

        logger.info(f"Uploaded spec file {file.filename} to {spec_type} with {len(endpoints)} endpoints")

        return {
            "success": True,
            "message": f"Specification uploaded successfully",
            "spec_id": f"{spec_type}_{file_path.stem}",
            "endpoints_count": len(endpoints)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to upload spec file: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to upload spec file: {e}")


@router.delete("/specs/{spec_id}")
async def delete_spec_file(spec_id: str):
    """
    Delete an OpenAPI specification file
    """
    try:
        # Parse spec_id
        parts = spec_id.split('_', 1)
        if len(parts) != 2 or parts[0] not in ['v1', 'v2']:
            raise HTTPException(status_code=400, detail="Invalid spec ID format")

        spec_type = parts[0]
        filename = parts[1]

        # Find the spec file
        specs_dir = get_specs_directory(spec_type)

        # Try different extensions
        spec_path = None
        for ext in ['.json', '.yaml', '.yml']:
            potential_path = specs_dir / f"{filename}{ext}"
            if potential_path.exists():
                spec_path = potential_path
                break

        if not spec_path:
            raise HTTPException(status_code=404, detail="Specification file not found")

        # Delete the file
        spec_path.unlink()

        logger.info(f"Deleted spec file {spec_id}")

        return {
            "success": True,
            "message": f"Specification {spec_id} deleted successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete spec file: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete spec file: {e}")