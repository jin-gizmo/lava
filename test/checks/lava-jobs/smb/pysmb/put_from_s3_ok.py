"""Assertions for smb/pysmb/put-from-s3-ok."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from lava import LavaError
from test.checks.smb_checker import SMBChecker


class Checker(SMBChecker):
    """Custom checker."""

    def __init__(self, *args, **kwargs) -> None:
        """Init checker state."""
        super().__init__(*args, **kwargs)
        self.share_root = Path(self.fx.dirs.smb_share)
        self.target_file: Path | None = None

    def teardown(self) -> None:
        """Remove destination file to keep tests independent."""

        if self.target_file:
            self.target_file.unlink(missing_ok=True)
            parent_dir = self.target_file.parent
            if parent_dir != self.share_root:
                try:
                    parent_dir.rmdir()
                except OSError:
                    pass

    def check(
        self,
        job_result: dict[str, Any] | None,
        job_events: dict[tuple[str, str], list[dict[str, Any]]],
        job_error: LavaError | None,
    ) -> None:
        """Validate smb_put copied a non-empty file into the SMB share."""

        assert job_error is None
        assert job_result is not None
        assert job_result['exit_status'] == 0

        _, remote_path = job_result['destination'].split(':', 1)
        target_file = self.share_root / remote_path.lstrip('/')
        self.target_file = target_file
        assert target_file.is_file()
        assert target_file.stat().st_size > 0
