"""
Test that Docker environment doesn't load .env files.
Ensures Docker containers follow security best practices.
"""

import os
import subprocess
import tempfile
from pathlib import Path

import pytest


@pytest.mark.unit
class TestDockerEnvironment:
    """Test Docker environment variable handling."""

    def test_docker_entrypoint_does_not_load_env_file(self):
        """Test that docker-entrypoint.sh does not load .env files."""
        # Get the docker-entrypoint.sh script path
        repo_root = Path(__file__).parent.parent
        entrypoint_script = repo_root / "docker-entrypoint.sh"

        assert entrypoint_script.exists(), "docker-entrypoint.sh not found"

        # Read the script content
        with open(entrypoint_script, "r") as f:
            script_content = f.read()

        # Verify that the script does NOT contain .env loading logic
        assert "/app/.env" not in script_content, "docker-entrypoint.sh should not reference .env files"
        assert "Loading environment variables from" not in script_content, "Script should not load .env files"
        assert ". /app/.env" not in script_content, "Script should not source .env files"

    def test_docker_entrypoint_script_functionality(self):
        """Test that docker-entrypoint.sh works correctly without .env loading."""
        repo_root = Path(__file__).parent.parent
        entrypoint_script = repo_root / "docker-entrypoint.sh"

        # Create a temporary .env file to ensure it's ignored
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_env = Path(temp_dir) / ".env"
            with open(temp_env, "w") as f:
                f.write("TEST_DOCKER_VAR=should_not_be_loaded\n")

            # Run the entrypoint script with a simple echo command
            # Change to temp directory to simulate container environment
            result = subprocess.run(
                ["bash", str(entrypoint_script), "echo", "test_passed"],
                cwd=temp_dir,
                capture_output=True,
                text=True,
                env={**os.environ, "PATH": os.environ.get("PATH", "")},
            )

            assert result.returncode == 0, f"Entrypoint script failed: {result.stderr}"
            assert "test_passed" in result.stdout, "Entrypoint script should execute the command"

            # Verify that the environment variable from .env was NOT loaded
            # Run a command that would show the env var if it was loaded
            result2 = subprocess.run(
                ["bash", str(entrypoint_script), "printenv"],
                cwd=temp_dir,
                capture_output=True,
                text=True,
                env={**os.environ, "PATH": os.environ.get("PATH", "")},
            )

            assert result2.returncode == 0, f"Entrypoint printenv failed: {result2.stderr}"
            assert "TEST_DOCKER_VAR" not in result2.stdout, ".env variables should not be loaded in Docker context"

    def test_dockerfile_copies_correctly(self):
        """Verify Dockerfile doesn't explicitly copy .env files."""
        repo_root = Path(__file__).parent.parent
        dockerfile = repo_root / "Dockerfile"

        assert dockerfile.exists(), "Dockerfile not found"

        with open(dockerfile, "r") as f:
            dockerfile_content = f.read()

        # Should not explicitly copy .env files
        assert "COPY .env" not in dockerfile_content, "Dockerfile should not explicitly copy .env files"
        assert "ADD .env" not in dockerfile_content, "Dockerfile should not explicitly add .env files"

        # It's OK to have "COPY . ." as long as .gitignore excludes .env
        # and the entrypoint doesn't load it
