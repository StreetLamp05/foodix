#!/usr/bin/env python3
"""
Standalone migration runner. Delegates to backend/app/db.run_migrations().
Can also be triggered automatically on backend startup with AUTO_MIGRATE=true.
"""

import sys
import os

# Allow importing from backend/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "backend", ".env"))

from app.db import run_migrations

if __name__ == "__main__":
    run_migrations()
