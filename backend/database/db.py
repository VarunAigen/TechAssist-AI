"""SQLite database setup and models."""

import sqlite3
import os
from datetime import datetime
from config import settings


def get_db_connection():
    """Get a database connection with row factory."""
    conn = sqlite3.connect(settings.SQLITE_DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    """Initialize database tables."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'bd_rep',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Documents table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            original_name TEXT NOT NULL,
            file_type TEXT NOT NULL,
            file_size INTEGER DEFAULT 0,
            chunk_count INTEGER DEFAULT 0,
            uploaded_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (uploaded_by) REFERENCES users(id)
        )
    """)

    # Queries / Chat history table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS queries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            question TEXT NOT NULL,
            answer TEXT NOT NULL,
            confidence_tier TEXT NOT NULL,
            confidence_score REAL NOT NULL,
            sources TEXT,
            is_bridge_response INTEGER DEFAULT 0,
            rating INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    # Chat sessions table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT DEFAULT 'New Chat',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    # Add session_id to queries if not exists (for grouping)
    try:
        cursor.execute("ALTER TABLE queries ADD COLUMN session_id INTEGER REFERENCES chat_sessions(id)")
    except sqlite3.OperationalError:
        pass  # Column already exists

    conn.commit()
    conn.close()
    print("[OK] Database initialized successfully")


def seed_demo_users():
    """Create demo users for the application."""
    from auth.jwt_handler import hash_password

    conn = get_db_connection()
    cursor = conn.cursor()

    demo_users = [
        ("demo@cloudnexus.com", hash_password("demo123"), "Alex Morgan", "bd_rep"),
        ("admin@cloudnexus.com", hash_password("admin123"), "Sam Chen", "admin"),
    ]

    for email, pwd_hash, name, role in demo_users:
        try:
            cursor.execute(
                "INSERT INTO users (email, password_hash, full_name, role) VALUES (?, ?, ?, ?)",
                (email, pwd_hash, name, role),
            )
        except sqlite3.IntegrityError:
            pass  # User already exists

    conn.commit()
    conn.close()
    print("[OK] Demo users seeded")
