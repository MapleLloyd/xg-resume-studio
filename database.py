import json
import os
import sqlite3
import sys
from datetime import datetime

# PyInstaller 打包态下，数据库跟随 exe 所在目录；源码态跟随本文件目录
if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# 所有用户数据统一收敛到 data/ 目录（开源打包时整体排除即可）
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)
# 测试/多实例可通过环境变量把数据库指到别处
DB_PATH = os.environ.get("RESUME_DB") or os.path.join(DATA_DIR, "data.db")
BACKUP_DIR = os.path.join(DATA_DIR, "data_backups")
MAX_BACKUPS = 20

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT DEFAULT '', avatar TEXT DEFAULT '', created_at TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS profile (
    id INTEGER PRIMARY KEY,
    name TEXT DEFAULT '', gender TEXT DEFAULT '', birth_date TEXT DEFAULT '',
    phone TEXT DEFAULT '', email TEXT DEFAULT '', address TEXT DEFAULT '',
    hometown TEXT DEFAULT '',
    self_eval TEXT DEFAULT '', self_tags TEXT DEFAULT '[]',
    summary TEXT DEFAULT '', skills TEXT DEFAULT '[]', languages TEXT DEFAULT '[]',
    photo_path TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS education (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    school TEXT DEFAULT '', degree TEXT DEFAULT '', major TEXT DEFAULT '',
    start TEXT DEFAULT '', end TEXT DEFAULT '', notes TEXT DEFAULT '',
    ongoing INTEGER DEFAULT 0, sort_order INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS papers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT DEFAULT '', authors TEXT DEFAULT '', venue TEXT DEFAULT '',
    year TEXT DEFAULT '', volume TEXT DEFAULT '', issue TEXT DEFAULT '',
    pages TEXT DEFAULT '', paper_type TEXT DEFAULT '', notes TEXT DEFAULT '',
    sort_order INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT DEFAULT '', role TEXT DEFAULT '', start TEXT DEFAULT '', end TEXT DEFAULT '',
    description TEXT DEFAULT '', ongoing INTEGER DEFAULT 0, sort_order INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS awards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT DEFAULT '', level TEXT DEFAULT '', category TEXT DEFAULT '',
    date TEXT DEFAULT '', organizer TEXT DEFAULT '', description TEXT DEFAULT '',
    source_file TEXT DEFAULT '', sort_order INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS positions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT DEFAULT '', org TEXT DEFAULT '', start TEXT DEFAULT '', end TEXT DEFAULT '',
    description TEXT DEFAULT '', source_file TEXT DEFAULT '',
    ongoing INTEGER DEFAULT 0, sort_order INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT DEFAULT '', stored_path TEXT DEFAULT '', file_type TEXT DEFAULT '',
    status TEXT DEFAULT 'parsed', raw_text TEXT DEFAULT '', created_at TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY, value TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS item_files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_type TEXT DEFAULT '', item_id INTEGER DEFAULT 0,
    filename TEXT DEFAULT '', stored_path TEXT DEFAULT '',
    created_at TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS resume_templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE, title TEXT DEFAULT '', html TEXT DEFAULT '',
    builtin INTEGER DEFAULT 0, created_at TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS resume_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER DEFAULT 1,
    name TEXT DEFAULT '默认简历',
    template TEXT DEFAULT 'classic',
    accent TEXT DEFAULT '',
    density TEXT DEFAULT 'standard',
    layout TEXT DEFAULT '',
    summary TEXT DEFAULT '',
    self_eval TEXT DEFAULT '',
    self_tags TEXT DEFAULT '[]',
    is_default INTEGER DEFAULT 0,
    created_at TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS certificates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER DEFAULT 1,
    title TEXT DEFAULT '', category TEXT DEFAULT '',
    issuer TEXT DEFAULT '', date TEXT DEFAULT '',
    level TEXT DEFAULT '', notes TEXT DEFAULT '',
    stored_path TEXT DEFAULT '', thumb_path TEXT DEFAULT '',
    ocr_text TEXT DEFAULT '', source TEXT DEFAULT 'photo',
    created_at TEXT DEFAULT ''
);
"""


# 旧库升级：缺列就补（新库由 SCHEMA 直接建出，这里只兜底老 data.db）
MIGRATIONS = [
    ("education", "ongoing", "INTEGER DEFAULT 0"),
    ("positions", "ongoing", "INTEGER DEFAULT 0"),
    ("projects", "ongoing", "INTEGER DEFAULT 0"),
    # 多账户：业务数据归属
    ("awards", "user_id", "INTEGER DEFAULT 1"),
    ("positions", "user_id", "INTEGER DEFAULT 1"),
    ("education", "user_id", "INTEGER DEFAULT 1"),
    ("papers", "user_id", "INTEGER DEFAULT 1"),
    ("projects", "user_id", "INTEGER DEFAULT 1"),
    ("files", "user_id", "INTEGER DEFAULT 1"),
    ("item_files", "user_id", "INTEGER DEFAULT 1"),
    # 资料细化：籍贯独立字段；论文卷/期/页码（GB/T 7714 完整引用格式）
    ("profile", "hometown", "TEXT DEFAULT ''"),
    ("profile", "self_eval", "TEXT DEFAULT ''"),
    ("profile", "self_tags", "TEXT DEFAULT '[]'"),
    ("papers", "volume", "TEXT DEFAULT ''"),
    ("papers", "issue", "TEXT DEFAULT ''"),
    ("papers", "pages", "TEXT DEFAULT ''"),
]


def migrate():
    conn = get_conn()
    for table, col, ddl in MIGRATIONS:
        cols = {r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}
        if cols and col not in cols:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {ddl}")
    conn.commit()
    _migrate_profile_drop_check(conn)
    conn.close()


def _migrate_profile_drop_check(conn):
    """老库的 profile 表带 CHECK (id = 1)，无法放第二个账户；原地重建去掉该约束。"""
    row = conn.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='profile'").fetchone()
    if not row or "CHECK" not in (row["sql"] or "").upper():
        return
    cols = [r[1] for r in conn.execute("PRAGMA table_info(profile)").fetchall()]
    col_list = ", ".join(cols)
    conn.executescript("""
        CREATE TABLE profile_new (
            id INTEGER PRIMARY KEY,
            name TEXT DEFAULT '', gender TEXT DEFAULT '', birth_date TEXT DEFAULT '',
            phone TEXT DEFAULT '', email TEXT DEFAULT '', address TEXT DEFAULT '',
            hometown TEXT DEFAULT '', self_eval TEXT DEFAULT '', self_tags TEXT DEFAULT '[]',
            summary TEXT DEFAULT '', skills TEXT DEFAULT '[]', languages TEXT DEFAULT '[]',
            photo_path TEXT DEFAULT ''
        );
    """)
    conn.execute(f"INSERT OR IGNORE INTO profile_new ({col_list}) SELECT {col_list} FROM profile")
    conn.execute("DROP TABLE profile")
    conn.execute("ALTER TABLE profile_new RENAME TO profile")
    conn.commit()


def ensure_default_user():
    conn = get_conn()
    n = conn.execute("SELECT COUNT(*) AS c FROM users").fetchone()["c"]
    if n == 0:
        conn.execute("INSERT INTO users (name, created_at) VALUES (?, ?)",
                     ("我的档案", datetime.now().strftime("%Y-%m-%d %H:%M")))
    conn.commit()
    conn.close()


def get_conn():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


def init_db():
    conn = get_conn()
    conn.executescript(SCHEMA)
    conn.execute("INSERT OR IGNORE INTO profile (id) VALUES (1)")
    conn.commit()
    conn.close()
    migrate()
    ensure_default_user()


def insert_profile(uid):
    """为新账户建立同名 id 的空白 profile 行（profile.id == users.id）。"""
    conn = get_conn()
    conn.execute("INSERT OR IGNORE INTO profile (id) VALUES (?)", (uid,))
    conn.commit()
    conn.close()


def get_rows_where(table, where, params, order="sort_order ASC, id ASC"):
    conn = get_conn()
    try:
        rows = conn.execute(f"SELECT * FROM {table} WHERE {where} ORDER BY {order}", params).fetchall()
    except sqlite3.OperationalError:
        rows = conn.execute(f"SELECT * FROM {table} WHERE {where} ORDER BY id", params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_rows_where(table, where, params):
    conn = get_conn()
    conn.execute(f"DELETE FROM {table} WHERE {where}", params)
    n = conn.execute("SELECT changes() AS c").fetchone()["c"]
    conn.commit()
    conn.close()
    return n


def all_rows(table, order="sort_order ASC, id ASC"):
    conn = get_conn()
    try:
        rows = conn.execute(f"SELECT * FROM {table} ORDER BY {order}").fetchall()
    except sqlite3.OperationalError:
        # 该表没有请求的排序列（如 users/files 没有 sort_order）时退回主键序
        rows = conn.execute(f"SELECT * FROM {table} ORDER BY id").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_row(table, row_id):
    conn = get_conn()
    row = conn.execute(f"SELECT * FROM {table} WHERE id = ?", (row_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_row_by(table, column, value):
    conn = get_conn()
    row = conn.execute(f"SELECT * FROM {table} WHERE {column} = ?", (value,)).fetchone()
    conn.close()
    return dict(row) if row else None


def insert_row(table, data):
    cols = [c for c in data.keys() if c != "id"]
    conn = get_conn()
    conn.execute(
        f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))})",
        [data.get(c, "") for c in cols],
    )
    conn.commit()
    new_id = conn.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]
    conn.close()
    return new_id


def update_row(table, row_id, data):
    cols = [c for c in data.keys() if c != "id"]
    if not cols:
        return
    conn = get_conn()
    sets = ", ".join(f"{c} = ?" for c in cols)
    conn.execute(f"UPDATE {table} SET {sets} WHERE id = ?", [data.get(c, "") for c in cols] + [row_id])
    conn.commit()
    conn.close()


def delete_row(table, row_id):
    conn = get_conn()
    conn.execute(f"DELETE FROM {table} WHERE id = ?", (row_id,))
    conn.commit()
    conn.close()


def next_sort_order(table):
    conn = get_conn()
    row = conn.execute(f"SELECT COALESCE(MAX(sort_order), -1) + 1 AS n FROM {table}").fetchone()
    conn.close()
    return row["n"]


def get_setting(key, default=""):
    conn = get_conn()
    row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    conn.close()
    return row["value"] if row else default


def set_setting(key, value):
    conn = get_conn()
    conn.execute(
        "INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, str(value)),
    )
    conn.commit()
    conn.close()


def json_list(value):
    try:
        return json.loads(value) if value else []
    except Exception:
        return []


def attachments_for(item_type, item_id):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM item_files WHERE item_type = ? AND item_id = ? ORDER BY id",
        (item_type, item_id),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def attachment_counts():
    conn = get_conn()
    rows = conn.execute(
        "SELECT item_type, item_id, COUNT(*) AS n FROM item_files GROUP BY item_type, item_id"
    ).fetchall()
    conn.close()
    return {(r["item_type"], r["item_id"]): r["n"] for r in rows}


def backup_db():
    """把当前数据库快照一份到 data_backups/，保留最近 MAX_BACKUPS 份。"""
    if os.environ.get("RESUME_NO_BACKUP"):
        return None
    try:
        os.makedirs(BACKUP_DIR, exist_ok=True)
        dest = os.path.join(BACKUP_DIR, "data_{}.db".format(datetime.now().strftime("%Y%m%d_%H%M%S")))
        src = sqlite3.connect(DB_PATH)
        dst = sqlite3.connect(dest)
        try:
            src.backup(dst)
        finally:
            dst.close()
            src.close()
        backups = sorted(f for f in os.listdir(BACKUP_DIR) if f.startswith("data_") and f.endswith(".db"))
        for old in backups[:-MAX_BACKUPS]:
            try:
                os.remove(os.path.join(BACKUP_DIR, old))
            except OSError:
                pass
        return dest
    except Exception:
        return None
