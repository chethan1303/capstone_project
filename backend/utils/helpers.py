"""
PI-EWS Utility Helpers.
"""

import uuid


def generate_session_id() -> str:
    """Generate a unique session identifier."""
    return str(uuid.uuid4())
