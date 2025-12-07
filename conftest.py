"""Pytest configuration for project-level defaults."""

# Ignore manual integration test that requires a running A2A server.
collect_ignore = ["src/test_a2a_client.py", "src/test_openrouter_api.py"]
