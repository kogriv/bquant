#!/usr/bin/env bash
# Cloud Claude Code (claude.ai/code) environment bootstrap for bquant.
#
# Runs at SessionStart in the ephemeral cloud sandbox to provision a working
# runtime (Python 3.12 venv + locked dependencies) so tests/linters are ready
# immediately. Local sessions are left untouched.
#
# Rationale (verified live in a cloud session, 2026-07-04):
#   - The sandbox proxy blocks github.com, so `uv python install` (which pulls
#     python-build-standalone from GitHub Releases) fails. The image already
#     ships /usr/bin/python3.12, so we use that interpreter directly.
#   - Installing a fresh resolve drifts dependency versions and breaks tests
#     (590 passed / 47 failed vs 646 / 4 with the lockfile). So we sync EXACTLY
#     from uv.lock.
set -euo pipefail

# Provision only in the cloud sandbox; skip on developer machines.
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

cd "${CLAUDE_PROJECT_DIR:-.}"

# Idempotent: a resumed session reuses the venv a prior start already built.
if [ -x .venv/bin/python ]; then
  exit 0
fi

# Pre-installed system interpreter (default `python` is 3.11 in the sandbox).
PY312="$(command -v python3.12 || echo /usr/bin/python3.12)"

# Reproducible install: venv on 3.12, dependencies + dev/research extras straight
# from uv.lock (dev extra = pytest/linters; research extra = TS method stack:
# tslearn/pyts/pycatch22, see research/methodology/method_tool_stack.md).
uv sync --python "$PY312" --extra dev --extra research

exit 0
