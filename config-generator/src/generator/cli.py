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