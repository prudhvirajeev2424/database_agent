# Test/experimentation script
# four backticks
import os, requests
endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "").rstrip("/")
url = f"{endpoint}/openai/deployments?api-version=2023-05-15"
r = requests.get(url, headers={"api-key": os.getenv("AZURE_OPENAI_API_KEY")})
print(r.status_code)
print(r.text)
# four backticks