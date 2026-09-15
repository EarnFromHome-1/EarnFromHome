import sqlite3
from flask import current_app

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    username TEXT UNIQUE,
    balance REAL NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'pending_payment',
    email_verified INTEGER NOT NULL DEFAULT 0,
    terms_accepted INTEGER NOT NULL DEFAULT 0,
    referral_code TEXT UNIQUE,
    referred_by TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS payment_proofs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    amount REAL NOT NULL,
    recipient TEXT NOT NULL,
    filename TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(id)
);
CREATE TABLE IF NOT EXISTS email_codes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    code TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    used INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY(user_id) REFERENCES users(id)
);
CREATE TABLE IF NOT EXISTS ledger (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    kind TEXT NOT NULL,
    amount REAL NOT NULL,
    note TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(id)
);
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    reward REAL NOT NULL,
    instructions TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS task_submissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    task_id INTEGER NOT NULL,
    proof_filename TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(id),
    FOREIGN KEY(task_id) REFERENCES tasks(id)
);
CREATE TABLE IF NOT EXISTS withdrawals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    amount REAL NOT NULL,
    destination TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(id)
);
CREATE TABLE IF NOT EXISTS referrals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    referrer_id INTEGER NOT NULL,
    referred_id INTEGER NOT NULL,
    reward REAL NOT NULL DEFAULT 5000,
    status TEXT NOT NULL DEFAULT 'pending',
    FOREIGN KEY(referrer_id) REFERENCES users(id),
    FOREIGN KEY(referred_id) REFERENCES users(id)
);
CREATE TABLE IF NOT EXISTS lucky_draws (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at TEXT NOT NULL,
    collection_ends_at TEXT NOT NULL,
    cooldown_ends_at TEXT,
    status TEXT NOT NULL DEFAULT 'collecting',
    winner_user_id INTEGER,
    prize_pool REAL NOT NULL DEFAULT 0,
    FOREIGN KEY(winner_user_id) REFERENCES users(id)
);
CREATE TABLE IF NOT EXISTS lucky_tickets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    draw_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    tickets INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY(draw_id) REFERENCES lucky_draws(id),
    FOREIGN KEY(user_id) REFERENCES users(id)
);
"""

def get_db():
    db = sqlite3.connect(current_app.config['DATABASE'])
    db.row_factory = sqlite3.Row
    return db

def init_db():
    import os
    os.makedirs(os.path.dirname(current_app.config['DATABASE']), exist_ok=True)
    os.makedirs(current_app.config['UPLOAD_DIR'], exist_ok=True)
    db = get_db()
    db.executescript(SCHEMA)
    if db.execute('SELECT COUNT(*) FROM tasks').fetchone()[0] == 0:
        db.executemany(
            'INSERT INTO tasks(title,reward,instructions) VALUES(?,?,?)',
            [
                ('Watch an ad', 500, 'Watch the assigned advertisement and submit the required proof.'),
                ('Visit a site', 750, 'Visit the assigned site and complete the stated action.'),
                ('Install an app', 1000, 'Install the assigned app and submit proof when the task is complete.'),
            ],
        )
    db.commit()
    db.close()
