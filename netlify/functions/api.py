"""
Campus2Career AI - Netlify Serverless Function Handler
Wraps the Flask app to run as a Netlify Function via serverless-wsgi.
"""

import sys
import os

# Add parent directory to path so we can import app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set NETLIFY env var so database.py uses /tmp path
os.environ['NETLIFY'] = 'true'

import serverless_wsgi
from app import app
from database import init_db, seed_demo_data

# Initialize and seed DB once per cold start (copies DB to /tmp on Netlify)
_initialized = False

def handler(event, context):
    global _initialized
    if not _initialized:
        try:
            init_db()
            seed_demo_data()
            _initialized = True
        except Exception as e:
            print(f"DB init warning: {e}")
            _initialized = True  # Don't retry on every request

    return serverless_wsgi.handle_request(app, event, context)
