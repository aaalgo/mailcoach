from abc import ABC, abstractmethod
import logging
from email import policy, message_from_bytes, message_from_string
from email.message import EmailMessage
import mailbox
from litellm import completion

def format_message_for_AI (message, serial_number):
    lines = []
    HEADERS = ["From", "To", "Subject", "Content-Type"]
    for header in HEADERS:
        value = message.get(header, "")
        lines.append(f"{header}: {value}")
    lines.append(f"X-Serial: {serial_number}")
    lines.append("")
    content = message.get_content()
    if isinstance(content, bytes):
        content = content.decode("utf-8")
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

class Agent(Entity):
    def __init__ (self, address):
        super().__init__()
        self.address = address
        self.context = []
        self.model = "openai/gpt-4o"

    def add (self, msg):
        # TODO: handle special messages
        self.context.append(msg)
    
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
        resp = completion(model=self.model, messages=context)
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

class Engine:
    def __init__ (self, mbox_path = None):
        self.queue = []
        self.offset = 0
        self.entities = {}
        if mbox_path:
            logging.info(f"Loading mbox {mbox_path}")
            mbox = mailbox.mbox(mbox_path)
            for msg in mbox:
                print(msg["From"])
                self.queue.append(msg)
                self.process(msg, True)
            self.offset = len(self.queue)
            logging.info(f"Loaded {len(self.queue)} messages")

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

    def add_robot (self, address, robot):
        assert not address in self.entities
        self.entities[address] = robot

    def enqueue (self, message):
        self.queue.append(message)

    def process (self, msg, init = False):
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
        if not isinstance(msg, EmailMessage):
            print(type(msg0), type(msg))
            assert False
        for address, action in todo:
            is_agent = address.endswith("agents.localdomain")
            if not address in self.entities:
                if is_agent:
                    self.entities[address] = Agent(address)
                    # handle copy
                else:
                    logging.warning(f"Unknown address {address}, message not delivered.")
                    continue
            entity = self.entities[address]
            if init:
                action = ACTION_SAVE_ONLY
                if not isinstance(entity, Agent):
                    continue
            entity.process(self, msg, action)

    def run (self):
        while self.offset < len(self.queue):
            msg = self.queue[self.offset]
            self.offset += 1
            self.process(msg)

