#!/usr/bin/env python3
"""
Parkly backend — handles parking reservations.
Run: python backend.py  (starts on http://localhost:8788)
Bookings are saved to parkly.db (SQLite file) — persists between restarts.
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import uuid
import datetime
import os

app = Flask(__name__)
CORS(app)

DB_FILE = 'parkly.db'


def get_db():
    """Open a connection to the database."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row  # lets us access columns by name, not just index
    return conn


def init_db():
    """Create the bookings table if it doesn't exist yet."""
    with get_db() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS bookings (
                booking_id  TEXT PRIMARY KEY,
                spot_id     INTEGER,
                spot_name   TEXT,
                name        TEXT,
                hour        INTEGER,
                dest        TEXT,
                price       TEXT,
                created_at  TEXT
            )
        ''')
    print('  Database ready → parkly.db')


@app.route('/reserve', methods=['POST'])
def reserve():
    data = request.get_json()

    required = ['spot_id', 'spot_name', 'name', 'hour']
    for field in required:
        if not data.get(field):
            return jsonify({'error': f'Missing field: {field}'}), 400

    booking_id = 'PKL-' + str(uuid.uuid4())[:6].upper()
    created_at = datetime.datetime.now().isoformat()

    with get_db() as conn:
        conn.execute('''
            INSERT INTO bookings (booking_id, spot_id, spot_name, name, hour, dest, price, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            booking_id,
            data['spot_id'],
            data['spot_name'],
            data['name'],
            data['hour'],
            data.get('dest', ''),
            data.get('price', ''),
            created_at,
        ))

    booking = {
        'booking_id': booking_id,
        'spot_id': data['spot_id'],
        'spot_name': data['spot_name'],
        'name': data['name'],
        'hour': data['hour'],
        'dest': data.get('dest', ''),
        'price': data.get('price', ''),
        'created_at': created_at,
    }
    print(f'[NEW BOOKING] {booking_id} — {data["name"]} → {data["spot_name"]}')
    return jsonify(booking), 201


@app.route('/bookings', methods=['GET'])
def list_bookings():
    with get_db() as conn:
        rows = conn.execute('SELECT * FROM bookings ORDER BY created_at DESC').fetchall()
    return jsonify([dict(row) for row in rows])


@app.route('/bookings/<booking_id>', methods=['GET'])
def get_booking(booking_id):
    with get_db() as conn:
        row = conn.execute('SELECT * FROM bookings WHERE booking_id = ?', (booking_id,)).fetchone()
    if not row:
        return jsonify({'error': 'Booking not found'}), 404
    return jsonify(dict(row))


@app.route('/bookings/<booking_id>', methods=['DELETE'])
def cancel_booking(booking_id):
    with get_db() as conn:
        result = conn.execute('DELETE FROM bookings WHERE booking_id = ?', (booking_id,))
    if result.rowcount == 0:
        return jsonify({'error': 'Booking not found'}), 404
    print(f'[CANCELLED] {booking_id}')
    return jsonify({'message': 'Booking cancelled'})


@app.route('/health', methods=['GET'])
def health():
    with get_db() as conn:
        count = conn.execute('SELECT COUNT(*) FROM bookings').fetchone()[0]
    return jsonify({'status': 'ok', 'bookings': count})


if __name__ == '__main__':
    init_db()
    print('▶ Parkly backend running on http://localhost:8788')
    print('  POST /reserve        — create a booking')
    print('  GET  /bookings       — list all bookings')
    print('  GET  /bookings/:id   — get one booking')
    print('  DELETE /bookings/:id — cancel booking')
    print('  Ctrl-C to stop\n')
    port = int(os.environ.get('PORT', 8788))
    app.run(host='0.0.0.0', port=port)
