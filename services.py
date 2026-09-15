import random
import secrets
import smtplib
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from flask import current_app
from db import get_db


def utcnow():
    return datetime.now(timezone.utc)


def send_email(to, subject, body):
    cfg = current_app.config
    if not cfg['SMTP_HOST'] or not cfg['SMTP_USERNAME']:
        current_app.logger.info('Email not configured. Would send to %s: %s\\n%s', to, subject, body)
        return False
    msg = EmailMessage()
    msg['From'] = cfg['SMTP_USERNAME']
    msg['To'] = to
    msg['Subject'] = subject
    msg.set_content(body)
    with smtplib.SMTP(cfg['SMTP_HOST'], cfg['SMTP_PORT']) as server:
        if cfg['SMTP_USE_TLS']:
            server.starttls()
        server.login(cfg['SMTP_USERNAME'], cfg['SMTP_PASSWORD'])
        server.send_message(msg)
    return True


def add_ledger(user_id, kind, amount, note):
    db = get_db()
    db.execute('INSERT INTO ledger(user_id,kind,amount,note) VALUES(?,?,?,?)', (user_id,kind,amount,note))
    db.execute('UPDATE users SET balance = balance + ? WHERE id=?', (amount,user_id))
    db.commit(); db.close()


def create_email_code(user_id):
    code = f'{secrets.randbelow(1000000):06d}'
    expires = utcnow() + timedelta(seconds=60)
    db = get_db()
    db.execute('INSERT INTO email_codes(user_id,code,expires_at) VALUES(?,?,?)', (user_id,code,expires.isoformat()))
    db.commit(); db.close()
    return code


def choose_lucky_winner(draw_id):
    db = get_db()
    rows = db.execute('SELECT user_id,tickets FROM lucky_tickets WHERE draw_id=? AND tickets>0', (draw_id,)).fetchall()
    pool = []
    for row in rows:
        pool.extend([row['user_id']] * row['tickets'])
    if not pool:
        db.close(); return None
    winner = random.choice(pool)
    db.close(); return winner
