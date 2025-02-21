import re
import logging
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


class Editor (Robot):
    def __init__(self, address):
        super().__init__(address)
        self.path = None
        self.cursor = None
        self.lines = None
        self.stdout = []

    def print_window (self, line = None, window=10, suffix=True, star=None):
        if line is None:
            line = self.cursor
        l = line - 1
        begin = max(0, l)
        end = min(len(self.lines), l + window)
        to_append = []
        leading_width = 0
        for i in range(begin, end):
            leading = '*' if i + 1 == star else ''
            to_append.append((leading + str(i+1), self.lines[i].rstrip()))
            leading_width = max(leading_width, len(to_append[-1][0]))
        for leading, line in to_append:
            self.stdout.append(f'{leading:>{leading_width}}  {line}')

        remain = len(self.lines) - end
        if remain > 0 and suffix:
            self.stdout.append('')
            self.stdout.append(f'{len(self.lines) - end} more lines below.')

    def open (self, msg, path):
        with open(path, "r") as f:
            self.lines = f.readlines()
        self.path = path
        self.stdout.append(f"File has {len(self.lines)} lines.")

    def goto (self, msg, line):
        line = int(line)
        self.cursor = line
        self.print_window()

    def replace (self, msg, range):
        begin, end = range.split('-')
        begin = int(begin)-1
        end = int(end)
        body = msg.get_content()
        top = self.lines[:begin]
        bottom = self.lines[end:]
        with open(self.path, "w") as f:
            f.writelines(top)
            f.write(body)
            f.writelines(bottom)
        with open(self.path, "r") as f:
            self.lines = f.readlines()
        self.stdout.append(f"{end-begin} lines replaced.")

    def search(self, msg, pattern):
        logging.info(f"Searching for pattern: {pattern}")
        regex = re.compile(pattern)
        found = []
        for i, line in enumerate(self.lines):
            if regex.search(line):
                found.append(i+1)
        max_found = 5
        if len(found) > max_found:
            self.stdout.append(f"Found {len(found)} matches, showing first {max_found}.")
            self.stdout.append('')
            found = found[:max_found]
        for i in found:
            self.print_window(i-2, window=5, suffix=False, star=i)
            self.stdout.append('')
    
    def process (self, engine, msg, action):
        if action != ACTION_TO:
            return
        command = msg.get("Subject", "").strip()
        self.stdout = []
        self.status = 'ok'
        fs = [f.strip() for f in command.split(' ') if f.strip()]
        if len(fs) == 0:
            self.status = 'bad command'
        else:
            cmd = fs[0]
            args = fs[1:]
            if hasattr(self, cmd):
                method = getattr(self, cmd)
                if callable(method):
                    method(msg, *args)
                else:
                    self.status(f'Error: {cmd} is not callable')
            else:
                self.status(f'Error: unknown command {cmd}')
        resp = EmailMessage()
        resp["From"] = self.address
        resp["To"] = msg["From"]
        resp["Subject"] = self.status
        resp.set_content('\n'.join(self.stdout))
        engine.enqueue(resp)
