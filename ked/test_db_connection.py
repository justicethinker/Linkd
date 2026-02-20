#!/usr/bin/env python3
"""Quick test of PostgreSQL connection."""

import sys
import os

# Add the current directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from src.config import settings
    from src.db import engine
    
    print("Configuration loaded successfully!")
    print(f"Database URL: {settings.database_url}")
    
    # Try to connect
    with engine.connect() as conn:
        result = conn.execute("SELECT 1 as test")
        print("✓ Database connection successful!")
        print(f"✓ Connection test result: {result.fetchone()[0]}")
    
    print("\n✅ PostgreSQL is ready for initialization!")
    
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)
