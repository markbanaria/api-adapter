# User Story 008: Qwen 7B Config Generator

## Story
As a developer, I want a CLI tool that uses Qwen 7B to automatically generate mapping configurations from V1 and V2 OpenAPI specs with confidence scores and ambiguous mapping proposals.

## Acceptance Criteria
- [ ] CLI tool accepts V2 spec (single endpoint) and V1 spec (complete) as inputs
- [ ] Constructs comprehensive prompt with domain context
- [ ] Calls local Qwen 7B model via API
- [ ] Parses AI response into YAML config format
- [ ] Includes confidence scores and ambiguous mapping proposals
- [ ] Validates generated config against schema
- [ ] Saves config to output directory
- [ ] Handles errors gracefully
- [ ] Works with all 7 test scenarios

## Technical Details

### Prompt Templates (config-generator/src/generator/prompt_templates.py)

```python
SYSTEM_PROMPT = """You are an expert API mapping specialist for insurance systems. Your task is to analyze V1 (legacy) and V2 (modern) API specifications and generate precise field mappings.

You understand:
- Life insurance and ILP (Investment-Linked Policy) products
- Common field naming conventions in insurance APIs
- Data transformations (field combinations, type conversions, nested structures)
- Parameter location shifts (path, query, body)

Generate mappings in YAML format following the exact schema provided."""


def create_mapping_prompt(v2_spec: dict, v1_spec: dict, v2_endpoint_path: str) -> str:
    """Create a detailed prompt for config generation"""
    
    # Extract V2 endpoint details
    v2_endpoint = None
    for path, methods in v2_spec.get("paths", {}).items():
        if path == v2_endpoint_path:
            v2_endpoint = {"path": path, "methods": methods}
            break
    
    if not v2_endpoint:
        raise ValueError(f"V2 endpoint {v2_endpoint_path} not found in spec")
    
    # Extract all V1 endpoints
    v1_endpoints = v2_spec.get("paths", {})
    
    prompt = f"""# Task: Generate API Mapping Configuration

## Domain Context
- **Industry**: Life Insurance & Investment-Linked Policies (ILP)
- **Goal**: Map legacy V1 API to modern V2 API
- **Approach**: Semantic field matching with transformations

## V2 API Endpoint (TARGET)
```json
{v2_endpoint}
```

## V1 API Endpoints (SOURCE - Complete API)
```json
{v1_endpoints}
```

## Mapping Requirements

### 1. Identify Required V1 Endpoints
- Analyze which V1 endpoints contain data needed for the V2 response
- You may need MULTIPLE V1 endpoints to build one V2 response
- List each V1 endpoint with a unique name

### 2. Map Parameters
- Map V2 parameters to V1 parameters
- Handle location shifts:
  - V2 path param → V1 query param
  - V2 query param → V1 path param
  - V2 body param → V1 query param
- Use the `location` field to indicate where the V2 param comes from

### 3. Map Response Fields
- Match V2 fields to V1 fields semantically (not just by name)
- For field combinations (e.g., fullName = firstName + lastName):
  - Use Jinja2 syntax: `{{{{ v1_call_name.field1 }}}} {{{{ v1_call_name.field2 }}}}`
- For nested V1 fields (e.g., policy.details.type):
  - Use dot notation in v1_path
- For V2 fields with no V1 equivalent:
  - Set source to "stub"
  - Provide appropriate stub_value (null, empty string, etc.)

### 4. Confidence Scoring
- Assign confidence score (0.0-1.0) to overall mapping
- If any field mapping is ambiguous, list it in `ambiguous_mappings` with multiple proposals

## Output Format

Generate YAML in this EXACT format:

```yaml
version: "1.0"
endpoint:
  v2_path: "<V2 endpoint path>"
  v2_method: "<HTTP method>"

v1_calls:
  - name: "<unique_identifier>"
    endpoint: "<V1 endpoint path>"
    method: "<HTTP method>"
    params:
      path:  # Optional
        - v2_param: "<V2 parameter name>"
          v1_param: "<V1 parameter name>"
          location: "path"  # where this param comes from in V2
      query:  # Optional
        - v2_param: "<V2 parameter name>"
          v1_param: "<V1 parameter name>"
          location: "<path|query|body>"
      body:  # Optional
        - v2_param: "<V2 parameter name>"
          v1_param: "<V1 parameter name>"
          location: "body"

field_mappings:
  - v2_path: "<V2 field path with dots for nesting>"
    source: "<v1_call_name or 'stub'>"
    v1_path: "<V1 field path with dots>"  # null if using transform
    transform: null  # or Jinja2 expression like "{{{{ source.field1 }}}} {{{{ source.field2 }}}}"
    
  # For unmappable fields:
  - v2_path: "<field_name>"
    source: "stub"
    stub_value: null
    stub_type: "null"

