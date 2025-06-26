#!/usr/bin/env python3
"""
Main entry point for the DevopsFlow web server.

This script:
1. Builds the frontend if needed
2. Launches the Flask development server
"""

import argparse
import os
import sys
import webbrowser
import subprocess
import threading
import logging
from threading import Timer
from src.web.app import app

logging.basicConfig(level=logging.INFO)
logging.getLogger('flask').setLevel(logging.WARNING)
logging.getLogger('werkzeug').setLevel(logging.WARNING)

from dotenv import load_dotenv
load_dotenv(override=True)

# Set the script's directory as the current working directory
script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)

def start_mlflow_server():
    """Starts the MLflow server in a separate process."""
    try:
        print("Starting MLflow server on http://localhost:9500...")
        # Use Popen to run in the background. 
        # Redirect stdout and stderr to prevent cluttering the main app's console.
        # Ensure mlflow is in the PATH or provide the full path if necessary.
        print(f"Attempting to start MLflow server from CWD: {os.getcwd()}")
        print(f"Using Python interpreter: {sys.executable}")
        process = subprocess.Popen(
            [sys.executable, "-m", "mlflow", "server", "--host", "0.0.0.0", "--port", "9500"],
            # stdout and stderr will now go to the console
        )
        print(f"MLflow server process started with PID: {process.pid}")
    except FileNotFoundError:
        print("Error: 'mlflow' command not found. Make sure MLflow is installed and in your PATH.")
    except Exception as e:
        print(f"An error occurred while starting MLflow server: {e}")

def main():
    """Launch the DevopsFlow web server with command line options."""
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Run the DevopsFlow web server.")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=4500, help="Port to listen on")
    parser.add_argument("--no-debug", action="store_false", dest="debug", 
                       help="Disable debug mode")
    parser.add_argument("--no-browser", action="store_false", dest="open_browser",
                       help="Don't open browser automatically")
    args = parser.parse_args()

    # Start MLflow server in a separate thread
    mlflow_thread = threading.Thread(target=start_mlflow_server, daemon=True)
    mlflow_thread.start()

    # Open browser if requested
    if args.open_browser:
        url = f"http://{args.host}:{args.port}"
        Timer(1, lambda: webbrowser.open_new(url)).start()
    
    # Run the server
    print(f"Starting server on http://{args.host}:{args.port}")
    print("Press Ctrl+C to stop")
    app.run(host=args.host, port=args.port, debug=args.debug, use_reloader=False)


if __name__ == "__main__":
    main()
