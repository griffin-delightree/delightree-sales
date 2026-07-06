#!/usr/bin/env python3
"""Launch the live FastAPI portal for the preview tool.

Runs the real app (auth, per-rep scoping, HubSpot) - NOT a static file server -
so login POSTs actually work. chdir to the project root first so .env / reps.json /
data/ resolve correctly regardless of where the launcher is invoked.
"""
import os
import sys

PROJ = os.path.dirname(os.path.abspath(__file__))
os.chdir(PROJ)
sys.path.insert(0, PROJ)

import uvicorn  # noqa: E402

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8123
    uvicorn.run("app.main:app", host="127.0.0.1", port=port, log_level="warning")
