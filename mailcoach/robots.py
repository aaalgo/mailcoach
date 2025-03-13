import re
import logging
import subprocess as sp
from . import EmailMessage, Robot, ACTION_TO

class Shell (Robot):
    def __init__(self, address):
        super().__init__(address)
    
    def process (self, engine, msg, action):
        if action != ACTION_TO:
            return
        command = msg.get("Subject", "").strip()
        stdin = msg.get_content()
        if isinstance(stdin, bytes):
            stdin = stdin.decode("utf-8")

        if command.startswith('aa_edit '):
            split = command.split(' ')
            if len(split) > 2:
                command = ' '.join(split[:2])

        result = sp.run(command, input=stdin, shell=True, capture_output=True, text=True)
        body = []
        add_lines(body, 'stdout', result.stdout, command=command)
        add_lines(body, 'stderr', result.stderr)
        body = '\n'.join(body)
        #return result.stdout, result.stderr, result.returncode
        resp = EmailMessage()
        resp["From"] = self.address
        resp["To"] = msg["From"]
        resp["Subject"] = f"Exit Code: {result.returncode}"
        resp.set_content(body)
        engine.enqueue(resp)
