import urllib.request
import json
import sys

try:
    print("Testing backend...")
    req = urllib.request.Request("http://localhost:8000/api/v1/academic/dashboard")
    with urllib.request.urlopen(req, timeout=5) as response:
        data = json.loads(response.read().decode())
        print("SUCCESS! KPIs count:", len(data.get('consolidated_kpis', [])))
except Exception as e:
    print("ERROR:", e)
