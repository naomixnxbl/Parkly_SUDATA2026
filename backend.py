#!/usr/bin/env python3
"""
Parkly backend — user accounts + booking management.

Endpoints:
  POST /signup              — create a new account
  POST /login               — sign in (returns a session token)
  GET  /me                  — get current user (requires X-Parkly-Token header)
  POST /reserve             — create a booking (requires X-Parkly-Token)
  GET  /bookings            — list CURRENT USER'S bookings
  GET  /bookings/:id        — get one booking (must belong to user)
  DELETE /bookings/:id      — cancel booking
  POST /bookings/:id/extend — extend by 1 hour
  GET  /health              — health check

Run:
    python backend.py     (starts on http://localhost:8788)

Data persists in parkly.db (SQLite).
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3, uuid, datetime, hashlib, secrets, os
from functools import wraps

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

DB_FILE = 'parkly.db'


def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id       TEXT PRIMARY KEY,
                email         TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at    TEXT NOT NULL
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                token      TEXT PRIMARY KEY,
                user_id    TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS bookings (
                booking_id    TEXT PRIMARY KEY,
                user_id       TEXT NOT NULL,
                spot_id       TEXT,
                spot_name     TEXT NOT NULL,
                dest          TEXT,
                duration_hrs  INTEGER NOT NULL,
                price         REAL,
                start_ms      INTEGER NOT NULL,
                status        TEXT NOT NULL DEFAULT 'active',
                created_at    TEXT NOT NULL
            )
        ''')
    print('  Database ready → parkly.db')


def hash_pw(pw: str) -> str:
    return hashlib.sha256(('parkly_demo_salt' + pw).encode()).hexdigest()


def new_token() -> str:
    return 'tok-' + secrets.token_urlsafe(24)


def user_from_token(token):
    if not token: return None
    with get_db() as conn:
        row = conn.execute('''
            SELECT u.user_id, u.email FROM sessions s
            JOIN users u ON u.user_id = s.user_id
            WHERE s.token = ?
        ''', (token,)).fetchone()
    return dict(row) if row else None


def require_auth(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user = user_from_token(request.headers.get('X-Parkly-Token', ''))
        if not user:
            return jsonify({'error': 'Not authenticated'}), 401
        kwargs['user'] = user
        return fn(*args, **kwargs)
    return wrapper


# ─── AUTH ─────────────────────────────────────────────────────────

@app.route('/signup', methods=['POST'])
def signup():
    data = request.get_json() or {}
    email = (data.get('email') or '').strip().lower()
    pw = data.get('password') or ''
    if '@' not in email or len(email) < 5:
        return jsonify({'error': 'Invalid email'}), 400
    if len(pw) < 4:
        return jsonify({'error': 'Password must be at least 4 characters'}), 400

    user_id = 'usr-' + str(uuid.uuid4())[:8]
    now = datetime.datetime.now().isoformat()
    try:
        with get_db() as conn:
            conn.execute(
                'INSERT INTO users (user_id, email, password_hash, created_at) VALUES (?, ?, ?, ?)',
                (user_id, email, hash_pw(pw), now),
            )
    except sqlite3.IntegrityError:
        return login()  # email exists — log them in instead

    token = new_token()
    with get_db() as conn:
        conn.execute(
            'INSERT INTO sessions (token, user_id, created_at) VALUES (?, ?, ?)',
            (token, user_id, now),
        )
    print(f'[SIGNUP] {email}')
    return jsonify({'token': token, 'user': {'user_id': user_id, 'email': email}}), 201


@app.route('/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    email = (data.get('email') or '').strip().lower()
    pw = data.get('password') or ''
    with get_db() as conn:
        row = conn.execute(
            'SELECT user_id, password_hash FROM users WHERE email = ?', (email,)
        ).fetchone()

    # Auto-signup if user doesn't exist (demo-friendly)
    if not row:
        return signup()

    if row['password_hash'] != hash_pw(pw):
        return jsonify({'error': 'Wrong password'}), 401

    token = new_token()
    with get_db() as conn:
        conn.execute(
            'INSERT INTO sessions (token, user_id, created_at) VALUES (?, ?, ?)',
            (token, row['user_id'], datetime.datetime.now().isoformat()),
        )
    print(f'[LOGIN] {email}')
    return jsonify({'token': token, 'user': {'user_id': row['user_id'], 'email': email}})


@app.route('/logout', methods=['POST'])
def logout():
    token = request.headers.get('X-Parkly-Token', '')
    if token:
        with get_db() as conn:
            conn.execute('DELETE FROM sessions WHERE token = ?', (token,))
    return jsonify({'ok': True})


@app.route('/me', methods=['GET'])
@require_auth
def me(user):
    return jsonify({'user': user})


# ─── BOOKINGS ─────────────────────────────────────────────────────

@app.route('/reserve', methods=['POST'])
@require_auth
def reserve(user):
    data = request.get_json() or {}
    if not data.get('spot_name'):
        return jsonify({'error': 'Missing spot_name'}), 400

    booking_id = 'PKL-' + str(uuid.uuid4())[:6].upper()
    now = datetime.datetime.now()
    start_ms = int(data.get('start_ms') or now.timestamp() * 1000)
    duration_hrs = int(data.get('duration_hrs') or 2)
    price = float(data.get('price') or 0)

    with get_db() as conn:
        conn.execute('''
            INSERT INTO bookings
              (booking_id, user_id, spot_id, spot_name, dest, duration_hrs, price, start_ms, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'active', ?)
        ''', (
            booking_id, user['user_id'], str(data.get('spot_id', '')),
            data['spot_name'], data.get('dest', ''),
            duration_hrs, price, start_ms, now.isoformat(),
        ))

    print(f'[BOOKING] {booking_id} · {user["email"]} · {data["spot_name"]} · {duration_hrs}h · ${price}')
    return jsonify({
        'booking_id': booking_id,
        'spot_name': data['spot_name'],
        'duration_hrs': duration_hrs,
        'price': price,
        'start_ms': start_ms,
        'status': 'active',
    }), 201


@app.route('/bookings', methods=['GET'])
@require_auth
def list_bookings(user):
    now_ms = int(datetime.datetime.now().timestamp() * 1000)
    with get_db() as conn:
        # Expire anything that's past its end time
        conn.execute('''
            UPDATE bookings SET status = 'past'
            WHERE user_id = ? AND status = 'active' AND (start_ms + duration_hrs * 3600000) < ?
        ''', (user['user_id'], now_ms))
        rows = conn.execute(
            'SELECT * FROM bookings WHERE user_id = ? ORDER BY start_ms DESC',
            (user['user_id'],),
        ).fetchall()
    return jsonify([dict(r) for r in rows])


@app.route('/bookings/<booking_id>', methods=['DELETE'])
@require_auth
def cancel_booking(user, booking_id):
    with get_db() as conn:
        r = conn.execute(
            'DELETE FROM bookings WHERE booking_id = ? AND user_id = ?',
            (booking_id, user['user_id']),
        )
    if r.rowcount == 0:
        return jsonify({'error': 'Booking not found'}), 404
    print(f'[CANCELLED] {booking_id} · {user["email"]}')
    return jsonify({'message': 'Booking cancelled'})


@app.route('/bookings/<booking_id>/extend', methods=['POST'])
@require_auth
def extend_booking(user, booking_id):
    with get_db() as conn:
        row = conn.execute(
            'SELECT * FROM bookings WHERE booking_id = ? AND user_id = ?',
            (booking_id, user['user_id']),
        ).fetchone()
        if not row:
            return jsonify({'error': 'Booking not found'}), 404
        if row['status'] != 'active':
            return jsonify({'error': 'Cannot extend expired booking'}), 400
        new_duration = row['duration_hrs'] + 1
        per_hour = row['price'] / max(row['duration_hrs'], 1)
        new_price = round(row['price'] + per_hour, 2)
        conn.execute(
            'UPDATE bookings SET duration_hrs = ?, price = ? WHERE booking_id = ?',
            (new_duration, new_price, booking_id),
        )
    print(f'[EXTEND] {booking_id} · now {new_duration}h · ${new_price}')
    return jsonify({'duration_hrs': new_duration, 'price': new_price})


@app.route('/health', methods=['GET'])
def health():
    with get_db() as conn:
        users = conn.execute('SELECT COUNT(*) FROM users').fetchone()[0]
        bookings = conn.execute('SELECT COUNT(*) FROM bookings').fetchone()[0]
    return jsonify({'status': 'ok', 'users': users, 'bookings': bookings})


if __name__ == '__main__':
    init_db()
    print('▶ Parkly backend running on http://localhost:8788')
    print('  POST /signup                 — create account')
    print('  POST /login                  — sign in')
    print('  POST /reserve                — create booking (auth)')
    print('  GET  /bookings               — list my bookings (auth)')
    print('  DELETE /bookings/:id         — cancel (auth)')
    print('  POST /bookings/:id/extend    — extend 1h (auth)')
    print('  Ctrl-C to stop\n')
    port = int(os.environ.get('PORT', 8788))
    app.run(host='0.0.0.0', port=port)
