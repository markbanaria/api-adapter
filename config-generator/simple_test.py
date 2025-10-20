#!/usr/bin/env python3
"""
Simple test of the config generator with your Qwen setup.
This bypasses CLI dependencies and directly tests the core functionality.
"""

import sys
import time
import subprocess
import requests
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from generator.config_generator import ConfigGenerator

def start_ollama_if_needed():
    """Start Ollama if not running"""
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            print("✅ Ollama is already running")
            return True
    except:
        pass

    print("🔄 Starting Ollama server...")
    try:
        subprocess.Popen(["ollama", "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # Wait for Ollama to be ready
        print("⏳ Waiting for Ollama to be ready...")
        for i in range(30):
            try:
                response = requests.get("http://localhost:11434/", timeout=2)
                if response.status_code == 200:
                    print("✅ Ollama server ready")
                    return True
            except:
                time.sleep(1)

        print("❌ Failed to start Ollama")
        return False
    except Exception as e:
        print(f"❌ Error starting Ollama: {e}")
        return False

def check_qwen_model():
    """Check if qwen2.5:7b is available"""
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            models = response.json().get("models", [])
            has_qwen = any("qwen2.5:7b" in model.get("name", "") for model in models)
            if has_qwen:
                print("✅ Qwen 2.5:7b model available")
                return True
            else:
                print("❌ Qwen 2.5:7b model not found")
                print("Available models:", [m.get("name") for m in models])
                return False
    except Exception as e:
        print(f"❌ Error checking models: {e}")
        return False

def test_generation():
    """Test config generation"""
    print("\n🚀 Testing config generation...")

    # Create generator
    generator = ConfigGenerator()

    try:
        # Generate config
        config = generator.generate_config(
            v2_spec_path=Path("specs/v2/scenario1-simple-rename.json"),
            v1_spec_path=Path("specs/v1/complete-v1-api.json"),
            v2_endpoint_path="/api/v2/policies/{policyId}",
            output_path=Path("../backend/configs/qwen-test-scenario1.yaml")
        )

        print("✅ Config generated successfully!")
        print(f"V1 calls: {len(config['v1_calls'])}")
        print(f"Field mappings: {len(config['field_mappings'])}")
        print(f"Confidence: {config.get('metadata', {}).get('confidence_score', 'N/A')}")

        # Show sample mappings
        print("\nSample field mappings:")
        for i, mapping in enumerate(config["field_mappings"][:3], 1):
            if mapping.get("transform"):
                print(f"  {i}. {mapping['v2_path']} ← [transform]")
            elif mapping["source"] == "stub":
                print(f"  {i}. {mapping['v2_path']} ← [stub]")
            else:
                print(f"  {i}. {mapping['v2_path']} ← {mapping.get('v1_path', 'N/A')}")

        return True

    except Exception as e:
        print(f"❌ Generation failed: {e}")
        return False
    finally:
        generator.close()

def main():
    print("🤖 Simple Qwen Config Generator Test\n")

    # Check Ollama
    if not start_ollama_if_needed():
        return 1

    # Check model
    if not check_qwen_model():
        print("\nTo install qwen2.5:7b, run: ollama pull qwen2.5:7b")
        return 1

    # Test generation
    if test_generation():
        print("\n🎉 Success! Config generator is working with your Qwen setup.")
        return 0
    else:
        return 1

if __name__ == "__main__":
    exit(main())