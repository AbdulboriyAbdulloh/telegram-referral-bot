import os
import sqlite3
from datetime import datetime
from typing import Optional, Tuple, List

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "database.db")

def conn():
    return sqlite3.connect(DB_PATH)

def init_db():
    c = conn()
    cur = c.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        full_name TEXT,
        invite_link TEXT,
        ref_count INTEGER DEFAULT 0,
        created_at TEXT
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS invites (
        invited_user_id INTEGER PRIMARY KEY,
        inviter_user_id INTEGER
    )
    """)

    # Kimin kiminle geldiğini tekrar saymamak için:
    cur.execute("""
    CREATE TABLE IF NOT EXISTS joins (
        invitee_user_id INTEGER PRIMARY KEY,
        inviter_user_id INTEGER,
        invite_link TEXT,
        joined_at TEXT
    )
    """)

    c.commit()
    c.close()

def upsert_user(user_id: int, username: Optional[str]):
    c = conn()
    cur = c.cursor()
    cur.execute(
        "INSERT OR IGNORE INTO users (user_id, username, created_at) VALUES (?, ?, ?)",
        (user_id, username, datetime.utcnow().isoformat())
    )
    cur.execute(
        "UPDATE users SET username=COALESCE(?, username) WHERE user_id=?",
        (username, user_id)
    )
    c.commit()
    c.close()

def set_full_name(user_id: int, full_name: str):
    c = conn()
    cur = c.cursor()
    cur.execute("UPDATE users SET full_name=? WHERE user_id=?", (full_name, user_id))
    c.commit()
    c.close()

def get_full_name(user_id: int) -> Optional[str]:
    c = conn()
    cur = c.cursor()
    cur.execute("SELECT full_name FROM users WHERE user_id=?", (user_id,))
    row = cur.fetchone()
    c.close()
    return row[0] if row and row[0] else None

def set_invite_link(user_id: int, invite_link: str):
    c = conn()
    cur = c.cursor()
    cur.execute("UPDATE users SET invite_link=? WHERE user_id=?", (invite_link, user_id))
    c.commit()
    c.close()

def get_invite_link(user_id: int) -> Optional[str]:
    c = conn()
    cur = c.cursor()
    cur.execute("SELECT invite_link FROM users WHERE user_id=?", (user_id,))
    row = cur.fetchone()
    c.close()
    return row[0] if row and row[0] else None

def find_inviter_by_link(invite_link: str) -> Optional[int]:
    c = conn()
    cur = c.cursor()
    cur.execute("SELECT user_id FROM users WHERE invite_link=?", (invite_link,))
    row = cur.fetchone()
    c.close()
    return int(row[0]) if row else None

def already_counted(invitee_user_id: int) -> bool:
    c = conn()
    cur = c.cursor()
    cur.execute("SELECT 1 FROM joins WHERE invitee_user_id=?", (invitee_user_id,))
    row = cur.fetchone()
    c.close()
    return row is not None

def record_join(invitee_user_id: int, inviter_user_id: int, invite_link: str) -> bool:
    """
    İlk kez geliyorsa kaydeder ve inviter'ın ref_count'unu +1 yapar.
    Tekrar gelirse False döner.
    """
    if already_counted(invitee_user_id):
        return False

    c = conn()
    cur = c.cursor()

    cur.execute(
        "INSERT OR IGNORE INTO joins (invitee_user_id, inviter_user_id, invite_link, joined_at) VALUES (?, ?, ?, ?)",
        (invitee_user_id, inviter_user_id, invite_link, datetime.utcnow().isoformat())
    )
    cur.execute(
        "UPDATE users SET ref_count = ref_count + 1 WHERE user_id=?",
        (inviter_user_id,)
    )
    c.commit()
    c.close()
    return True

def top10() -> List[Tuple[str, str, int]]:
    c = conn()
    cur = c.cursor()
    cur.execute("""
        SELECT COALESCE(username, CAST(user_id AS TEXT)) as uname,
               COALESCE(full_name, '') as fname,
               ref_count
        FROM users
        ORDER BY ref_count DESC
        LIMIT 10
    """)
    rows = cur.fetchall()
    c.close()
    return rows

def all_users() -> List[Tuple[int, Optional[str], Optional[str], int, Optional[str]]]:
    c = conn()
    cur = c.cursor()
    cur.execute("""
        SELECT user_id, username, full_name, ref_count, invite_link
        FROM users
        ORDER BY ref_count DESC, user_id ASC
    """)
    rows = cur.fetchall()
    c.close()
    return rows
def get_ref_count(user_id: int) -> int:
    c = conn()
    cur = c.cursor()
    cur.execute("SELECT ref_count FROM users WHERE user_id=?", (user_id,))
    row = cur.fetchone()
    c.close()
    return int(row[0]) if row and row[0] is not None else 0
def save_invite(invited_user_id: int, inviter_user_id: int):
    c = conn()
    cur = c.cursor()
    cur.execute(
        "INSERT OR IGNORE INTO invites (invited_user_id, inviter_user_id) VALUES (?, ?)",
        (invited_user_id, inviter_user_id)
    )
    cur.execute(
        "UPDATE users SET ref_count = ref_count + 1 WHERE user_id=?",
        (inviter_user_id,)
    )
    c.commit()
    c.close()
