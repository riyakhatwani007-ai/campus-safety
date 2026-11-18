"""Database layer. Default = SQLite (zero setup). Set DB_TYPE=mysql to use MySQL."""
import os, json, sqlite3, datetime
from werkzeug.security import generate_password_hash

BASE = os.path.dirname(os.path.abspath(__file__))
DB_TYPE = os.getenv("DB_TYPE", "sqlite")
SQLITE_PATH = os.getenv("DB_PATH", os.path.join(BASE, "campus_safety.db"))


def now():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def get_conn():
    if DB_TYPE == "mysql":
        import mysql.connector
        return mysql.connector.connect(
            host=os.getenv("DB_HOST", "localhost"),
            user=os.getenv("DB_USER", "root"),
            password=os.getenv("DB_PASSWORD", ""),
            database=os.getenv("DB_NAME", "campus_safety"),
        )
    conn = sqlite3.connect(SQLITE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _sql(sql):
    # We write queries with '?' (SQLite style); MySQL needs '%s'.
    return sql.replace("?", "%s") if DB_TYPE == "mysql" else sql


def query(sql, args=(), one=False):
    """Run a SELECT. Returns list of dicts (or one dict / None if one=True)."""
    conn = get_conn()
    try:
        cur = conn.cursor(dictionary=True) if DB_TYPE == "mysql" else conn.cursor()
        cur.execute(_sql(sql), args)
        rows = [dict(r) for r in cur.fetchall()]
        if one:
            return rows[0] if rows else None
        return rows
    finally:
        conn.close()


def execute(sql, args=()):
    """Run INSERT/UPDATE. Returns the new row id."""
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(_sql(sql), args)
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def init_db():
    """Create tables and seed contacts + a default security account (first run only)."""
    schema_file = "schema_mysql.sql" if DB_TYPE == "mysql" else "schema_sqlite.sql"
    with open(os.path.join(BASE, schema_file), encoding="utf-8") as f:
        script = f.read()
    conn = get_conn()
    try:
        if DB_TYPE == "mysql":
            cur = conn.cursor()
            for stmt in script.split(";"):
                if stmt.strip():
                    cur.execute(stmt)
            conn.commit()
        else:
            conn.executescript(script)
    finally:
        conn.close()

    if not query("SELECT id FROM emergency_contacts LIMIT 1"):
        with open(os.path.join(BASE, "contacts.json"), encoding="utf-8") as f:
            for c in json.load(f):
                execute("INSERT INTO emergency_contacts (label, number, categories, is_national) VALUES (?,?,?,?)",
                        (c["label"], c["number"], c["categories"], c["is_national"]))

    if not query("SELECT id FROM users WHERE role='security' LIMIT 1"):
        pw = os.getenv("SECURITY_PASSWORD", "ChangeMe123")
        execute("INSERT INTO users (name,email,password_hash,role,phone,created_at) VALUES (?,?,?,?,?,?)",
                ("Campus Security", "security@campus.local", generate_password_hash(pw), "security", "", now()))
