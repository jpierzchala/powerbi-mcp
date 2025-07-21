"""
Tests for Docker-related functionality and configuration.
"""

import os

import pytest


@pytest.mark.unit
class TestDockerConfiguration:
    """Test Docker configuration and security measures."""

    def test_dockerignore_exists(self):
        """Test that .dockerignore file exists in the repository."""
        dockerignore_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".dockerignore")
        assert os.path.exists(dockerignore_path), ".dockerignore file should exist"

    def test_dockerignore_excludes_env_files(self):
        """Test that .dockerignore excludes environment files."""
        dockerignore_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".dockerignore")

        with open(dockerignore_path, "r") as f:
            content = f.read()

        # Check that various env file patterns are excluded
        expected_patterns = [".env", ".env.local", "*.env"]
        for pattern in expected_patterns:
            assert pattern in content, f"Pattern '{pattern}' should be in .dockerignore"

    def test_dockerignore_excludes_sensitive_files(self):
        """Test that .dockerignore excludes other sensitive and unnecessary files."""
        dockerignore_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".dockerignore")

        with open(dockerignore_path, "r") as f:
            content = f.read()

        # Check that other sensitive patterns are excluded
        sensitive_patterns = [".git", "tests/", "__pycache__/", ".vscode/", ".idea/"]
        for pattern in sensitive_patterns:
            assert pattern in content, f"Sensitive pattern '{pattern}' should be in .dockerignore"

    def test_env_example_not_excluded(self):
        """Test that .env.example is not excluded from Docker builds."""
        dockerignore_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".dockerignore")

        with open(dockerignore_path, "r") as f:
            content = f.read()

        # .env.example should not be explicitly excluded as it's a template file
        lines = [line.strip() for line in content.split("\n") if line.strip() and not line.startswith("#")]
        assert ".env.example" not in lines, ".env.example should not be excluded from Docker builds"

    def test_gitignore_still_excludes_env(self):
        """Test that .gitignore still excludes .env files (for local development)."""
        gitignore_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".gitignore")

        with open(gitignore_path, "r") as f:
            content = f.read()

        # Ensure .env is still in .gitignore for local development
        assert ".env" in content, ".env should still be in .gitignore for local development"
