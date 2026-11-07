"""Route hygiene tests — ensure no route collisions or shadowed endpoints."""

from collections import Counter
import pytest
from app.main import app


def test_no_duplicate_routes():
    """Verify that no HTTP method and path combination is registered more than once."""
    collisions = []
    seen = Counter((m, r.path) for r in app.routes if getattr(r, "methods", None) for m in r.methods)
    for (method, path), count in seen.items():
        if count > 1:
            collisions.append(f"{method} {path} (registered {count} times)")
    assert not collisions, f"Duplicate routes found: {collisions}"
