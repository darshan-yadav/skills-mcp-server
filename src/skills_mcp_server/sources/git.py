"""Git source implementation.

Fetches skill bundles from a remote git repository, securely caching them
locally. Uses OS-level file locking (`fcntl.flock`) to prevent cache
contention when multiple server instances bootstrap simultaneously.
"""

from __future__ import annotations

import dataclasses
import fcntl
import logging
import os
import stat
import subprocess
import time
from collections.abc import Iterator
from pathlib import Path

from skills_mcp_server.models import SkillBundle
from skills_mcp_server.sources.base import SourceError
from skills_mcp_server.sources.local import LocalSource

logger = logging.getLogger(__name__)


class GitSource:
    """Load skill bundles from a remote git repository.

    Maintains a local clone at `data_dir/skills/<name>` and synchronizes
    it via an exclusive lock at `data_dir/locks/<name>.lock`.
    """

    def __init__(
        self,
        name: str,
        url: str,
        ref: str,
        data_dir: Path,
        subpath: str | None = None,
    ) -> None:
        self.name = name
        self.url = url
        self.ref = ref
        self.subpath = subpath

        data_dir_real = Path(os.path.realpath(Path(data_dir).expanduser()))
        if not data_dir_real.exists():
            raise SourceError(f"git source {name!r}: data_dir does not exist: {data_dir_real}")
        if not data_dir_real.is_dir():
            raise SourceError(f"git source {name!r}: data_dir is not a directory: {data_dir_real}")

        self.cache_dir = data_dir_real / "skills" / name
        self.lock_file = data_dir_real / "locks" / f"{name}.lock"

        self.cache_dir.parent.mkdir(parents=True, exist_ok=True)
        self.lock_file.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> Iterator[SkillBundle]:
        """Fetch/update the git repo and yield its skill bundles.

        Acquires an exclusive flock(2) lock with a 30-second timeout.
        If the lock is acquired, performs git fetch/clone.
        If the lock times out, proceeds with the existing cache (if any).
        """
        self._sync()

        # Resolve the effective root to scan
        scan_root = self.cache_dir
        if self.subpath:
            # Prevent subpath traversal outside the cache_dir
            scan_root = Path(os.path.realpath(scan_root / self.subpath))
            if not str(scan_root).startswith(str(self.cache_dir) + os.sep) and str(scan_root) != str(self.cache_dir):
                raise SourceError(f"git source {self.name!r}: subpath {self.subpath!r} escapes repo root")

        if not scan_root.exists() or not scan_root.is_dir():
            logger.warning("source %r: scan root %s is missing or not a directory", self.name, scan_root)
            return

        commit_sha = self._get_commit_sha()

        # Delegate the actual directory walk to LocalSource
        local_source = LocalSource(name=self.name, root=scan_root)

        for bundle in local_source.load():
            yield dataclasses.replace(bundle, commit_sha=commit_sha)

    def _sync(self) -> None:
        """Synchronize the local git clone using an exclusive file lock."""
        fd = os.open(self.lock_file, os.O_RDWR | os.O_CREAT, 0o600)
        acquired = False
        start_time = time.monotonic()
        timeout = 30.0

        try:
            while True:
                try:
                    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    acquired = True
                    break
                except BlockingIOError:
                    if time.monotonic() - start_time > timeout:
                        break
                    time.sleep(0.5)

            if not acquired:
                if not (self.cache_dir / ".git").exists():
                    raise SourceError(
                        f"git source {self.name!r}: lock acquisition timed out after {timeout}s "
                        "and cache is empty. Cannot start."
                    )
                logger.warning(
                    "git source %r: lock acquisition timed out after %ss. Skipping fetch and using existing cache.",
                    self.name,
                    timeout,
                )
                return

            self._set_cache_permissions(writable=True)
            self._do_git_pull()
            self._set_cache_permissions(writable=False)

        finally:
            if acquired:
                fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)

    def _do_git_pull(self) -> None:
        """Perform the actual clone or fetch+checkout."""
        if (self.cache_dir / ".git").exists():
            logger.debug("git source %r: fetching %s from %s", self.name, self.ref, self.url)
            self._run_git(["fetch", "origin", self.ref], cwd=self.cache_dir)
            self._run_git(["checkout", "--force", "FETCH_HEAD"], cwd=self.cache_dir)
            self._run_git(["clean", "-fdx"], cwd=self.cache_dir)
        else:
            logger.debug("git source %r: cloning %s", self.name, self.url)
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            self._run_git(["clone", "--no-checkout", self.url, str(self.cache_dir)])
            self._run_git(["checkout", "--force", self.ref], cwd=self.cache_dir)

    def _get_commit_sha(self) -> str | None:
        """Return the current HEAD SHA, or None if it fails."""
        try:
            return self._run_git(["rev-parse", "HEAD"], cwd=self.cache_dir).strip()
        except SourceError:
            return None

    def _run_git(self, args: list[str], cwd: Path | None = None) -> str:
        """Run a git command and return its stdout."""
        cmd = ["git"] + args
        env = os.environ.copy()
        env["GIT_TERMINAL_PROMPT"] = "0"  # Prevent hangs on credential prompts
        try:
            result = subprocess.run(
                cmd,
                cwd=cwd,
                env=env,
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout
        except subprocess.CalledProcessError as exc:
            raise SourceError(
                f"git source {self.name!r}: command `{' '.join(cmd)}` failed: {exc.stderr.strip()}"
            ) from exc

    def _set_cache_permissions(self, writable: bool) -> None:
        """Alter write permissions on the cache directory recursively."""
        if not self.cache_dir.exists():
            return

        def _chmod(path: str) -> None:
            try:
                current = os.stat(path).st_mode
                if writable:
                    os.chmod(path, current | stat.S_IWUSR)
                else:
                    os.chmod(path, current & ~stat.S_IWUSR)
            except OSError:
                pass

        for root, dirs, files in os.walk(str(self.cache_dir)):
            for name in dirs + files:
                _chmod(os.path.join(root, name))
        _chmod(str(self.cache_dir))
