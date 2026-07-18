"""Shared checker utilities for SMB integration jobs."""

from __future__ import annotations

from pathlib import Path
from time import monotonic, sleep

from lava.connection import get_smb_connection
from lava.lib.smb import SMBBaseError
from test.integration.conftest import HandlerChecker


class SMBChecker(HandlerChecker):
    """Base checker for SMB jobs with shared setup/teardown helpers."""

    def __init__(self, *args, **kwargs) -> None:
        """Initialize shared SMB checker state."""

        super().__init__(*args, **kwargs)

        self.message = ''
        self.expected_status = 0
        self.conn_id = ''

        self.share_name_get: str | None = None
        self.remote_source: str | None = None
        self.share_file: Path | None = None
        self.seed_source = False
        self.share_content = ''

        self.share_name_put: str | None = None
        self.remote_dir: str | None = None
        self.share_dir: Path | None = None
        self.share_target: Path | None = None

        self._snapshot_files: dict[Path, bytes | None] = {}

    def init_split_triplet(self) -> None:
        """Initialize common split exe state from a single args triplet."""

        args = self.job_spec['parameters']['args']
        assert len(args) == 3, f'Expected exactly 3 args, got {len(args)}'

        self.message = args[0]
        self.expected_status = 0 if self.message.startswith('OK:') else 1
        self.conn_id = self.job_spec['parameters']['connections']['smb']

    def configure_split_get_source(self) -> None:
        """Rewrite SMB source to a run-scoped path and define source seed metadata."""

        source = self.job_spec['parameters']['args'][1]
        self.share_name_get, source_path = source.split(':', 1)

        source_name = source_path.rsplit('/', 1)[-1]
        self.remote_source = f'/{self.run_id}/{source_name}'
        self.job_spec['parameters']['args'][1] = f'{self.share_name_get}:{self.remote_source}'

        self.share_file = Path(self.fx.dirs.smb_share) / self.run_id / source_name
        self.seed_source = 'no such source file' not in self.message.lower()
        self.share_content = f'hello-world,{self.run_id}\n'

    def configure_split_put_destination(self) -> None:
        """Rewrite SMB destination to a run-scoped path and define cleanup metadata."""

        destination = self.job_spec['parameters']['args'][2]
        if ':' not in destination or destination.startswith('s3://'):
            return

        share_name, remote_path = destination.split(':', 1)
        if not remote_path.startswith('/'):
            return

        target_name = remote_path.rsplit('/', 1)[-1]
        self.share_name_put = share_name
        self.remote_dir = f'/{self.run_id}'
        run_scoped_target = f'{self.remote_dir}/{target_name}'
        self.job_spec['parameters']['args'][2] = f'{self.share_name_put}:{run_scoped_target}'

        self.share_dir = Path(self.fx.dirs.smb_share) / self.run_id
        self.share_target = self.share_dir / target_name

    def configure_smb_source(
        self,
        conn_id: str,
        share_name: str,
        remote_source: str,
        share_file: Path,
        share_content: str,
        seed_source: bool = True,
    ) -> None:
        """Configure SMB source file setup/teardown handled by this checker."""

        self.conn_id = conn_id
        self.share_name_get = share_name
        self.remote_source = remote_source
        self.share_file = share_file
        self.share_content = share_content
        self.seed_source = seed_source

    def setup(self) -> None:
        """Apply common SMB setup routines configured by the checker subclass."""

        self.setup_split_get_source()
        self.setup_split_put_destination()

    def teardown(self) -> None:
        """Apply common SMB teardown routines configured by the checker subclass."""

        self.teardown_split_put_destination()
        self.teardown_split_get_source()
        self.restore_snapshot_files()

    def snapshot_files(self, *paths: Path) -> None:
        """Snapshot file contents so teardown can restore original state."""

        for path in paths:
            self._snapshot_files[path] = path.read_bytes() if path.exists() else None

    def restore_snapshot_files(self) -> None:
        """Restore previously snapshotted files and remove newly created ones."""

        for path, contents in self._snapshot_files.items():
            if contents is None:
                path.unlink(missing_ok=True)
            else:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(contents)
        self._snapshot_files.clear()

    def setup_split_get_source(self) -> None:
        """Create and verify run-scoped SMB source file for split exe-get jobs."""

        if not self.seed_source:
            return
        if not self.share_file or not self.share_name_get or not self.remote_source or not self.conn_id:
            return

        self.share_file.parent.mkdir(parents=True, exist_ok=True)
        self.share_file.write_text(self.share_content, encoding='utf-8')

        expected_size = len(self.share_content.encode('utf-8'))
        deadline = monotonic() + 5.0
        last_error: Exception | None = None
        with get_smb_connection(self.conn_id, self.realm) as conn:
            while monotonic() < deadline:
                try:
                    smb_file = conn.get_attributes(self.share_name_get, self.remote_source, timeout=2)
                    if smb_file.file_size == expected_size:
                        break
                except SMBBaseError as exc:
                    last_error = exc
                sleep(0.1)
            else:
                raise AssertionError(
                    f'SMB source file did not become visible in time: '
                    f'{self.share_name_get}:{self.remote_source}'
                ) from last_error

    def setup_split_put_destination(self) -> None:
        """Create and verify run-scoped SMB destination directory for split exe-put jobs."""

        if not self.share_dir or not self.remote_dir or not self.share_name_put:
            return
        if self.expected_status != 0:
            return
        if not self.conn_id:
            return

        self.share_dir.mkdir(parents=True, exist_ok=True)

        deadline = monotonic() + 5.0
        last_error: Exception | None = None
        with get_smb_connection(self.conn_id, self.realm) as conn:
            while monotonic() < deadline:
                try:
                    entries = conn.list_path(self.share_name_put, '/', timeout=2)
                    if any(entry.filename == self.run_id for entry in entries):
                        break
                except SMBBaseError as exc:
                    last_error = exc
                sleep(0.1)
            else:
                raise AssertionError(
                    f'SMB destination directory did not become visible in time: '
                    f'{self.share_name_put}:{self.remote_dir}'
                ) from last_error

    def teardown_split_get_source(self) -> None:
        """Remove run-scoped source assets created for split exe-get jobs."""

        if not self.seed_source or not self.share_file:
            return

        self.share_file.unlink(missing_ok=True)
        try:
            self.share_file.parent.rmdir()
        except OSError:
            pass

    def teardown_split_put_destination(self) -> None:
        """Remove run-scoped destination assets created for split exe-put jobs."""

        if self.share_target:
            self.share_target.unlink(missing_ok=True)
        if self.share_dir:
            try:
                self.share_dir.rmdir()
            except OSError:
                pass
