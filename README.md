# PM3
Like pm2 without node.js.

![](https://github.com/ilariofebi/PM3/blob/main/screenshots/ls.png?raw=true)

## Installation

Create a virtual environment and install PM3:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install pm3
```

To upgrade:

```bash
pip install -U pm3
```

## Quick start

```bash
pm3 daemon start
pm3 ping
```

Create and manage a process:

```bash
pm3 new "/bin/sleep 10" -n sleep10 --autorun
pm3 start sleep10
pm3 stop sleep10
pm3 rm sleep10
```

## Useful commands

```bash
pm3 ls
pm3 ls -l
pm3 ls -j
pm3 ps all
pm3 dump all -f dump.json
pm3 load -f dump.json
pm3 log all -f
pm3 err all -n 50
pm3 flush all all
pm3 version
```

## Configuration

Default config file: `~/.pm3/config.ini`

```ini
[main_section]
pm3_home_dir = /home/user/.pm3
pm3_db = /home/user/.pm3/pm3_db.json
pm3_db_process_table = pm3_procs
main_interpreter = /home/user/venv/bin/python
max_backups = 20
log_max_bytes = 10485760
log_backup_count = 5
log_compress = true

[backend]
name = __backend__
url = http://127.0.0.1:7979/
cmd = /home/user/venv/bin/pm3_backend

[cron_checker]
name = __cron_checker__
cmd = /home/user/venv/bin/pm3_cron_checker
sleep_time = 5
debug = False
```

## Backup and recovery

PM3 creates compressed backups of the TinyDB file before write operations.
Backups are stored in `~/.pm3/backups/`.

If the database is corrupted at startup, PM3 prints a restore hint. Manual restore example:

```bash
gunzip -c ~/.pm3/backups/pm3_db_YYYYMMDD_HHMMSS.json.gz > ~/.pm3/pm3_db.json
```

## Log rotation

Process log files are managed through `RotatingFileHandler` and can be configured with:

- `log_max_bytes`
- `log_backup_count`
- `log_compress`

When `log_compress=true`, rotated logs are gzip-compressed.
