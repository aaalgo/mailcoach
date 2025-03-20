#!/usr/bin/env python3
import traceback
from flask import Flask, request, jsonify
import subprocess
import argparse
import sys
import threading
import time

app = Flask(__name__)

@app.route('/api/run', methods=['POST'])
def run_command():
    try:
        data = request.get_json()
        command = data.get('command')
        stdin = data.get('stdin')

        # Run the command
        process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE if stdin else None,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            shell=True
        )
        # Send stdin if provided
        stdout, stderr = process.communicate(input=stdin)

        return jsonify({
            'returncode': process.returncode,
            'stdout': stdout,
            'stderr': stderr
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8642)
    args = parser.parse_args()
    
    # Run Flask without the reloader to allow clean shutdown
    app.run(host='0.0.0.0', port=args.port, use_reloader=False)

if __name__ == "__main__":
    main()
