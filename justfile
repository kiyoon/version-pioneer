set windows-shell := ["pwsh", "-NoProfile", "-Command"]

# Ensure recipes run from repo root
root := justfile_directory()

# Format repo
format:
    cd "{{root}}" && ruff format .
    cd "{{root}}" && ruff check . --select I --fix
    cd "{{root}}" && prettier --write ".github/**/*.{yml,yaml}"
