"""
Rate limiting configuration using slowapi.

Protects against brute force and DoS attacks without needing
external services like Azure API Management.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

# Create limiter instance
# Uses client IP address for rate limiting
limiter = Limiter(key_func=get_remote_address)

# Rate limit constants
RATE_LIMIT_DEFAULT = "100/minute"  # General API calls
RATE_LIMIT_AUTH = "5/minute"  # Login attempts (strict)
RATE_LIMIT_REGISTER = "3/hour"  # Registration (very strict)
RATE_LIMIT_INTELLIGENCE = "10/minute"  # AI calls (expensive)
