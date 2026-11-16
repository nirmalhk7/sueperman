# Optional hash-verified build inputs

The normal build uses `uv sync`. In environments where the container lacks the
host's trusted network route, run `scripts/prepare_container_wheels.py` on the
host with its existing verified TLS setup, then set `CONTAINER_OFFLINE_WHEELS=1`.
Only lockfile-hashed wheels and exported requirements are used. Docker's install
step has no network access in this mode. Generated files are ignored by Git;
never put certificates, tokens, environment files or credentials here.
