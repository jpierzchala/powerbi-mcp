# Agent Instructions

When modifying code in this repository:

- Recreate the environment described in the `Dockerfile` (install the .NET runtime and ADOMD.NET library) so tests mimic the container as closely as possible.
- Always run `pytest -q` after changes.
- For every new or modified feature, add or update tests to cover the change.