metadata:
  generated_at: "<ISO 8601 timestamp>"
  confidence_score: <0.0-1.0>
  ambiguous_mappings:  # Optional
    - v2_field: "<field_name>"
      proposals:
        - v1_field: "<option1>"
          confidence: <0.0-1.0>
        - v1_field: "<option2>"
          confidence: <0.0-1.0>
```

## Important Notes
- Use semantic matching (e.g., "policy_num" → "policyNumber")
- Common insurance fields:
  - Customer: first_name, last_name, customer_age, email_address
  - Policy: policy_num, policy_status, policy_type, premium_amount
  - Coverage: amount, type
  - ILP: fund_value, unit_price, allocation_rate
- Be conservative with confidence scores (0.95+ only for very clear mappings)
- Always provide reasoning for ambiguous mappings

Generate the YAML configuration now:"""
    
    return prompt
```

### Qwen Client (config-generator/src/generator/qwen_client.py)

```python
import httpx
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class QwenClient:
    """Client for local Qwen 7B model"""
    
    def __init__(
        self,
        base_url: str = "http://localhost:11434",  # Ollama default
        model: str = "qwen:7b",
        timeout: float = 120.0
    ):
        self.base_url = base_url
        self.model = model
        self.timeout = timeout
        self.client = httpx.Client(timeout=timeout)
    
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.1,  # Low temp for consistent config generation
        max_tokens: int = 4096
    ) -> str:
        """
        Generate completion from Qwen model
        
        Args:
            prompt: User prompt
            system_prompt: System prompt (optional)
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum tokens to generate
            
        Returns:
            Generated text
        """
        url = f"{self.base_url}/api/generate"
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "system": system_prompt,
            "temperature": temperature,
            "stream": False,
            "options": {
                "num_predict": max_tokens
            }
        }
        
        logger.info(f"Calling Qwen model: {self.model}")
        logger.debug(f"Prompt length: {len(prompt)} chars")
        
        try:
            response = self.client.post(url, json=payload)
            response.raise_for_status()
            
            data = response.json()
            generated_text = data.get("response", "")
            
            logger.info(f"Generated {len(generated_text)} characters")
            return generated_text
            
        except httpx.HTTPError as e:
            logger.error(f"Qwen API error: {e}")
            raise RuntimeError(f"Failed to call Qwen model: {e}")
    
    def close(self):
        """Close HTTP client"""
        self.client.close()
```

### Config Generator (config-generator/src/generator/config_generator.py)

```python
import json
import yaml
from pathlib import Path
from datetime import datetime
from typing import Dict, Any
import logging
import re

from .qwen_client import QwenClient
from .prompt_templates import SYSTEM_PROMPT, create_mapping_prompt

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
        output_path: Path
    ) -> Dict[str, Any]:
        """
        Generate mapping config for a V2 endpoint
        
        Args:
            v2_spec_path: Path to V2 OpenAPI spec
            v1_spec_path: Path to V1 OpenAPI spec (complete)
            v2_endpoint_path: Specific V2 endpoint to map
            output_path: Where to save generated YAML
            
        Returns:
            Generated config as dict
        """
        logger.info(f"Generating config for {v2_endpoint_path}")
        
        # Load specs
        v2_spec = self.load_spec(v2_spec_path)
        v1_spec = self.load_spec(v1_spec_path)
        
        logger.info(f"Loaded V2 spec: {v2_spec.get('info', {}).get('title', 'Unknown')}")
        logger.info(f"Loaded V1 spec: {v1_spec.get('info', {}).get('title', 'Unknown')}")
        
        # Create prompt
        prompt = create_mapping_prompt(v2_spec, v1_spec, v2_endpoint_path)
        
        # Generate with Qwen
        logger.info("Calling Qwen 7B model...")
        response = self.qwen_client.generate(
            prompt=prompt,
            system_prompt=SYSTEM_PROMPT,
            temperature=0.1
        )
        
        logger.info("Received response from Qwen")
        logger.debug(f"Raw response:\n{response}")
        
        # Extract YAML
        yaml_content = self.extract_yaml_from_response(response)
        
        # Parse YAML
        try:
            config = yaml.safe_load(yaml_content)
        except yaml.YAMLError as e:
            logger.error(f"Failed to parse YAML: {e}")
            logger.error(f"YAML content:\n{yaml_content}")
            raise ValueError(f"Generated config is not valid YAML: {e}")
        
        # Add generation timestamp if not present
        if 'metadata' in config:
            if 'generated_at' not in config['metadata']:
                config['metadata']['generated_at'] = datetime.now().isoformat()
        else:
            config['metadata'] = {
                'generated_at': datetime.now().isoformat(),
                'confidence_score': 0.8  # default
            }
        
        # Validate basic structure
        self._validate_config(config)
        
        # Save to file
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)
        
        logger.info(f"Config saved to {output_path}")
        logger.info(f"Confidence score: {config.get('metadata', {}).get('confidence_score', 'N/A')}")
        
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
```

