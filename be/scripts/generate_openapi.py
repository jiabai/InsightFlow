"""
Script to generate OpenAPI specification from FastAPI application.

This script exports the OpenAPI schema from the FastAPI app and saves it as a JSON file.
The generated specification can be used for API documentation and client generation.
"""

import json
import os
import sys

# Add the project root to the sys.path
script_dir = os.path.dirname(__file__)
project_root = os.path.abspath(os.path.join(script_dir, '..', '..'))
sys.path.insert(0, project_root)

from be.api_services.api_services_main import app

def generate_openapi_spec():
    """
    Generates the OpenAPI specification from the FastAPI app and saves it to a file.
    """
    openapi_schema = app.openapi()
    output_path = os.path.join(script_dir, "openapi.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(openapi_schema, f, ensure_ascii=False, indent=2)
    print(f"OpenAPI specification generated successfully at {output_path}")

if __name__ == "__main__":
    generate_openapi_spec()
