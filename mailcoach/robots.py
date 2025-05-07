import re
import logging
import subprocess as sp
from types import SimpleNamespace
import requests
from . import EmailMessage, Entity, ACTION_TO

def add_lines (body, filename, content, top=50, bottom=50, min_skip = 10, max_lines = 20, command = None):
    if len(content.strip()) == 0:
        return
    lines = content.split('\n')
    if command is not None:
        if ('find' in command or 'grep' in command) and len(lines) > max_lines:
            body.append(f"!!! Your command generates too many output lines.  Try to restrict the comamnd to produce less output.  If you are looking for the definition of a class or a function, try aa_find_class or aa_find_def .\n")
            return
    skip = len(lines) - top - bottom
    if skip >= min_skip:
        body.extend(lines[:top])
        body.append(f"--- {filename}: {skip} lines skipped ---")
        body.extend(lines[-bottom:])
    else:
        body.append(f"--- {filename} ---")
        body.extend(lines)

class Shell (Entity):
    def __init__(self, address, url):
        super().__init__(address)
        self.url = url

    def run_remote_command (self, command, stdin):
        response = requests.post(
            f"{self.url}/api/run",
            json={"command": command, "stdin": stdin}
        )
        resp = response.json()
        return SimpleNamespace(
            stdout = resp["stdout"],
            stderr = resp["stderr"],
            returncode = resp["returncode"]
        )
    
    def process (self, engine, msg, action):
        if action != ACTION_TO:
            return
        command = msg.get("Subject", "").strip()
        stdin = msg.get_content()
        if isinstance(stdin, bytes):
            stdin = stdin.decode("utf-8")

        if self.url is not None:
            result = self.run_remote_command(command, stdin)
        else:
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
