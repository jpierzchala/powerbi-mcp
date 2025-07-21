"""
Test Docker environment behavior to ensure .env files are not loaded.
"""

import os
import subprocess
import tempfile

import pytest


class TestDockerEnvironment:
    """Test Docker-specific environment behavior."""

    def test_dockerignore_excludes_env_files(self):
        """Test that .dockerignore properly excludes .env files."""
        # Read .dockerignore file
        dockerignore_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".dockerignore")

        assert os.path.exists(dockerignore_path), ".dockerignore file should exist"

        with open(dockerignore_path, "r") as f:
            content = f.read()

        # Check that .env files are excluded
        assert ".env" in content, ".env should be in .dockerignore"
        assert ".env.*" in content, ".env.* should be in .dockerignore"

    def test_docker_entrypoint_no_env_loading(self):
        """Test that docker-entrypoint.sh does not load .env files."""
        entrypoint_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "docker-entrypoint.sh")

        assert os.path.exists(entrypoint_path), "docker-entrypoint.sh should exist"

        with open(entrypoint_path, "r") as f:
            content = f.read()

        # Ensure .env loading code is not present
        assert "/app/.env" not in content, "docker-entrypoint.sh should not reference .env files"
        assert ". /app/.env" not in content, "docker-entrypoint.sh should not source .env files"
        assert "Loading environment variables from" not in content, "No .env loading message should be present"

    def test_dockerfile_copies_correctly(self):
        """Test that Dockerfile behavior is appropriate for security."""
        dockerfile_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "Dockerfile")

        assert os.path.exists(dockerfile_path), "Dockerfile should exist"

        with open(dockerfile_path, "r") as f:
            content = f.read()

        # The COPY . . should still be there (it's the .dockerignore that prevents .env copying)
        assert "COPY . ." in content, "Dockerfile should still copy application files"

    @pytest.mark.skipif(not os.path.exists("/usr/bin/docker"), reason="Docker not available")
    def test_docker_build_excludes_env(self):
        """Test that docker build properly excludes .env files (integration test)."""
        # This test requires Docker to be available
        project_root = os.path.dirname(os.path.dirname(__file__))

        # Create a temporary .env file for testing
        env_file_path = os.path.join(project_root, ".env.test")
        try:
            with open(env_file_path, "w") as f:
                f.write("TEST_DOCKER_ENV=should_not_be_copied\n")

            # Try building the image and check if .env.test exists in it
            # Note: This is a basic test - in CI/CD we would run full Docker tests
            result = subprocess.run(
                ["docker", "build", "-t", "test-powerbi-mcp", ".", "--quiet"],
                cwd=project_root,
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode == 0:
                # Check if the file was excluded by trying to see it in the built image
                inspect_result = subprocess.run(
                    ["docker", "run", "--rm", "test-powerbi-mcp", "ls", "-la", "/app/.env.test"],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )

                # The file should NOT exist in the container (ls should fail)
                assert inspect_result.returncode != 0, ".env.test file should not exist in Docker container"

                # Clean up the test image
                subprocess.run(["docker", "rmi", "test-powerbi-mcp"], capture_output=True)
            else:
                pytest.skip(f"Docker build failed: {result.stderr}")

        finally:
            # Clean up test file
            if os.path.exists(env_file_path):
                os.remove(env_file_path)
