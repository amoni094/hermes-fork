#!/usr/bin/env python3
"""
hermes-gateway-prestart.py
Runs before the gateway opens state.db.
1. Force-checkpoint the WAL into the main db file.
2. Remove any retired-wal dirs whose artifact change_counter <= live db.
3. Exit 0 always (never block gateway startup).
"""
import os, sys, sqlite3, struct, shutil, json, glob, logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s %(message)s')
log = logging.getLogger('prestart')

def cc(path):
    try:
        with open(path, 'rb') as f:
            data = f.read(100)
        if len(data) < 32:
            return 0
        return struct.unpack('>I', data[28:32])[0]
    except Exception:
        return 0

def checkpoint_wal(db_path):
    try:
        conn = sqlite3.connect(db_path, timeout=10)
        conn.execute('PRAGMA wal_checkpoint(TRUNCATE)')
        conn.close()
        log.info(f'WAL checkpoint OK: {db_path}')
    except Exception as e:
        log.warning(f'WAL checkpoint failed (non-fatal): {e}')

def clean_retired_dirs(base_dir, db_path):
    live_cc = cc(db_path)
    pattern = os.path.join(base_dir, 'state.db.retired-wal-*')
    dirs = sorted(glob.glob(pattern))
    for d in dirs:
        try:
            art_db = os.path.join(d, 'state.db')
            art_cc = cc(art_db)
            if art_cc <= live_cc:
                shutil.rmtree(d)
                log.info(f'Removed stale retired-wal dir: {os.path.basename(d)} (art_cc={art_cc} <= live_cc={live_cc})')
            else:
                log.warning(f'Keeping retired-wal dir: {os.path.basename(d)} (art_cc={art_cc} > live_cc={live_cc}) — manual inspection needed')
        except Exception as e:
            log.warning(f'Could not process {d}: {e}')

hermes_home = os.environ.get('HERMES_HOME', os.path.expanduser('~/.hermes'))
db_path = os.path.join(hermes_home, 'state.db')

if not os.path.exists(db_path):
    log.info(f'No state.db at {db_path}, skipping')
    sys.exit(0)

checkpoint_wal(db_path)
clean_retired_dirs(hermes_home, db_path)
log.info('Pre-start cleanup complete')
sys.exit(0)
