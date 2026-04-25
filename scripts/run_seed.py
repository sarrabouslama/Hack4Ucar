#!/usr/bin/env python
"""
Quick seed script runner
Run from project root: python -m scripts.seed_db
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.seed_db import seed_all

if __name__ == "__main__":
    seed_all()
