import json
import yaml
from pathlib import Path
from datetime import datetime
from typing import Dict, Any
import logging
import re

from .qwen_client import QwenClient
from .prompt_templates import SYSTEM_PROMPT, create_mapping_prompt, create_correction_prompt
from .advanced_validator import AdvancedConfigValidator

logger = logging.getLogger(__name__)


class ConfigGenerator:
    """Generates mapping configurations using Qwen 7B"""

    def __init__(self, qwen_base_url: str = "http://localhost:11434"):
        self.qwen_client = QwenClient(base_url=qwen_base_url)

    def load_spec(self, spec_path: Path) -> Dict[str, Any]:
        """Load OpenAPI spec from JSON file"""
        with open(spec_path, 'r') as f:
            return json.load(f)

    def extract_yaml_from_response(self, response: str) -> str:
        """Extract YAML from AI response (may include markdown code blocks)"""
        # Try to find YAML in code blocks
        yaml_match = re.search(r'```ya?ml\n(.*?)\n```', response, re.DOTALL)
        if yaml_match:
            return yaml_match.group(1)

        # Try to find YAML without code blocks
        yaml_match = re.search(r'version:\s*["\']1\.0["\'].*', response, re.DOTALL)
        if yaml_match:
            return yaml_match.group(0)

        # Return as-is and let YAML parser handle it
        return response

    def generate_config(
        self,
        v2_spec_path: Path,
        v1_spec_path: Path,
        v2_endpoint_path: str,
        output_path: Path,
        max_iterations: int = 3
    ) -> Dict[str, Any]:
        """
        Generate mapping config for a V2 endpoint with iterative validation feedback

        Args:
            v2_spec_path: Path to V2 OpenAPI spec
            v1_spec_path: Path to V1 OpenAPI spec (complete)
            v2_endpoint_path: Specific V2 endpoint to map
            output_path: Where to save generated YAML
            max_iterations: Maximum correction attempts

        Returns:
            Generated config as dict
        """
        logger.info(f"Generating config for {v2_endpoint_path}")

        # Load specs
        v2_spec = self.load_spec(v2_spec_path)
        v1_spec = self.load_spec(v1_spec_path)

        logger.info(f"Loaded V2 spec: {v2_spec.get('info', {}).get('title', 'Unknown')}")
        logger.info(f"Loaded V1 spec: {v1_spec.get('info', {}).get('title', 'Unknown')}")

        # Initialize validator
        validator = AdvancedConfigValidator(v1_spec, v2_spec)

        # Create initial prompt
        original_prompt = create_mapping_prompt(v2_spec, v1_spec, v2_endpoint_path)
        current_prompt = original_prompt

        config = None
        yaml_content = None

        # Iterative generation with validation feedback
        for iteration in range(max_iterations):
            logger.info(f"Generation attempt {iteration + 1}/{max_iterations}")

            # Generate with Qwen
            logger.info("Calling Qwen 7B model...")
            response = self.qwen_client.generate(
                prompt=current_prompt,
                system_prompt=SYSTEM_PROMPT,
                temperature=0.1
            )

            logger.info("Received response from Qwen")
            logger.debug(f"Raw response:\n{response}")

            # Extract YAML
            try:
                yaml_content = self.extract_yaml_from_response(response)
            except Exception as e:
                logger.error(f"Failed to extract YAML: {e}")
                if iteration == max_iterations - 1:
                    raise ValueError(f"Failed to extract valid YAML after {max_iterations} attempts")
                continue

            # Parse YAML
            try:
                config = yaml.safe_load(yaml_content)
            except yaml.YAMLError as e:
                error_msg = f"Generated config is not valid YAML: {e}"
                logger.warning(f"Attempt {iteration + 1}: {error_msg}")

                if iteration == max_iterations - 1:
                    raise ValueError(f"Failed to generate valid YAML after {max_iterations} attempts")

                # Create correction prompt for YAML syntax error
                current_prompt = create_correction_prompt(
                    original_prompt,
                    yaml_content or "Invalid YAML",
                    f"YAML_SYNTAX_ERROR: {error_msg}\nFix: Ensure proper YAML indentation and syntax"
                )
                continue

            # Add generation timestamp if not present
            if 'metadata' in config:
                if 'generated_at' not in config['metadata']:
                    config['metadata']['generated_at'] = datetime.now().isoformat()
            else:
                config['metadata'] = {
                    'generated_at': datetime.now().isoformat(),
                    'confidence_score': 0.8  # default
                }

            # Comprehensive validation
            is_valid, errors = validator.validate_config(config)

            if is_valid:
                logger.info(f"✅ Config validation passed on attempt {iteration + 1}")
                break
            else:
                logger.warning(f"⚠️ Attempt {iteration + 1}: Found {len(errors)} validation errors")

                if iteration == max_iterations - 1:
                    error_summary = validator.format_errors_for_ai(errors)
                    logger.error(f"Final validation errors:\n{error_summary}")
                    raise ValueError(f"Config validation failed after {max_iterations} attempts")

                # Create correction prompt with specific errors
                error_summary = validator.format_errors_for_ai(errors)
                current_prompt = create_correction_prompt(
                    original_prompt,
                    yaml_content,
                    error_summary
                )
                logger.info(f"🔄 Generating correction prompt for attempt {iteration + 2}")

        # Final basic validation (legacy check)
        self._validate_config(config)

        # Save to file
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)

        logger.info(f"✅ Config saved to {output_path}")
        logger.info(f"📊 Summary:")
        logger.info(f"  - V1 calls: {len(config.get('v1_calls', []))}")
        logger.info(f"  - Field mappings: {len(config.get('field_mappings', []))}")
        logger.info(f"  - Confidence: {config.get('metadata', {}).get('confidence_score', 'N/A')}")

        if config.get('metadata', {}).get('ambiguous_mappings'):
            logger.warning(f"Found {len(config['metadata']['ambiguous_mappings'])} ambiguous mappings")

        return config

    def _validate_config(self, config: Dict[str, Any]):
        """Basic validation of generated config"""
        required_keys = ['version', 'endpoint', 'v1_calls', 'field_mappings']

        for key in required_keys:
            if key not in config:
                raise ValueError(f"Generated config missing required key: {key}")

        if not config['v1_calls']:
            raise ValueError("Generated config has no V1 calls")

        if not config['field_mappings']:
            raise ValueError("Generated config has no field mappings")

        logger.info("Config validation passed")

    def close(self):
        """Close Qwen client"""
        self.qwen_client.close()