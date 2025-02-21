import os
import sys
from abc import ABC, abstractmethod
import logging
import datetime
from email import policy, message_from_bytes, message_from_string
from email.message import EmailMessage
import mailbox
import litellm

MODELS = [
    'openai/gpt-4o-mini',
    'openai/gpt-4o',
    'anthropic/claude-3-5-haiku',
    'anthropic/claude-3-5-sonnet'
]

LUNARY_PUBLIC_KEY = os.getenv("LUNARY_PUBLIC_KEY")
if not LUNARY_PUBLIC_KEY is None:
    litellm.success_callback = ["lunary"]

if sys.stdout.isatty():
    COLOR_SEP = "\033[95m"  # Magenta
    COLOR_HEADER_NAME = "\033[94m"  # Blue
    COLOR_HEADER_VALUE = "\033[92m"  # Green
    COLOR_BODY = "\033[93m"  # Yellow
    COLOR_RESET = "\033[0m"  # Reset color
else:
    COLOR_SEP = ""
    COLOR_HEADER_NAME = ""
    COLOR_HEADER_VALUE = ""
    COLOR_BODY = ""
    COLOR_RESET = ""

def print_message (msg):
    print(f"{COLOR_SEP}From {'-' * 32}")
    for k, v in msg.items():
        print(f"{COLOR_HEADER_NAME}{k}: {COLOR_HEADER_VALUE}{v}")
    print(COLOR_BODY)
    print(msg.get_content())
    print(COLOR_RESET)

def format_message_for_AI (message, serial_number):
    lines = []
    HEADERS = ["From", "To", "Subject", "Content-Type"]
    for header in HEADERS:
        value = message.get(header, "")
        if header == "Content-Type":
            value = value.split(";")[0]
        lines.append(f"{header}: {value}")
    lines.append(f"X-Serial: {serial_number}")
    lines.append("")
    try:
        content = message.get_content()
        if isinstance(content, bytes):
            content = content.decode("utf-8")
    except KeyError:
        content = ""
    lines.append(content)
    return '\n'.join(lines)

ACTION_TO = 1
ACTION_CC = 2
ACTION_SAVE_ONLY = 3

class Entity(ABC):
    def __init__ (self):
        pass

    @abstractmethod
    def process (self, engine, msg, action):
        assert False, "Not implemented"

class Robot(Entity):
    def __init__ (self):
        super().__init__()

def make_primer (agent_address):
    primer = []
    msg = EmailMessage()
    msg["From"] = "system@localdomain"
    msg["To"] = agent_address
    msg["Subject"] = "Welcome to the system!"
    msg.set_content("""
You are an agent who communicates with the outside world by emails.
Make sure you generate the emails headers correctly.""".strip())
    primer.append(msg)
    msg = EmailMessage()
    msg["From"] = agent_address
    msg["To"] = "system@localdomain"
    msg["Subject"] = "RE: Welcome to the system"
    msg.set_content("""
I'm ready to process messages.
""".strip())
    primer.append(msg)
    return primer

class Agent(Entity):
    def __init__ (self, address):
        super().__init__()
        self.address = address
        self.context = make_primer(address)
        self.model = "openai/gpt-4o-mini"

    def add (self, msg):
        # TODO: handle special messages
        self.context.append(msg)
        if 'X-Hint-Model' in msg:
            self.model = msg['X-Hint-Model']
    
    def format_context (self):
        context = []
        for serial, msg in enumerate(self.context):
            From = msg["From"].strip()
            if From == self.address:
                role = 'assistant'
            else:
                role = 'user'
            context.append({
                "role": role,
                "content": format_message_for_AI(msg, serial)
                })
        return context

    def inference (self):
        context = self.format_context()
        resp = litellm.completion(model=self.model, messages=context)
        content = resp["choices"][0]["message"]["content"]
        try:
            msg =  message_from_string(content, policy=policy.default.clone(utf8=True))
        except Exception as e:
            logging.error(f"Failed to parse response: {e}")
            logging.error(content)
            raise e
        return [msg]

    def process (self, engine, msg, action):
        self.add(msg)
        if action != ACTION_TO:
            # TODO: use a cheap model to test whether we want to reply
            return
        for msg in self.inference():
            engine.enqueue(msg)


ENQUEUE_MEMORY = 0
ENQUEUE_TASK = 1

