#!/usr/bin/env python3
"""
Test the config generator using your existing Qwen setup.
This leverages your qwen-chatbot project's Ollama configuration.
"""

import subprocess
import time
import requests
import sys
from pathlib import Path
from rich.console import Console
from rich.panel import Panel

console = Console()

def start_ollama_if_needed():
    """Start Ollama using your existing qwen-chatbot setup"""
    try:
        # Check if Ollama is already running
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            console.print("[green]✅ Ollama is already running[/green]")
            return True
    except:
        pass

    console.print("[yellow]🔄 Starting Ollama server...[/yellow]")

    # Start Ollama serve in background
    try:
        subprocess.Popen(["ollama", "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # Wait for Ollama to be ready
        console.print("⏳ Waiting for Ollama to be ready...")
        for i in range(30):  # Wait up to 30 seconds
            try:
                response = requests.get("http://localhost:11434/", timeout=2)
                if response.status_code == 200:
                    console.print("[green]✅ Ollama server ready[/green]")
                    return True
            except:
                time.sleep(1)

        console.print("[red]❌ Failed to start Ollama[/red]")
        return False

    except Exception as e:
        console.print(f"[red]❌ Error starting Ollama: {e}[/red]")
        return False

def check_qwen_model():
    """Check if qwen2.5:7b model is available"""
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            models = response.json().get("models", [])
            return any("qwen2.5:7b" in model.get("name", "") for model in models)
    except:
        pass
    return False

def pull_qwen_if_needed():
    """Pull qwen2.5:7b model if not available"""
    if check_qwen_model():
        console.print("[green]✅ Qwen 2.5:7b model already available[/green]")
        return True

    console.print("[yellow]📥 Pulling Qwen 2.5:7b model (this may take a while)...[/yellow]")
    try:
        result = subprocess.run(["ollama", "pull", "qwen2.5:7b"],
                              capture_output=True, text=True, timeout=600)  # 10 minute timeout
        if result.returncode == 0:
            console.print("[green]✅ Qwen 2.5:7b model ready[/green]")
            return True
        else:
            console.print(f"[red]❌ Failed to pull model: {result.stderr}[/red]")
            return False
    except subprocess.TimeoutExpired:
        console.print("[red]❌ Model pull timed out[/red]")
        return False
    except Exception as e:
        console.print(f"[red]❌ Error pulling model: {e}[/red]")
        return False

def test_config_generation():
    """Test the config generator with scenario 1"""
    console.print("\n🚀 Testing config generation with Qwen 2.5:7b...")

    cmd = [
        "python3", "-m", "generator.cli",
        "--v2-spec", "specs/v2/scenario1-simple-rename.json",
        "--v1-spec", "specs/v1/complete-v1-api.json",
        "--endpoint", "/api/v2/policies/{policyId}",
        "--output", "../backend/configs/qwen-generated-scenario1.yaml"
    ]

    env = {"PYTHONPATH": "src"}

    try:
        console.print("⏳ Generating config (this may take 1-2 minutes)...")
        result = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=180)

        if result.returncode == 0:
            console.print("[green]✅ Config generation successful![/green]")
            console.print(result.stdout)

            # Show generated config
            output_file = Path("../backend/configs/qwen-generated-scenario1.yaml")
            if output_file.exists():
                console.print(f"\n📄 Generated config saved to: {output_file}")
                console.print("\n[bold]Generated YAML config:[/bold]")
                content = output_file.read_text()
                console.print(f"[dim]{content[:800]}{'...' if len(content) > 800 else ''}[/dim]")
                return True
        else:
            console.print("[red]❌ Config generation failed[/red]")
            console.print("STDOUT:", result.stdout)
            console.print("STDERR:", result.stderr)
            return False

    except subprocess.TimeoutExpired:
        console.print("[red]❌ Generation timed out (>3 minutes)[/red]")
        return False
    except Exception as e:
        console.print(f"[red]❌ Error running generator: {e}[/red]")
        return False

def main():
    console.print(Panel.fit(
        "[bold cyan]🤖 Qwen Config Generator Test[/bold cyan]\n"
        "Using your existing qwen-chatbot Ollama setup",
        title="Insurance API Adapter"
    ))

    # Step 1: Start Ollama
    if not start_ollama_if_needed():
        console.print("\n[red]Failed to start Ollama. Please check your setup.[/red]")
        return 1

    # Step 2: Ensure Qwen model is available
    if not pull_qwen_if_needed():
        console.print("\n[red]Failed to get Qwen model. Please check your internet connection.[/red]")
        return 1

    # Step 3: Test config generation
    if test_config_generation():
        console.print("\n[green]🎉 Success! The config generator is working with your Qwen setup.[/green]")
        console.print("\n[dim]You can now generate configs for all scenarios:")
        console.print("  python3 -m generator.cli --v2-spec specs/v2/scenario2-field-combination.json ...")
        console.print("  python3 -m generator.cli --v2-spec specs/v2/scenario3-param-shift.json ...")
        console.print("  etc.[/dim]")
        return 0
    else:
        console.print("\n[red]❌ Config generation failed. Check the errors above.[/red]")
        return 1

if __name__ == "__main__":
    exit(main())