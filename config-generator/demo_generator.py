#!/usr/bin/env python3
"""
Demo script for the Insurance API Config Generator

This script shows how to use the config generator with a mock Qwen response.
In production, this would call the actual Qwen 7B model via Ollama.
"""

from pathlib import Path
import sys
import json
from unittest.mock import patch

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from generator.config_generator import ConfigGenerator
from rich.console import Console
from rich.table import Table

console = Console()


def demo_config_generation():
    """Demonstrate config generation with mock Qwen response"""

    # Mock Qwen response (in production, this would come from actual Qwen model)
    mock_qwen_response = """version: "1.0"
endpoint:
  v2_path: "/api/v2/policies/{policyId}"
  v2_method: "GET"

v1_calls:
  - name: "get_policy_details"
    endpoint: "/api/v1/policy/{policy_num}"
    method: "GET"
    params:
      path:
        - v2_param: "policyId"
          v1_param: "policy_num"
          location: "path"

field_mappings:
  # Direct field mappings
  - v2_path: "policyNumber"
    source: "get_policy_details"
    v1_path: "policy_num"

  - v2_path: "status"
    source: "get_policy_details"
    v1_path: "policy_status"

  # Transformed field - combining first and last name
  - v2_path: "insuredName"
    source: "get_policy_details"
    transform: "{{ get_policy_details.first_name }} {{ get_policy_details.last_name }}"

  # Nested field mapping
  - v2_path: "coverage.amount"
    source: "get_policy_details"
    v1_path: "coverage_amount"

  - v2_path: "coverage.type"
    source: "get_policy_details"
    v1_path: "coverage_type"

  # Stub field - not available in V1
  - v2_path: "digitalSignatureUrl"
    source: "stub"
    stub_value: null
    stub_type: "null"

metadata:
  confidence_score: 0.92
  ambiguous_mappings:
    - v2_field: "beneficiaries"
      proposals:
        - v1_field: "beneficiary_list"
          confidence: 0.75
        - v1_field: "nominees"
          confidence: 0.25"""

    console.print("\n[bold cyan]Insurance API Config Generator - Demo[/bold cyan]\n")

    # Create sample specs
    v2_spec = {
        "openapi": "3.0.0",
        "info": {"title": "Insurance V2 API", "version": "2.0.0"},
        "paths": {
            "/api/v2/policies/{policyId}": {
                "get": {
                    "operationId": "getPolicy",
                    "parameters": [
                        {"name": "policyId", "in": "path", "required": True, "schema": {"type": "string"}}
                    ],
                    "responses": {
                        "200": {
                            "description": "Policy details",
                            "content": {"application/json": {"schema": {"type": "object"}}}
                        }
                    }
                }
            }
        }
    }

    v1_spec = {
        "openapi": "3.0.0",
        "info": {"title": "Legacy V1 API", "version": "1.0.0"},
        "paths": {
            "/api/v1/policy/{policy_num}": {
                "get": {
                    "operationId": "getPolicyV1",
                    "parameters": [
                        {"name": "policy_num", "in": "path", "required": True, "schema": {"type": "string"}}
                    ]
                }
            }
        }
    }

    # Create temp directory for demo
    demo_dir = Path("demo_output")
    demo_dir.mkdir(exist_ok=True)

    # Save specs
    v2_spec_path = demo_dir / "v2_spec.json"
    v1_spec_path = demo_dir / "v1_spec.json"
    output_path = demo_dir / "generated_config.yaml"

    v2_spec_path.write_text(json.dumps(v2_spec, indent=2))
    v1_spec_path.write_text(json.dumps(v1_spec, indent=2))

    console.print("[yellow]Note: Using mock Qwen response for demo[/yellow]")
    console.print("In production, this would call the actual Qwen 7B model via Ollama\n")

    # Generate config with mock response
    generator = ConfigGenerator()

    with patch.object(generator.qwen_client, 'generate', return_value=mock_qwen_response):
        try:
            config = generator.generate_config(
                v2_spec_path=v2_spec_path,
                v1_spec_path=v1_spec_path,
                v2_endpoint_path="/api/v2/policies/{policyId}",
                output_path=output_path
            )

            # Display results
            console.print("\n[bold green]✓ Config generated successfully![/bold green]\n")

            # Create summary table
            table = Table(title="Generated Configuration Summary")
            table.add_column("Property", style="cyan")
            table.add_column("Value", style="yellow")

            table.add_row("V2 Endpoint", config["endpoint"]["v2_path"])
            table.add_row("V2 Method", config["endpoint"]["v2_method"])
            table.add_row("V1 Calls", str(len(config["v1_calls"])))
            table.add_row("Field Mappings", str(len(config["field_mappings"])))
            table.add_row("Confidence Score", f"{config['metadata']['confidence_score']:.2%}")

            if config.get('metadata', {}).get('ambiguous_mappings'):
                table.add_row("Ambiguous Mappings", str(len(config['metadata']['ambiguous_mappings'])))

            console.print(table)

            # Show sample mappings
            console.print("\n[bold]Sample Field Mappings:[/bold]")
            for i, mapping in enumerate(config["field_mappings"][:3], 1):
                if mapping.get("transform"):
                    console.print(f"  {i}. {mapping['v2_path']} ← [transform]")
                elif mapping["source"] == "stub":
                    console.print(f"  {i}. {mapping['v2_path']} ← [stub: null]")
                else:
                    console.print(f"  {i}. {mapping['v2_path']} ← {mapping['v1_path']}")

            console.print(f"\n[green]Config saved to: {output_path}[/green]")

            # Show ambiguous mappings if present
            if config.get('metadata', {}).get('ambiguous_mappings'):
                console.print("\n[yellow]⚠ Ambiguous Mappings Found:[/yellow]")
                for amb in config['metadata']['ambiguous_mappings']:
                    console.print(f"  • {amb['v2_field']}:")
                    for proposal in amb['proposals']:
                        console.print(f"    - {proposal['v1_field']} ({proposal['confidence']:.0%})")

        except Exception as e:
            console.print(f"\n[red]✗ Error: {e}[/red]")
            raise

        finally:
            generator.close()

    console.print("\n[dim]Demo complete. In production, install and run Ollama with Qwen 7B:[/dim]")
    console.print("[dim]  ollama pull qwen:7b[/dim]")
    console.print("[dim]  ollama serve[/dim]")
    console.print("[dim]Then use: generate-config --v2-spec v2.json --v1-spec v1.json --endpoint /api/v2/policies/{policyId} --output config.yaml[/dim]\n")


if __name__ == "__main__":
    demo_config_generation()