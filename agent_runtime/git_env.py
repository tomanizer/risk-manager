from __future__ import annotations

import os
from typing import Mapping


# Matches `git rev-parse --local-env-vars` so nested git calls honor their cwd.
LOCAL_GIT_ENV_VARS = (
    "GIT_ALTERNATE_OBJECT_DIRECTORIES",
    "GIT_CONFIG",
    "GIT_CONFIG_PARAMETERS",
    "GIT_CONFIG_COUNT",
    "GIT_OBJECT_DIRECTORY",
    "GIT_DIR",
    "GIT_WORK_TREE",
    "GIT_IMPLICIT_WORK_TREE",
    "GIT_GRAFT_FILE",
    "GIT_INDEX_FILE",
    "GIT_NO_REPLACE_OBJECTS",
    "GIT_REPLACE_REF_BASE",
    "GIT_PREFIX",
    "GIT_SHALLOW_FILE",
    "GIT_COMMON_DIR",
)


def scrub_git_local_env(env: Mapping[str, str] | None = None) -> dict[str, str]:
    sanitized = dict(os.environ if env is None else env)
    for name in LOCAL_GIT_ENV_VARS:
        sanitized.pop(name, None)
    return sanitized
