import os
import sys
from tavily import TavilyClient

env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env")
if os.path.exists(env_path):
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ[k.strip()] = v.strip()

api_key = os.environ.get("TAVILY_API_KEY")
if not api_key:
    print("[-] Error: TAVILY_API_KEY is not set in environment or .env file.")
    sys.exit(1)

client = TavilyClient(api_key=api_key)

query = "FastAPI security advisory CVE Broken Object Level Authorization"
print(f"[+] Querying Tavily API for: '{query}'...")

try:
    response = client.search(
        query=query,
        search_depth="basic",
        max_results=3,
        include_answer=True
    )
    print("[+] Tavily API Connection Successful!")
    print(f"[+] Total results returned: {len(response.get('results', []))}")
    if response.get("answer"):
        print(f"[+] AI Summary Answer:\n    {response.get('answer')[:200]}...")
    for idx, r in enumerate(response.get("results", [])[:3], 1):
        print(f"\n--- Result #{idx} ---")
        print(f"Title: {r.get('title')}")
        print(f"URL: {r.get('url')}")
        print(f"Snippet: {r.get('content', '')[:120]}...")
except Exception as e:
    print(f"[-] Tavily API Query Failed: {e}")
    sys.exit(1)
