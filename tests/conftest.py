"""
Test configuration and fixtures
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def sample_document():
    """Sample document fixture"""
    return {
        "filename": "test.pdf",
        "content_type": "application/pdf",
    }
