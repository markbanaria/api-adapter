#!/usr/bin/env python3
"""
Test script for the Qwen config generator.
This script will check if Ollama is running and guide you through testing.
"""

import subprocess
import time
import requests
from pathlib import Path
import sys
from rich.console import Console
from rich.panel import Panel

console = Console()

def check_ollama_status():
    """Check if Ollama is running and accessible"""
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        return response.status_code == 200
    except:
        return False

def check_qwen_model():
    """Check if Qwen model is available"""
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            models = response.json().get("models", [])
            # Check for qwen2.5:7b specifically (same as your chatbot project)
            return any("qwen2.5:7b" in model.get("name", "") for model in models)
    except:
        pass
    return False

def main():
    console.print("\n[bold cyan]Qwen Config Generator Test[/bold cyan]\n")

    # Check Ollama status
    console.print("🔍 Checking Ollama status...")

    if not check_ollama_status():
        console.print("[red]❌ Ollama is not running[/red]")
        console.print("\nTo start Ollama, run:")
        console.print("[yellow]ollama serve[/yellow]")
        console.print("\nThen run this script again.")
        return

    console.print("[green]✅ Ollama is running[/green]")

    # Check Qwen model
    console.print("🔍 Checking for Qwen model...")

    if not check_qwen_model():
        console.print("[red]❌ Qwen 2.5:7b model not found[/red]")
        console.print("\nTo install Qwen 2.5:7b, run:")
        console.print("[yellow]ollama pull qwen2.5:7b[/yellow]")
        console.print("\nThen run this script again.")
        return

    console.print("[green]✅ Qwen model is available[/green]")

    # Test generation
    console.print("\n🚀 Testing config generation...")

    cmd = [
        "python3", "-m", "generator.cli",
        "--v2-spec", "specs/v2/scenario1-simple-rename.json",
        "--v1-spec", "specs/v1/complete-v1-api.json",
        "--endpoint", "/api/v2/policies/{policyId}",
        "--output", "../backend/configs/generated-scenario1.yaml"
    ]

    env = {"PYTHONPATH": "src"}

    try:
        result = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=120)

        if result.returncode == 0:
            console.print("[green]✅ Config generation successful![/green]")
            console.print(result.stdout)

            # Check if output file exists
            output_file = Path("../backend/configs/generated-scenario1.yaml")
            if output_file.exists():
                console.print(f"\n📄 Generated config saved to: {output_file}")
                console.print("\nFirst few lines of generated config:")
                console.print("[dim]" + output_file.read_text()[:500] + "...[/dim]")
        else:
            console.print("[red]❌ Config generation failed[/red]")
            console.print("STDOUT:", result.stdout)
            console.print("STDERR:", result.stderr)

    except subprocess.TimeoutExpired:
        console.print("[red]❌ Generation timed out (>2 minutes)[/red]")
        console.print("This might indicate an issue with the Qwen model response.")
    except Exception as e:
        console.print(f"[red]❌ Error running generator: {e}[/red]")

if __name__ == "__main__":
    main()