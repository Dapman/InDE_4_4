#!/usr/bin/env python3
"""
InDE MVP v3.7.4 - Application Entry Point
"Integration, Polish & Gradio Retirement"

This script starts the InDE FastAPI server.

Note: As of v3.7.4.4, the Gradio UI has been retired in favor of the
React 18 frontend. For development, run the React dev server separately:
    cd frontend && npm run dev

Usage:
    python run_inde.py                    # Start FastAPI server
    python run_inde.py --port 8000        # Specify port
    python run_inde.py --demo             # Demo mode with in-memory DB

Production:
    The FastAPI server serves the React build from frontend/dist/
    when running in production mode.
"""

import argparse
import os
import sys

from core.config import VERSION, VERSION_NAME


def start_fastapi_server(host: str = "0.0.0.0", port: int = 8000, demo: bool = False):
    """Start the FastAPI server."""
    import uvicorn

    if demo:
        os.environ["USE_MONGOMOCK"] = "true"
        print("Demo mode enabled (in-memory database)")

    print(f"\n=== InDE v{VERSION} - {VERSION_NAME} ===")
    print(f"Starting FastAPI server on http://{host}:{port}")
    print(f"API Documentation: http://{host}:{port}/docs")
    print(f"\nReact Frontend:")
    print(f"  Development: cd frontend && npm run dev (port 5173)")
    print(f"  Production:  Served from /frontend/dist/ via FastAPI")
    print("\nPress Ctrl+C to stop the server.\n")

    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=True,
        log_level="info"
    )


def main():
    parser = argparse.ArgumentParser(
        description=f"InDE v{VERSION} - {VERSION_NAME}"
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host to bind to"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind to"
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run in demo mode with in-memory database"
    )

    args = parser.parse_args()
    start_fastapi_server(args.host, args.port, args.demo)


if __name__ == "__main__":
    main()
