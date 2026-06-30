#!/usr/bin/env python3
"""
Verify free LLM provider keys and endpoints.
Run before adding to routing: python3 scripts/verify-providers.py

Checks:
  - .env file exists and contains keys
  - API keys are set and non-empty
  - Endpoints are reachable and respond with 200 or 401 (not 0% network failure)
  - Models list is readable from each provider
"""

import os
import json
import sys
from pathlib import Path
import urllib.request
import urllib.error

def check_env_file():
    """Check ~/.hermes/.env exists and is readable."""
    env_path = Path.home() / ".hermes" / ".env"
    if not env_path.exists():
        print(f"ERROR: {env_path} does not exist")
        return False
    try:
        with open(env_path) as f:
            content = f.read()
        print(f"✓ .env file found ({len(content)} bytes)")
        return True
    except Exception as e:
        print(f"ERROR reading .env: {e}")
        return False

def load_env():
    """Load env vars from ~/.hermes/.env"""
    env_path = Path.home() / ".hermes" / ".env"
    env = {}
    try:
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    env[k.strip()] = v.strip().strip('"').strip("'")
        return env
    except Exception as e:
        print(f"ERROR loading .env: {e}")
        return {}

def test_groq(api_key):
    """Test Groq endpoint."""
    if not api_key:
        print("  ✗ GROQ_API_KEY not set in .env")
        return False
    
    try:
        url = "https://api.groq.com/openai/v1/models"
        req = urllib.request.Request(
            url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "User-Agent": "hermes-provider-verify/1.0"
            }
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
            models = [m.get("id", "?") for m in data.get("data", [])[:3]]
            print(f"  ✓ Groq OK (models: {', '.join(models)}...)")
            return True
    except urllib.error.HTTPError as e:
        if e.code == 401:
            print(f"  ✗ Groq 401 Unauthorized — check API key")
        else:
            print(f"  ✗ Groq HTTP {e.code}")
        return False
    except Exception as e:
        print(f"  ✗ Groq error: {e}")
        return False

def test_cerebras(api_key):
    """Test Cerebras endpoint."""
    if not api_key:
        print("  ✗ CEREBRAS_API_KEY not set in .env")
        return False
    
    try:
        url = "https://api.cerebras.ai/v1/models"
        req = urllib.request.Request(
            url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "User-Agent": "hermes-provider-verify/1.0"
            }
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
            models = [m.get("id", "?") for m in data.get("data", [])[:3]]
            print(f"  ✓ Cerebras OK (models: {', '.join(models)}...)")
            return True
    except urllib.error.HTTPError as e:
        if e.code == 401:
            print(f"  ✗ Cerebras 401 Unauthorized — check API key")
        else:
            print(f"  ✗ Cerebras HTTP {e.code}")
        return False
    except Exception as e:
        print(f"  ✗ Cerebras error: {e}")
        return False

def test_google_ai(api_key):
    """Test Google AI endpoint."""
    if not api_key:
        print("  ✗ GOOGLE_AI_KEY not set in .env")
        return False
    
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "hermes-provider-verify/1.0"}
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
            models = [m.get("name", "?") for m in data.get("models", [])[:3]]
            print(f"  ✓ Google AI OK (models: {', '.join(str(m).split('/')[-1] for m in models)}...)")
            return True
    except urllib.error.HTTPError as e:
        if e.code == 401 or e.code == 403:
            print(f"  ✗ Google AI {e.code} — check API key")
        else:
            print(f"  ✗ Google AI HTTP {e.code}")
        return False
    except Exception as e:
        print(f"  ✗ Google AI error: {e}")
        return False

if __name__ == "__main__":
    print("Verifying free LLM providers...\n")
    
    if not check_env_file():
        sys.exit(1)
    
    env = load_env()
    print(f"✓ Loaded .env ({len(env)} keys)\n")
    
    results = {
        "groq": test_groq(env.get("GROQ_API_KEY")),
        "cerebras": test_cerebras(env.get("CEREBRAS_API_KEY")),
        "google_ai": test_google_ai(env.get("GOOGLE_AI_KEY")),
    }
    
    print(f"\nSummary:")
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    print(f"  {passed}/{total} providers verified")
    
    if passed == 0:
        print("\nNo providers working. Check API keys in ~/.hermes/.env and provider dashboards.")
        sys.exit(1)
    elif passed < total:
        print(f"\n{total - passed} provider(s) failed. Check keys and endpoints above.")
    else:
        print("\nAll providers ready for integration!")
