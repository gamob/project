import sqlite3
from datetime import datetime

DB_PATH = "chat_history.db"

def get_connection():
    """Returns a connection to the SQLite database."""
    return sqlite3.connect(DB_PATH)

def init_db():
    """Creates the tables if they don't exist yet. Safe to call every startup."""
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                title      TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                role       TEXT NOT NULL,
                content    TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES sessions(id)
            )
        """)
        conn.commit()

def create_session(first_message: str) -> int:
    """
    Creates a new chat session.
    Title is auto-generated from the first user message (truncated to 40 chars).
    Returns the new session_id.
    """
    title = first_message[:40] + ("..." if len(first_message) > 40 else "")
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO sessions (title, created_at) VALUES (?, ?)",
            (title, now)
        )
        conn.commit()
        return cursor.lastrowid

def save_message(session_id: int, role: str, content: str):
    """Saves a single message to a session."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO messages (session_id, role, content, created_at) VALUES (?, ?, ?, ?)",
            (session_id, role, content, now)
        )
        conn.commit()

def load_session_messages(session_id: int) -> list[dict]:
    """Loads all messages for a given session as a list of {role, content} dicts."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT role, content FROM messages WHERE session_id = ? ORDER BY id ASC",
            (session_id,)
        ).fetchall()
    return [{"role": row[0], "content": row[1]} for row in rows]

def get_all_sessions() -> list[dict]:
    """Returns all sessions ordered by most recent first."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id, title, created_at FROM sessions ORDER BY id DESC"
        ).fetchall()
    return [{"id": row[0], "title": row[1], "created_at": row[2]} for row in rows]

def delete_session(session_id: int):
    """Deletes a session and all its messages."""
    with get_connection() as conn:
        conn.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
        conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        conn.commit()

def rename_session(session_id: int, new_title: str):
    """Renames a chat session."""
    new_title = new_title.strip()
    if not new_title:
        return  # Don't allow empty titles
    with get_connection() as conn:
        conn.execute(
            "UPDATE sessions SET title = ? WHERE id = ?",
            (new_title, session_id)
        )
        conn.commit()