class Engine:
    def __init__ (self):
        self.queue = []
        self.offset = 0
        self.entities = {}
        trace_path = f"./trace.{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
        self.trace = open(trace_path, "w")

    def enqueue (self, msg, mode=ENQUEUE_TASK):
        self.trace.write('\nFrom ' + '-' * 32 + '\n')
        content = msg.as_string()
        self.trace.write(content)
        if not content.endswith('\n'):
            self.trace.write('\n')
        self.trace.flush()
        self.queue.append((mode, msg))
    
    def load_mbox (self, mbox_path, mode):
        logging.info(f"Loading mbox {mbox_path}...")
        mbox = mailbox.mbox(mbox_path)
        loaded = 0
        for msg in mbox:
            msg = message_from_bytes(msg.as_bytes(), policy=policy.default.clone(utf8=True))
            assert isinstance(msg, EmailMessage)
            self.enqueue(msg, mode)
            loaded += 1
        logging.info(f"Loaded {loaded} messages (mode = {mode})")

    def save_mbox (self, mbox_path = '/dev/stdout', address = None):
        messages = self.queue
        if not address is None:
            agent = self.entities.get(address, None)
            assert isinstance(agent, Agent), "Can only save agent address."
            messages = agent.context
        with open(mbox_path, "w") as f:
            for msg in messages:
                f.write(f"From {msg['From']}\n")
                f.write(msg.as_string())
                f.write("\n")
        pass

    def register (self, address, robot):
        assert not address in self.entities
        self.entities[address] = robot

    def process (self, msg, mode):
        if mode == ENQUEUE_TASK:
            print_message(msg)
        todo = []
        if "From" in msg:
            todo.append((msg["From"].strip(), ACTION_SAVE_ONLY))
        if "To" in msg:
            for address in msg["To"].split(','):
                todo.append((address.strip(), ACTION_TO))
        if "Cc" in msg:
            for address in msg["Cc"].split(','):
                todo.append((address.strip(), ACTION_CC))
        if "Bcc" in msg:
            for address in msg["Bcc"].split(','):
                todo.append((address.strip(), ACTION_CC))
            msg0 = msg
            msg = message_from_bytes(msg.as_bytes(), policy=policy.default.clone(utf8=True))
            del msg["Bcc"]
            assert isinstance(msg, EmailMessage)
        for address, action in todo:
            is_agent = address.endswith("@agents.localdomain")
            if not address in self.entities:
                if is_agent:
                    agent = Agent(address)
                    self.entities[address] = agent
                else:
                    logging.warning(f"Unknown address {address}, message not delivered.")
                    continue
            entity = self.entities[address]
            if mode == ENQUEUE_MEMORY:
                action = ACTION_SAVE_ONLY
                if not isinstance(entity, Agent):
                    continue
            entity.process(self, msg, action)

    def run (self):
        while self.offset < len(self.queue):
            mode, msg = self.queue[self.offset]
            self.offset += 1
            self.process(msg, mode)

    def chat (self, to_address, model):
        while True:
            # get user input; \ continues to the next line
            user_input = input("ready> ")
            while user_input.endswith("\\"):
                user_input = user_input[:-1] + '\n' + input("")

            user_input = user_input.strip()
            while user_input.startswith("/"):
                fs = user_input.split(" ", 1)
                command = fs[0]
                user_input = ''
                if len(fs) > 1: 
                    user_input = fs[1].strip()
                if command.startswith("/to:"):
                    to_address = command[4:].strip()
                    print("to_address:", to_address)
                elif command.startswith("/model:"):
                    model = command[7:].strip()
                    if not model in MODELS:
                        print("\nAvailable models:")
                        for i, m in enumerate(MODELS):
                            print(f"{i+1}: {m}")
                        while True:
                            try:
                                choice = int(input("\nSelect model number: "))
                                if 1 <= choice <= len(MODELS):
                                    model = MODELS[choice-1]
                                    break
                                print("Invalid selection, please try again")
                            except ValueError:
                                print("Please enter a valid number")
                    print("model:", model)
            if len(user_input) == 0:
                continue
            if to_address is None:
                print("No to_address specified")
                continue
            message = EmailMessage()
            message["From"] = "user@localdomain"
            message["To"] = to_address
            if not model is None:
                message["X-Hint-Model"] = model
            message.set_content(user_input)
            self.enqueue(message)
            self.run()
