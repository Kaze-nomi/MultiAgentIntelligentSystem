#!/usr/bin/env python3
"""
Black Hole Agent Server

This module implements a simple server for the Black Hole Agent, which simulates a 'black hole'
by accepting requests and processing them in a way that 'absorbs' or discards the input,
returning a minimal response. It's designed to demonstrate a basic agent architecture.

The server uses Flask for handling HTTP requests and provides endpoints for health checks
and processing tasks.
"""

import logging
from flask import Flask, request, jsonify
from werkzeug.exceptions import BadRequest

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

@app.route('/health', methods=['GET'])
"""Health check endpoint.

Returns a simple JSON response indicating the service is healthy.
"""
def health_check():
    return jsonify({'status': 'healthy'}), 200

@app.route('/process', methods=['POST'])
"""Process task endpoint.

Accepts a JSON payload with a 'task' field, simulates processing by logging the task,
and returns a response indicating the task was 'absorbed'.

Raises:
    BadRequest: If the request is malformed or missing required fields.
"""
def process_task():
    try:
        data = request.get_json()
        if not data or 'task' not in data:
            raise BadRequest('Invalid request: missing task field')

        task = data['task']
        logger.info(f'Black Hole Agent absorbing task: {task}')

        # Simulate absorption: do nothing with the task
        return jsonify({'message': 'Task absorbed by black hole', 'status': 'success'}), 200
    except BadRequest as e:
        logger.error(f'Bad request: {str(e)}')
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f'Unexpected error: {str(e)}')
        return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5003, debug=False)
