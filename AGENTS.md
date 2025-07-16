# Agent Instructions

When modifying code in this repository:

- Recreate the environment described in the `Dockerfile` (install the .NET runtime and ADOMD.NET library) so tests mimic the container as closely as possible.
- Always run `pytest -q` after changes.
- For every new or modified feature, add or update tests to cover the change.
- Attempt to build and run the Docker image to ensure the server starts:
  ```bash
  docker build -t powerbi-mcp .
  docker run --rm -e OPENAI_API_KEY=dummy powerbi-mcp timeout 5 python src/server.py
  ```
  It's OK if these commands fail in the sandbox, but make a best effort.
