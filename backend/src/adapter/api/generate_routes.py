"""
API routes for AI-powered configuration generation
"""

import tempfile
import json
from pathlib import Path
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from typing import List, Optional
from pydantic import BaseModel
import logging
import subprocess
import os

logger = logging.getLogger(__name__)

router = APIRouter()


class GenerateConfigRequest(BaseModel):
    """Request for generating config via uploaded specs"""
    v2_endpoint_path: str
    config_name: str
    v1_spec_content: dict
    v2_spec_content: dict


class GeneratedConfigResponse(BaseModel):
    """Response containing generated config"""
    success: bool
    config: Optional[dict] = None
    confidence_score: Optional[float] = None
    ambiguous_mappings: Optional[List[dict]] = None
    error_message: Optional[str] = None


@router.post("/generate-config", response_model=GeneratedConfigResponse)
async def generate_config_from_specs(request: GenerateConfigRequest):
    """
    Generate configuration using Qwen AI from uploaded OpenAPI specs
    """
    try:
        logger.info(f"Generating config for endpoint: {request.v2_endpoint_path}")

        # Create temporary files for specs
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Save specs to temporary files
            v1_spec_path = temp_path / "v1_spec.json"
            v2_spec_path = temp_path / "v2_spec.json"
            output_path = temp_path / f"{request.config_name}.yaml"

            with open(v1_spec_path, 'w') as f:
                json.dump(request.v1_spec_content, f, indent=2)

            with open(v2_spec_path, 'w') as f:
                json.dump(request.v2_spec_content, f, indent=2)

            # Use config-generator CLI to generate config
            try:
                # Get the config-generator path relative to backend
                config_gen_path = Path(__file__).parent.parent.parent.parent.parent / "config-generator"

                # Build command using config-generator's virtual environment
                python_path = config_gen_path / "venv" / "bin" / "python"
                cmd = [
                    str(python_path), "-m", "generator.cli",
                    "--v2-spec", str(v2_spec_path),
                    "--v1-spec", str(v1_spec_path),
                    "--endpoint", request.v2_endpoint_path,
                    "--output", str(output_path)
                ]

                # Set environment and run
                env = os.environ.copy()
                env["PYTHONPATH"] = str(config_gen_path / "src")

                logger.info(f"Running command: {' '.join(cmd)}")
                logger.info(f"Working directory: {config_gen_path}")

                # Retry logic for handling model busy/timeout issues
                max_retries = 2
                for attempt in range(max_retries + 1):
                    try:
                        result = subprocess.run(
                            cmd,
                            cwd=config_gen_path,
                            env=env,
                            capture_output=True,
                            text=True,
                            timeout=300  # 5 minute timeout for AI generation
                        )

                        if result.returncode == 0:
                            break  # Success, exit retry loop

                        # Log the error
                        error_msg = result.stderr.strip()
                        logger.warning(f"Config generation attempt {attempt + 1} failed: {error_msg}")

                        # If it's an "Aborted!" error and we have retries left, wait and try again
                        if "Aborted!" in error_msg and attempt < max_retries:
                            import time
                            wait_time = (attempt + 1) * 5  # Wait 5, 10 seconds
                            logger.info(f"Retrying in {wait_time} seconds...")
                            time.sleep(wait_time)
                            continue

                        # Final failure
                        return GeneratedConfigResponse(
                            success=False,
                            error_message=f"AI generation failed after {attempt + 1} attempts: {error_msg}"
                        )

                    except subprocess.TimeoutExpired:
                        logger.warning(f"Config generation attempt {attempt + 1} timed out")
                        if attempt < max_retries:
                            logger.info(f"Retrying generation...")
                            continue
                        else:
                            return GeneratedConfigResponse(
                                success=False,
                                error_message="Config generation timed out after multiple attempts"
                            )

                # Load the generated config
                if output_path.exists():
                    import yaml
                    with open(output_path, 'r') as f:
                        config = yaml.safe_load(f)

                    # Extract metadata
                    metadata = config.get('metadata', {})
                    confidence_score = metadata.get('confidence_score')
                    ambiguous_mappings = metadata.get('ambiguous_mappings', [])

                    logger.info(f"Config generated successfully with confidence: {confidence_score}")

                    return GeneratedConfigResponse(
                        success=True,
                        config=config,
                        confidence_score=confidence_score,
                        ambiguous_mappings=ambiguous_mappings
                    )
                else:
                    return GeneratedConfigResponse(
                        success=False,
                        error_message="Config file was not generated"
                    )

            except Exception as e:
                logger.error(f"Error running config generator: {e}")
                return GeneratedConfigResponse(
                    success=False,
                    error_message=f"Generation error: {str(e)}"
                )

    except Exception as e:
        logger.error(f"Config generation failed: {e}")
        return GeneratedConfigResponse(
            success=False,
            error_message=str(e)
        )


@router.post("/upload-and-generate")
async def upload_and_generate_config(
    v1_spec: UploadFile = File(...),
    v2_spec: UploadFile = File(...),
    endpoint_path: str = Form(...),
    config_name: str = Form(...)
):
    """
    Upload OpenAPI specs and generate config in one step
    """
    try:
        # Read uploaded files
        v1_content = await v1_spec.read()
        v2_content = await v2_spec.read()

        # Parse JSON
        try:
            v1_spec_dict = json.loads(v1_content.decode('utf-8'))
            v2_spec_dict = json.loads(v2_content.decode('utf-8'))
        except json.JSONDecodeError as e:
            raise HTTPException(status_code=400, detail=f"Invalid JSON in uploaded files: {e}")

        # Create request and generate
        request = GenerateConfigRequest(
            v2_endpoint_path=endpoint_path,
            config_name=config_name,
            v1_spec_content=v1_spec_dict,
            v2_spec_content=v2_spec_dict
        )

        return await generate_config_from_specs(request)

    except Exception as e:
        logger.error(f"Upload and generate failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/save-generated-config/{config_name}")
async def save_generated_config(config_name: str, config: dict):
    """
    Save a generated configuration to the configs directory
    """
    try:
        # Get configs directory (should be backend/configs, not backend/src/configs)
        configs_dir = Path(__file__).parent.parent.parent.parent / "configs"
        configs_dir.mkdir(exist_ok=True)

        # Save config as YAML
        config_path = configs_dir / f"{config_name}.yaml"

        import yaml
        with open(config_path, 'w') as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)

        logger.info(f"Config saved to {config_path}")

        return {
            "success": True,
            "message": f"Configuration '{config_name}' saved successfully",
            "path": str(config_path)
        }

    except Exception as e:
        logger.error(f"Failed to save config: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save config: {e}")


@router.get("/check-qwen-status")
async def check_qwen_status():
    """
    Check if Qwen model is available
    """
    try:
        # Try to call ollama list
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0:
            # Check if qwen2.5:7b model is in the list
            has_qwen = "qwen2.5:7b" in result.stdout

            return {
                "ollama_available": True,
                "qwen_available": has_qwen,
                "models": result.stdout.strip().split('\n') if result.stdout else []
            }
        else:
            return {
                "ollama_available": False,
                "qwen_available": False,
                "error": result.stderr
            }

    except subprocess.TimeoutExpired:
        return {
            "ollama_available": False,
            "qwen_available": False,
            "error": "Ollama service timeout"
        }
    except FileNotFoundError:
        return {
            "ollama_available": False,
            "qwen_available": False,
            "error": "Ollama not installed"
        }
    except Exception as e:
        return {
            "ollama_available": False,
            "qwen_available": False,
            "error": str(e)
        }