### CLI (config-generator/src/generator/cli.py)

```python
import click
from pathlib import Path
import logging
from rich.logging import RichHandler
from rich.console import Console

from .config_generator import ConfigGenerator

# Setup rich logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[RichHandler(rich_tracebacks=True)]
)
logger = logging.getLogger(__name__)
console = Console()


@click.command()
@click.option(
    '--v2-spec',
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help='Path to V2 OpenAPI spec (JSON)'
)
@click.option(
    '--v1-spec',
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help='Path to complete V1 OpenAPI spec (JSON)'
)
@click.option(
    '--endpoint',
    type=str,
    required=True,
    help='V2 endpoint path to generate config for (e.g., /api/v2/policies/{id})'
)
@click.option(
    '--output',
    type=click.Path(path_type=Path),
    required=True,
    help='Output path for generated YAML config'
)
@click.option(
    '--qwen-url',
    type=str,
    default='http://localhost:11434',
    help='Qwen API base URL (default: http://localhost:11434)'
)
def main(v2_spec: Path, v1_spec: Path, endpoint: str, output: Path, qwen_url: str):
    """Generate API mapping configuration using Qwen 7B"""
    
    console.print("\n[bold cyan]Insurance API Config Generator[/bold cyan]")
    console.print(f"V2 Spec: {v2_spec}")
    console.print(f"V1 Spec: {v1_spec}")
    console.print(f"Endpoint: {endpoint}")
    console.print(f"Output: {output}\n")
    
    try:
        generator = ConfigGenerator(qwen_base_url=qwen_url)
        
        config = generator.generate_config(
            v2_spec_path=v2_spec,
            v1_spec_path=v1_spec,
            v2_endpoint_path=endpoint,
            output_path=output
        )
        
        generator.close()
        
        console.print("\n[bold green]✓ Config generated successfully![/bold green]")
        
        # Display summary
        console.print(f"\n[bold]Summary:[/bold]")
        console.print(f"  V1 calls: {len(config['v1_calls'])}")
        console.print(f"  Field mappings: {len(config['field_mappings'])}")
        console.print(f"  Confidence: {config.get('metadata', {}).get('confidence_score', 'N/A')}")
        
        if config.get('metadata', {}).get('ambiguous_mappings'):
            console.print(f"\n[yellow]⚠ {len(config['metadata']['ambiguous_mappings'])} ambiguous mappings found[/yellow]")
            console.print("  Review the config file for details")
        
    except Exception as e:
        console.print(f"\n[bold red]✗ Error: {e}[/bold red]")
        logger.exception("Config generation failed")
        raise click.Abort()


if __name__ == '__main__':
    main()
```

## Testing Checklist
- [ ] CLI accepts all required arguments
- [ ] V2 and V1 specs loaded correctly
- [ ] Prompt constructed with full context
- [ ] Qwen API called successfully
- [ ] YAML extracted from response
- [ ] Config parsed and validated
- [ ] Generated config saved to file
- [ ] Works with all 7 test scenarios
- [ ] Confidence scores included
- [ ] Ambiguous mappings detected and listed

## Usage Example

```bash
# Generate config for scenario 1
generate-config \
  --v2-spec specs/v2/scenario1-simple-rename.json \
  --v1-spec specs/v1/complete-v1-api.json \
  --endpoint "/api/v2/policies/{policyId}" \
  --output ../backend/configs/scenario1.yaml

# Generate all scenarios
for scenario in scenario{1..7}*.json; do
  generate-config \
    --v2-spec "specs/v2/$scenario" \
    --v1-spec "specs/v1/complete-v1-api.json" \
    --endpoint $(jq -r '.paths | keys[0]' "specs/v2/$scenario") \
    --output "../backend/configs/${scenario%.json}.yaml"
done
```

## Definition of Done
- QwenClient can call local Qwen 7B model
- Prompt templates include full context
- Config generator parses AI responses
- CLI tool works end-to-end
- Generated configs validate against schema
- Works with all 7 test scenarios
- Error handling for invalid responses
- Confidence scores and ambiguous mappings captured