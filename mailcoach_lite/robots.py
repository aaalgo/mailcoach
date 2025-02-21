import subprocess as sp
from . import EmailMessage, Robot, ACTION_TO

def add_lines (body, filename, content, top=8, bottom=8, min_skip = 4):
    content = content.strip()
    if len(content) == 0:
        return
    lines = content.split('\n')
    skip = len(lines) - top - bottom
    if skip >= min_skip:
        body.append(f"--- {filename}: top ---")
        body.extend(lines[:top])
        body.append(f"--- {filename}: {skip} lines skipped ---")
        body.extend(lines[-bottom:])
    else:
        body.append(f"--- {filename} ---")
        body.extend(lines)

class Shell (Robot):
    def __init__(self, address):
        super().__init__(address)
    
    def process (self, engine, msg, action):
        if action != ACTION_TO:
            return
        command = msg.get("Subject", "")
        stdin = msg.get_content()
        if isinstance(stdin, bytes):
            stdin = stdin.decode("utf-8")

        result = sp.run(command, input=stdin, shell=True, capture_output=True, text=True)
        body = []
        add_lines(body, 'stdout', result.stdout)
        add_lines(body, 'stderr', result.stderr)
        body = '\n'.join(body)
        #return result.stdout, result.stderr, result.returncode
        resp = EmailMessage()
        resp["From"] = self.address
        resp["To"] = msg["From"]
        resp["Subject"] = f"Exit Code: {result.returncode}"
        resp.set_content(body)
        engine.enqueue(resp)
