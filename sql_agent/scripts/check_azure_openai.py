# Verify Azure OpenAI connection
"""Diagnostics for Azure OpenAI configuration.

Checks:
- Sanitizes endpoint and API key.
- Tries the configured API version and a few fallbacks to list deployments.
- Reports whether the configured deployment name exists.

Run:
    python scripts/check_azure_openai.py
"""
import os
import sys
import json
import textwrap
from dotenv import load_dotenv

import requests

load_dotenv()

AZ_ENDPOINT = (os.getenv("AZURE_OPENAI_ENDPOINT") or "").strip()
AZ_KEY = (os.getenv("AZURE_OPENAI_API_KEY") or "").strip()
AZ_DEPLOYMENT = (os.getenv("AZURE_OPENAI_DEPLOYMENT") or "").strip()
AZ_API_VERSION = (os.getenv("AZURE_OPENAI_API_VERSION") or "").strip()

if not AZ_ENDPOINT:
    print("ERROR: AZURE_OPENAI_ENDPOINT is empty in your .env")
    sys.exit(2)

if not AZ_KEY:
    print("ERROR: AZURE_OPENAI_API_KEY is empty in your .env")
    sys.exit(2)

endpoint = AZ_ENDPOINT.rstrip("/")

print("Endpoint:", endpoint)
print("Deployment (expected):", AZ_DEPLOYMENT)
print("Configured api-version:", AZ_API_VERSION or "(none)")

# Candidate API versions to try (configured first, then fallbacks)
candidates = []
if AZ_API_VERSION:
    candidates.append(AZ_API_VERSION)
candidates.extend(["2025-04-01-preview", "2024-12-01-preview", "2023-05-15"])

headers = {"api-key": AZ_KEY}

found = False

for api_ver in candidates:
    url = f"{endpoint}/openai/deployments?api-version={api_ver}"
    print("\nTrying:", url)
    try:
        r = requests.get(url, headers=headers, timeout=10)
    except Exception as e:
        print("Request failed:", e)
        continue

    print("Status code:", r.status_code)
    text = r.text
    # Truncate long responses for readability
    print("Response (truncated):", textwrap.shorten(text, width=1000, placeholder="..."))

    if r.status_code == 200:
        try:
            data = r.json()
        except Exception as e:
            print("Failed to parse JSON response:", e)
            continue

        # Azure may return a list or an object; attempt to search anywhere for deployment id/name
        s = json.dumps(data)
        if AZ_DEPLOYMENT and AZ_DEPLOYMENT in s:
            print("OK: Found deployment name in response for api-version", api_ver)
            found = True
            break
        else:
            print("Note: deployment name not found in response for api-version", api_ver)
            # Also pretty-print keys to help debugging
            if isinstance(data, dict):
                print("Top-level keys:", list(data.keys()))
            continue

    # Helpful hints for common errors
    if r.status_code == 404:
        print("404 Not Found: The resource path was not found. Ensure endpoint is correct and includes your resource name.")
    elif r.status_code >= 500:
        print("Server error from Azure (5xx). This may be transient; try again later or contact Azure support.")
    elif r.status_code == 401 or r.status_code == 403:
        print("Authentication/authorization error (401/403). Check your API key and that it has appropriate access.")

if not found:
    print("\nRESULT: deployment not confirmed. If you expect the deployment to exist, verify in Azure Portal -> OpenAI -> Deployments.")
    print("You can also run a curl equivalent shown below to reproduce the request:")
    print(f"curl -s -X GET \"{endpoint}/openai/deployments?api-version=2023-05-15\" -H \"api-key: <your key>\"")
    sys.exit(1)

print("\nAll checks passed: deployment found.")
sys.exit(0)
