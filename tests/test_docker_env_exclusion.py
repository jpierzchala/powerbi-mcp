"""Test that .env files are properly excluded from Docker builds."""

import os
import subprocess
import tempfile
import unittest
from pathlib import Path


class TestDockerEnvExclusion(unittest.TestCase):
    """Test Docker build excludes .env files."""

    def test_dockerignore_excludes_env_files(self):
        """Test that .dockerignore properly excludes .env files."""
        # Get the repository root
        repo_root = Path(__file__).parent.parent
        dockerignore_path = repo_root / ".dockerignore"

        # Verify .dockerignore exists
        self.assertTrue(dockerignore_path.exists(), ".dockerignore file should exist")

        # Read .dockerignore content
        dockerignore_content = dockerignore_path.read_text()

        # Verify .env patterns are included
        env_patterns = [".env", "*.env", ".env.local", ".env.*.local"]
        for pattern in env_patterns:
            self.assertIn(pattern, dockerignore_content, f"Pattern '{pattern}' should be in .dockerignore")

    def test_dockerignore_format(self):
        """Test that .dockerignore is properly formatted."""
        repo_root = Path(__file__).parent.parent
        dockerignore_path = repo_root / ".dockerignore"

        dockerignore_content = dockerignore_path.read_text()

        # Should not be empty
        self.assertTrue(len(dockerignore_content.strip()) > 0, ".dockerignore should not be empty")

        # Should include comments explaining the env exclusion
        self.assertIn(
            "Environment files", dockerignore_content, ".dockerignore should document environment file exclusion"
        )


if __name__ == "__main__":
    unittest.main()
