"""
Campus2Career AI - Netlify Serverless Function Handler
Wraps the Flask app to run as a Netlify Function via serverless-wsgi.
The build script (build_netlify.py) copies all app source files here before deploy.
"""

import sys
import os

# This file lives in netlify/functions/
# After build, app.py, database.py, modules/, pages/, templates/ are all here too
FUNC_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, FUNC_DIR)

# Set NETLIFY env var so database.py uses /tmp path
os.environ["NETLIFY"] = "true"

import serverless_wsgi

# Import Flask app (app.py was copied here by build_netlify.py)
from app import app
from database import init_db, seed_demo_data

# Fix Flask template and static paths to point into the functions directory
app.template_folder = os.path.join(FUNC_DIR, "templates")
app.static_folder = os.path.join(FUNC_DIR, "static")

# Initialize and seed DB once per cold start
_initialized = False


def handler(event, context):
    global _initialized
    if not _initialized:
        try:
            init_db()
            seed_demo_data()
        except Exception as e:
            print(f"DB init warning: {e}")
        finally:
            _initialized = True

    return serverless_wsgi.handle_request(app, event, context)
