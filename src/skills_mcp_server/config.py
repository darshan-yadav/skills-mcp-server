"""Configuration loading for skills-mcp-server.

Implements the YAML config schema described in SPEC §7 (Storage) and
SPEC §13.2 (First-run config). v0.1 scope: ``local`` and ``git`` sources,
``data_dir``, ``log_level``, and a scheduled-pull cadence knob
(``refresh_interval_seconds``, SPEC §7.2).

Public surface:

* :class:`Config` — top-level pydantic model.
* :class:`SourceConfig` — tagged union of :class:`LocalSourceConfig` and
  :class:`GitSourceConfig`, discriminated by the ``type`` field.
* :class:`ConfigError` — raised for any load/parse/validation failure; the
  message is intended to be user-facing (printed by the CLI).
* :func:`load_config` — open a YAML file, substitute ``${VAR}`` /
  ``${VAR:-default}`` references from the process environment, parse,
  validate, and return a :class:`Config`.

v0.1 deliberately omits fields that land in later phases (execution,
webhook, mcp_admin_tools — all specified in SPEC §16).
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Annotated, Any, Literal, Union

import yaml
from pydantic import (
    BaseModel,
    ConfigDict,
    Discriminator,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)

__all__ = [
    "Config",
    "SourceConfig",
    "LocalSourceConfig",
    "GitSourceConfig",
    "ConfigError",
    "load_config",
]


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class ConfigError(Exception):
    """Raised for any failure loading, parsing, or validating the config.

    The message is user-facing — ``load_config`` callers (CLI, server
    bootstrap) should surface it verbatim without adding their own
    framing. Error messages always include the offending config path
    when one is available so operators can find the file.
    """


# ---------------------------------------------------------------------------
# Source schemas
# ---------------------------------------------------------------------------


class _SourceBase(BaseModel):
    """Shared base for all source configs.

    ``model_config`` is set to forbid unknown keys — we want typos in
    source stanzas to surface as validation errors rather than silently
    ignored fields. Later phases that add new keys update the schema
    explicitly.
    """

    model_config = ConfigDict(extra="forbid")

    name: str = Field(
        min_length=1,
        description="Stable identifier for this source; must be unique across the config.",
    )


class LocalSourceConfig(_SourceBase):
    """A source that loads skills from a local filesystem directory.

    The ``path`` is expanded (``~``), normalised via ``os.path.realpath``
    to follow symlinks to their target, and required to exist as a
    directory at load time. This fail-fast check matches SPEC §10's
    symlink-resolution guarantee: by the time a ``LocalSourceConfig``
    exists, its ``path`` is the real, canonical on-disk location.
    """

    type: Literal["local"]
    path: Path = Field(description="Absolute path to a directory of skill bundles.")

    @field_validator("path", mode="before")
    @classmethod
    def _resolve_and_check_path(cls, value: Any) -> Path:
        if value is None:
            raise ValueError("path is required")
        # Accept str or Path; expand ~, then realpath-resolve.
        raw = Path(str(value)).expanduser()
        resolved = Path(os.path.realpath(raw))
        if not resolved.exists():
            raise ValueError(f"path does not exist: {resolved}")
        if not resolved.is_dir():
            raise ValueError(f"path is not a directory: {resolved}")
        return resolved


class GitSourceConfig(_SourceBase):
    """A source that clones a remote git repository and scans it.

    Clone/pull behaviour lives in ``sources/git.py`` (not this module);
    here we only capture the declarative fields the operator writes in
    their YAML. SPEC §3.4 and §7.1 call out pinning ``ref`` to a tag or
    commit SHA as the recommended production posture — ``main`` is the
    convenience default, not the recommendation.
    """

    type: Literal["git"]
    url: str = Field(min_length=1, description="Git remote URL (https or ssh).")
    ref: str = Field(
        default="main",
        min_length=1,
        description="Branch, tag, or commit SHA to check out.",
    )
    subpath: str | None = Field(
        default=None,
        description="Optional sub-directory within the repo to scan for skills.",
    )


SourceConfig = Annotated[
    Union[LocalSourceConfig, GitSourceConfig],
    Discriminator("type"),
]


# ---------------------------------------------------------------------------
# Top-level config
# ---------------------------------------------------------------------------


class Config(BaseModel):
    """Top-level server configuration.

    Corresponds to the YAML shape in SPEC §13.2:

    .. code-block:: yaml

        sources:
          - name: local
            type: local
            path: /skills
        data_dir: /data
        log_level: info

    Phase 2+ fields (``execution``, ``webhook``, ``mcp_admin_tools``) are
    intentionally absent; they will be added in later revisions of this
    schema when those features land.
    """

    model_config = ConfigDict(extra="forbid")

    sources: list[SourceConfig] = Field(
        min_length=1,
        description="One or more skill sources. At least one is required.",
    )
    data_dir: Path = Field(
        default=Path("/data"),
        description="Writable directory for git caches, lock files, audit log.",
    )
    log_level: Literal["debug", "info", "warning", "error"] = Field(
        default="info",
        description="Server log verbosity.",
    )
    refresh_interval_seconds: int = Field(
        default=300,
        ge=0,
        description=(
            "Cadence of the scheduled-pull loop (SPEC §7.2). 0 disables "
            "periodic refresh — sources only reload on explicit CLI reload."
        ),
    )

    @model_validator(mode="after")
    def _unique_source_names(self) -> Config:
        seen: set[str] = set()
        duplicates: list[str] = []
        for source in self.sources:
            if source.name in seen and source.name not in duplicates:
                duplicates.append(source.name)
            seen.add(source.name)
        if duplicates:
            raise ValueError(
                "duplicate source name(s): " + ", ".join(sorted(duplicates))
            )
        return self


# ---------------------------------------------------------------------------
# Env-var substitution
# ---------------------------------------------------------------------------

# Matches ${VAR} and ${VAR:-default}.
#   group 1: variable name (required; ASCII identifier chars)
#   group 2: optional ":-default" marker
#   group 3: default value (may be empty string, may not contain '}')
_ENV_VAR_RE = re.compile(
    r"\$\{([A-Za-z_][A-Za-z0-9_]*)(:-([^}]*))?\}"
)


def _substitute_env_vars(text: str, path: Path) -> str:
    """Expand ``${VAR}`` / ``${VAR:-default}`` references in *text*.

    More complex shell expansions (``${VAR:?msg}``, ``${VAR:+alt}``,
    command substitution, arithmetic, etc.) are deliberately not
    supported — operators who need that power should template the config
    themselves before feeding it to the server. A missing variable with
    no default raises :class:`ConfigError` referencing the file path so
    the operator knows which config had the unresolved reference.
    """

    missing: list[str] = []

    def _replace(match: re.Match[str]) -> str:
        var_name = match.group(1)
        has_default = match.group(2) is not None
        default_value = match.group(3) if has_default else None

        if var_name in os.environ:
            return os.environ[var_name]
        if has_default:
            # group(3) is "" for `${VAR:-}` — treat that as empty string.
            return default_value or ""
        missing.append(var_name)
        return match.group(0)

    substituted = _ENV_VAR_RE.sub(_replace, text)

    if missing:
        unique = sorted(set(missing))
        raise ConfigError(
            f"config {path}: environment variable(s) not set and no default "
            f"provided: {', '.join(unique)}. Use ${{VAR:-default}} if the "
            f"variable is optional."
        )

    return substituted


# ---------------------------------------------------------------------------
# Validation-error flattening
# ---------------------------------------------------------------------------


def _flatten_validation_error(exc: ValidationError, path: Path) -> str:
    """Render a pydantic ValidationError as one error per line.

    Produces output like::

        config /path/to/config.yaml: 2 validation error(s):
          - sources.0.type: Input tag 'bogus' found using 'type' does not match...
          - sources.1.path: path does not exist: /missing

    The leading header includes the config path so operators can find
    the file. Each bullet includes the dotted field path (``sources.0.type``)
    and the message pydantic produced, stripped of any trailing context
    noise that isn't useful at CLI-printing time.
    """

    lines: list[str] = []
    for err in exc.errors():
        loc = ".".join(str(part) for part in err.get("loc", ())) or "<root>"
        msg = err.get("msg", "invalid value")
        lines.append(f"  - {loc}: {msg}")

    count = len(lines)
    header = f"config {path}: {count} validation error{'s' if count != 1 else ''}:"
    return "\n".join([header, *lines])


# ---------------------------------------------------------------------------
# Public loader
# ---------------------------------------------------------------------------


def load_config(path: Path | str) -> Config:
    """Load, env-expand, parse, and validate a YAML config file.

    Args:
        path: Filesystem path to the YAML config (typically
            ``/config/config.yaml`` inside the server container, or a
            local path during development).

    Returns:
        A fully-validated :class:`Config`.

    Raises:
        ConfigError: The file could not be opened, the YAML was
            malformed, an ``${ENV_VAR}`` reference was unresolved, or
            the parsed document failed schema validation. The exception
            message is intended to be printed verbatim.
    """

    config_path = Path(path)

    # 1. Read raw text.
    try:
        raw_text = config_path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ConfigError(f"config file not found: {config_path}") from exc
    except OSError as exc:
        raise ConfigError(
            f"could not read config file {config_path}: {exc}"
        ) from exc

    # 2. Env-var substitution on the raw text, pre-YAML.
    substituted = _substitute_env_vars(raw_text, config_path)

    # 3. Parse YAML.
    try:
        data = yaml.safe_load(substituted)
    except yaml.YAMLError as exc:
        raise ConfigError(
            f"config {config_path}: YAML parse error: {exc}"
        ) from exc

    if data is None:
        raise ConfigError(
            f"config {config_path}: file is empty; expected a YAML mapping"
        )
    if not isinstance(data, dict):
        raise ConfigError(
            f"config {config_path}: top-level YAML value must be a mapping, "
            f"got {type(data).__name__}"
        )

    # 4. Validate with pydantic.
    try:
        return Config.model_validate(data)
    except ValidationError as exc:
        raise ConfigError(_flatten_validation_error(exc, config_path)) from exc
