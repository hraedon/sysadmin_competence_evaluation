"""Shared test configuration."""
import os

# Disable rate limiting during tests
os.environ["RATE_LIMIT_ENABLED"] = "false"
