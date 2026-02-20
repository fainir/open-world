#!/usr/bin/env python3
"""Start the Open World Studio server."""
import os
import sys

# Ensure the project root is on the path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Load .env if present
from dotenv import load_dotenv
env_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(env_path):
    load_dotenv(env_path)

import uvicorn

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print(f"\n  Open World Studio")
    print(f"  http://localhost:{port}\n")
    uvicorn.run(
        "app.backend.main:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        reload_dirs=[os.path.join(project_root, "app")],
    )
