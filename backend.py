#!/usr/bin/env python3
"""
Parkly backend — handles parking reservations.
Run: python backend.py  (starts on http://localhost:8788)
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import uuid
import datetime

app = Flask(__name__)
CORS(app)

# In-memory store — resets when server restarts (fine for demo)
bookings = {}

@app.route('/reserve', methods=['POST'])
def reserve():
    data = request.get_json()

    required = ['spot_id', 'spot_name', 'name', 'hour']
    for field in required:
        if not data.get(field):
            return jsonify({'error': f'Missing field: {field}'}), 400

    booking_id = 'PKL-' + str(uuid.uuid4())[:6].upper()
    booking = {
        'booking_id': booking_id,
        'spot_id': data['spot_id'],
        'spot_name': data['spot_name'],
        'name': data['name'],
        'hour': data['hour'],
        'dest': data.get('dest', ''),
        'price': data.get('price', ''),
        'created_at': datetime.datetime.now().isoformat(),
    }
    bookings[booking_id] = booking
    print(f'[NEW BOOKING] {booking_id} — {data["name"]} → {data["spot_name"]}')
    return jsonify(booking), 201


@app.route('/bookings', methods=['GET'])
def list_bookings():
    return jsonify(list(bookings.values()))


@app.route('/bookings/<booking_id>', methods=['GET'])
def get_booking(booking_id):
    booking = bookings.get(booking_id)
    if not booking:
        return jsonify({'error': 'Booking not found'}), 404
    return jsonify(booking)


@app.route('/bookings/<booking_id>', methods=['DELETE'])
def cancel_booking(booking_id):
    if booking_id not in bookings:
        return jsonify({'error': 'Booking not found'}), 404
    del bookings[booking_id]
    print(f'[CANCELLED] {booking_id}')
    return jsonify({'message': 'Booking cancelled'})


@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'bookings': len(bookings)})


if __name__ == '__main__':
    print('▶ Parkly backend running on http://localhost:8788')
    print('  POST /reserve      — create a booking')
    print('  GET  /bookings     — list all bookings')
    print('  GET  /bookings/:id — get one booking')
    print('  DELETE /bookings/:id — cancel booking')
    print('  Ctrl-C to stop\n')
    app.run(port=8788, debug=True)
