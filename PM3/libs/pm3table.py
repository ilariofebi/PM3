import json
import hashlib
import gzip
import logging
import shutil
from datetime import datetime
from pathlib import Path
from PM3.model.pm3_protocol import ION
from PM3.model.process import Process
from tinydb import where
from tinydb.table import Table
from filelock import FileLock
from configparser import ConfigParser

logger = logging.getLogger(__name__)


def hidden_proc(x: str) -> bool:
    return x.startswith('__') and x.endswith('__')


class Pm3Database:
    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self.backup_dir = self.db_path.parent / 'backups'
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.max_backups = 20
        self._last_backup_hash = None
        config = ConfigParser()
        config_file = Path('~/.pm3/config.ini').expanduser()
        if config_file.exists():
            config.read(config_file)
            self.max_backups = int(config['main_section'].get('max_backups', '20'))

    @staticmethod
    def _calculate_file_hash(file_path: Path, compressed: bool = False) -> str:
        sha = hashlib.sha256()
        opener = gzip.open if compressed else open
        with opener(file_path, 'rb') as fh:
            for chunk in iter(lambda: fh.read(4096), b''):
                sha.update(chunk)
        return sha.hexdigest()

    def _compress_file(self, source_path: Path, dest_path: Path) -> None:
        with open(source_path, 'rb') as f_in:
            with gzip.open(dest_path, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)

    def _decompress_file(self, source_path: Path, dest_path: Path) -> None:
        with gzip.open(source_path, 'rb') as f_in:
            with open(dest_path, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)

    def _cleanup_old_backups(self):
        backups = sorted(self.backup_dir.glob(f'{self.db_path.stem}_*.json.gz'))
        if len(backups) > self.max_backups:
            for old_backup in backups[:-self.max_backups]:
                old_backup.unlink(missing_ok=True)

    def _create_backup(self) -> bool:
        if not self.db_path.exists():
            return True
        try:
            with open(self.db_path, 'r', encoding='utf-8') as db_file:
                json.load(db_file)
        except json.JSONDecodeError:
            logger.error('Database is corrupted: backup skipped')
            return False

        current_hash = self._calculate_file_hash(self.db_path)
        if current_hash == self._last_backup_hash:
            return True

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        temp_backup_path = self.backup_dir / f'{self.db_path.stem}_{timestamp}.json'
        backup_path = self.backup_dir / f'{self.db_path.stem}_{timestamp}.json.gz'
        shutil.copy2(self.db_path, temp_backup_path)
        self._compress_file(temp_backup_path, backup_path)
        temp_backup_path.unlink(missing_ok=True)
        try:
            with gzip.open(backup_path, 'rt', encoding='utf-8') as backup_file:
                json.load(backup_file)
        except Exception:
            backup_path.unlink(missing_ok=True)
            logger.error('Backup validation failed')
            return False

        self._last_backup_hash = current_hash
        self._cleanup_old_backups()
        return True

    def safe_write(self, operation):
        if not self._create_backup():
            return False
        result = operation()
        try:
            with open(self.db_path, 'r', encoding='utf-8') as db_file:
                json.load(db_file)
        except Exception:
            logger.exception('Database validation failed after write')
            return False
        return result


class Pm3Table:
    def __init__(self, tbl: Table, lock_file: str, db_path: str):
        self.tbl = tbl
        self.lock_file_name = lock_file
        self.db = Pm3Database(db_path)

        self.locked_all = self.locked_function(self.tbl.all)
        self.locked_contains = self.locked_function(self.tbl.contains)
        self.locked_get = self.locked_function(self.tbl.get)
        self.locked_remove = self.locked_function(self.tbl.remove)
        self.locked_update = self.locked_function(self.tbl.update)

    def locked_function(this, func):
        def inner(*args, **kwargs):
            logger.debug("Acquiring db lock for %s", getattr(func, "__name__", str(func)))
            with FileLock(this.lock_file_name):
                output = func(*args, **kwargs)
            logger.debug("Released db lock for %s", getattr(func, "__name__", str(func)))
            return output
        return inner
    
    def next_id(self, start_from=None):
        if start_from:
            # Next Id start from specific id
            pm3_id = start_from
            while self.check_exist(pm3_id):
                pm3_id += 1
            return pm3_id
        else:
            all_docs = self.locked_all()
            if len(all_docs) > 0:
                return max([i['pm3_id'] for i in all_docs])+1
            else:
                return 1

    def check_exist(self, val, col='pm3_id'):
            return self.locked_contains(where(col) == val)

    def select(self, proc, col='pm3_id'):
        return self.locked_get(where(col) == proc.model_dump()[col])

    def delete(self, proc, col='pm3_id'):
        if self.select(proc, col):
            def operation():
                self.tbl.remove(where(col) == proc.model_dump()[col])
                return True
            return self.locked_function(lambda: self.db.safe_write(operation))()
        else:
            return False

    def update(self, proc, col='pm3_id'):
        if self.select(proc, col):
            def operation():
                self.tbl.update(proc.model_dump(), where(col) == proc.model_dump()[col])
                return True
            return self.locked_function(lambda: self.db.safe_write(operation))()
        else:
            return False

    def find_id_or_name(self, id_or_name, hidden=False) -> ION:
        if id_or_name == 'all':
            # Tutti (nascosti esclusi)
            out = ION('special',
                    id_or_name,
                    [Process(**i) for i in self.locked_all() if not hidden_proc(i['pm3_name'])]
                    )
            return out

        elif id_or_name == 'ALL':
            # Proprio tutti (compresi i nascosti)
            out = ION('special', id_or_name, [Process(**i) for i in self.locked_all()])
            return out
        elif id_or_name == 'hidden_only':
            # Solo i nascosti (nascosti esclusi)
            out = ION('special',
                    id_or_name,
                    [Process(**i) for i in self.locked_all() if hidden_proc(i['pm3_name'])]
                    )
            return out

        elif id_or_name == 'autorun_only':
            # Tutti gli autorun (compresi i sospesi)
            out = ION('special',
                    id_or_name,
                    [Process(**i) for i in self.locked_all() if i['autorun'] is True])
            return out
        elif id_or_name == 'autorun_enabled':
            # Gruppo di autorun non sospesi
            out = ION('special',
                    id_or_name,
                    [Process(**i) for i in self.locked_all() if i['autorun'] is True and i['autorun_exclude'] is False])
            return out

        try:
            id_or_name = int(id_or_name)
        except ValueError:
            if self.check_exist(id_or_name, col='pm3_name'):
                p_data = self.locked_get(where('pm3_name') == id_or_name)
                out = ION('pm3_name', id_or_name, [Process(**p_data), ])
            else:
                out = ION('pm3_name', id_or_name, [])

        else:
            if self.check_exist(id_or_name, col='pm3_id'):
                p_data = self.locked_get(where('pm3_id') == id_or_name)
                out = ION('pm3_id', id_or_name, [Process(**p_data), ])
            else:
                out = ION('pm3_id', id_or_name, [])
        return out
