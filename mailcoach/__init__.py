import os
import sys
from abc import ABC, abstractmethod
import pickle
import logging
import datetime
from email import policy, message_from_bytes, message_from_string
from email.message import EmailMessage
import mailbox
import litellm

MODEL_PRICES = {
    #   pricing           input, cached_write, cache_read, output
    # 'openai/gpt-4.5-preview':       [75, 0.00, 0.075, 150],   This is rip-off
    'openai/gpt-4o-mini':           [0.15, 0.00, 0.075, 0.6],
    'openai/gpt-4o':                [2.50, 0.00, 1.250, 10.0],
    'anthropic/claude-3-5-haiku-latest':   [0.80, 1.00, 0.080, 4.00],
    'anthropic/claude-3-5-sonnet-latest':  [3.00, 3.75, 0.300, 15.0],
    'anthropic/claude-3-7-sonnet-20250219': [3.00, 3.75, 0.3, 15.0]
}

DEFAULT_MODEL_PRICE = [0.15, 0.00, 0.075, 0.6]

MODELS = list(MODEL_PRICES.keys())

INPUT_PRICE_INDEX = 0
OUTPUT_PRICE_INDEX = 3
PRICE_UNIT = 1000000

DEFAULT_MODEL = "openai/gpt-4o-mini"
LITELLM_API_BASE = os.getenv("LITELLM_API_BASE")

LUNARY_PUBLIC_KEY = os.getenv("LUNARY_PUBLIC_KEY")
if not LUNARY_PUBLIC_KEY is None:
    #litellm.success_callback = ["lunary"]
    pass

if sys.stdout.isatty():
    COLOR_SEP = "\033[95m"  # Magenta
    COLOR_HEADER_NAME = "\033[94m"  # Blue
    COLOR_HEADER_VALUE = "\033[92m"  # Green
    COLOR_BODY = "\033[93m"  # Yellow
    COLOR_RESET = "\033[0m"  # Reset color
    TTY_COLUMNS = os.get_terminal_size().columns
else:
    COLOR_SEP = ""
    COLOR_HEADER_NAME = ""
    COLOR_HEADER_VALUE = ""
    COLOR_BODY = ""
    COLOR_RESET = ""
    TTY_COLUMNS = None

def display_list (todo):
    if TTY_COLUMNS is None:
        for item in todo:
            print(item)
    else:
        max_width = max(len(item) for item in todo) + 2  # Adding 2 for padding
        num_columns = TTY_COLUMNS // max_width
        num_rows = (len(todo) + num_columns - 1) // num_columns

        for row in range(num_rows):
            for col in range(num_columns):
                index = row + col * num_rows
                if index < len(todo):
                    print(f"{todo[index]:<{max_width}}", end='')
            print()

def print_message (msg):
    print(f"{COLOR_SEP}From {'-' * 32}")
    for k, v in msg.items():
        print(f"{COLOR_HEADER_NAME}{k}: {COLOR_HEADER_VALUE}{v}")
    print(COLOR_BODY)
    print(msg.get_content())
    print(COLOR_RESET)

def format_message_for_AI (message, serial_number):
    lines = []
    HEADERS = ["From", "To", "Subject", "Content-Type", "X-Pop-Shell"]
    for header in HEADERS:
        if not header in message:
            continue
        value = message[header]
        if header == "Content-Type":
            value = value.split(";")[0]
        lines.append(f"{header}: {value}")
    #lines.append(f"X-Serial: {serial_number}")
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
    def __init__ (self, address):
        self.address = address
        pass

    @abstractmethod
    def process (self, engine, msg, action):
        assert False, "Not implemented"

class Robot(Entity):
    def __init__ (self, address):
        super().__init__(address)

def make_primer (agent_address):
    primer = []
    msg = EmailMessage()
    msg["From"] = "system@localdomain"
    msg["To"] = agent_address
    msg["Subject"] = "Welcome to the system!"
    msg.set_content("""
You are an agent who communicates with the outside world by emails.
Make sure you generate the emails headers correctly.
Generate only one email each time.""".strip())
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
    def __init__ (self, address, default_model = DEFAULT_MODEL):
        super().__init__(address)
        self.context = make_primer(address)
        #assert default_model in MODEL_PRICES, f"Unknown model {default_model}"
        self.default_model = default_model
        self.model = default_model
        self.total_cost = 0

    def add (self, msg):
        # TODO: handle special messages
        if 'X-Hint-Model' in msg:
            hint_model = msg['X-Hint-Model'].strip()
            if len(hint_model) == 0:
                logging.info(f"Reverting to default model {self.default_model}")
                hint_model = self.default_model
            if hint_model in MODEL_PRICES:
                self.model = hint_model
            else:
                logging.info(f"Unknown model {hint_model}, ignoring")
        if 'X-Rollback' in msg:
            rollback = int(msg['X-Rollback'])
            self.context = self.context[:(rollback+1)]
        if 'X-Pop-Shell' in msg:
            while len(self.context) > 0:
                last = self.context[-1]
                From = last['From'].strip()
                To = last['To'].strip()
                if 'shell@localdomain' in [From, To]:
                    self.context.pop()
                else:
                    break
        self.context.append(msg)
    
    def format_context (self):
        context = []
        last_role = None
        for serial, msg in enumerate(self.context):
            From = msg["From"].strip()
            if From == self.address:
                role = 'assistant'
                other = 'user'
            else:
                role = 'user'
                other = 'assistant'
            if ('gemma' in self.model) and (last_role == role):
                context.append({
                    'role': other,
                    'content': ''
                    })
            last_role = role

            context.append({
                "role": role,
                "content": format_message_for_AI(msg, serial)
                })
        return context

    def format_flat_context (self):
        context = []
        for serial, msg in enumerate(self.context):
            context.append("From --------")
            context.append(format_message_for_AI(msg, serial))
        context.append("From --------")
        return '\n'.join(context)

    def inference (self):
        if False and self.model.startswith("hosted_vllm/"):
            context = self.format_flat_context() + "\nFrom:"
            print('-'* 20)
            print(context)
            print('-'* 20)
            resp = litellm.text_completion(model=self.model, prompt=context, api_base=LITELLM_API_BASE)
            content = "From:" + resp.choices[0].text
            print('-'* 20)
            print(content)
            print('-'* 20)
        else:
            context = self.format_context()
            resp = litellm.completion(model=self.model, messages=context, api_base=LITELLM_API_BASE)
            content = resp.choices[0].message.content
        try:
            msg =  message_from_string(content, policy=policy.default.clone(utf8=True))
        except Exception as e:
            logging.error(f"Failed to parse response: {e}")
            logging.error(content)
            raise e
        msg['M-Model'] = self.model
        msg['M-Tokens-Input'] = str(resp.usage.prompt_tokens)
        msg['M-Tokens-Output'] = str(resp.usage.completion_tokens)
        prices = MODEL_PRICES.get(self.model, DEFAULT_MODEL_PRICE)
        cost = 0
        cost += prices[INPUT_PRICE_INDEX] * resp.usage.prompt_tokens / PRICE_UNIT
        cost += prices[OUTPUT_PRICE_INDEX] * resp.usage.completion_tokens / PRICE_UNIT
        msg['M-Cost'] = f"{cost:.8f}"
        self.total_cost += cost
        logging.info(f"Cost + {cost:.8f} => {self.total_cost:.8f}")
        return [msg], cost

    def process (self, engine, msg, action):
        self.add(msg)
        if action != ACTION_TO:
            # TODO: use a cheap model to test whether we want to reply
            return
        msgs, cost = self.inference()
        for msg in msgs:
            engine.enqueue(msg)
        return cost

ENQUEUE_MEMORY = 0
ENQUEUE_TASK = 1

class Engine:
    def __init__ (self, trace_path = None, allow_new_agents = False):
        self.queue = []
        self.offset = 0
        self.entities = {}
        if trace_path is None:
            trace_path = f"./mailcoach.{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
        self.trace = open(trace_path, "w")
        self.allow_new_agents = allow_new_agents
        self.total_cost = 0

    def enqueue (self, msg, mode=ENQUEUE_TASK):
        if mode == ENQUEUE_TASK:
            if 'Date' in msg:
                if len(msg['Date'].strip()) == 0:
                    del msg['Date']
            if not 'Date' in msg:
                msg['Date'] = datetime.datetime.now().strftime("%a %b %d %H:%M:%S %Y")
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

    def register (self, entity):
        assert not entity.address in self.entities
        self.entities[entity.address] = entity

    def process (self, msg, mode):
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
            is_agent = True #address.endswith("@agents.localdomain")
            if not address in self.entities:
                if is_agent and self.allow_new_agents:
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
            else:
                if isinstance(entity, Agent):
                    logging.info(f"Total cost so far: ${self.total_cost:.8f}")
            cost = entity.process(self, msg, action)
            if not cost is None:
                self.total_cost += cost


    def run (self, stop_condition = None, debug = False):
        while self.offset < len(self.queue):
            if stop_condition is not None and stop_condition(self.total_cost):
                logging.info(f"Stop condition triggered.")
                break
            mode, msg = self.queue[self.offset]
            self.offset += 1
            if mode == ENQUEUE_TASK:
                print_message(msg)
                if debug:
                    print(f"Press enter to continue...")
                    input()
            self.process(msg, mode)
        #logging.info(f"Total cost: ${self.total_cost:.8f}")

    def prompt_for_action (self):
        # Print all models, numbered by 1, 2, ...
        todo = []
        for i, model in enumerate(MODELS):
            todo.append(f"{i+1}: {model}")
        todo.append("0: [choose model...]")
        display_list(todo)
        print()

        # Print all entries in self.entities.keys(), numbered by a, b, ...
        todo = []
        for i, address in enumerate(self.entities.keys(), ord('a')):
            todo.append(f"{chr(i)}: {address}")
        todo.append("z: [choose address...]")
        display_list(todo)
        print()
        print(": [subject]")

        # Ask the user to choose an item with input
        choice = input("? ").strip()

        # If the user inputs a number, return a tuple ('model', chosen model)
        if choice.isdigit():
            index = int(choice)
            if index == 0:
                model = input("Enter model: ")
                return ('model', model)
            if 1 <= index <= len(MODELS):
                return ('model', MODELS[index-1])
            else:
                print("Invalid model number.")
                return None
        # If the user inputs a letter, return ('to', chosen address)
        elif len(choice) == 1 and 'a' <= choice <= chr(ord('a') + len(self.entities) - 1):
            index = ord(choice) - ord('a')
            address = list(self.entities.keys())[index]
            return ('to', address)
        elif choice == 'z':
            address = input("Enter address: ")
            return ('to', address)
        elif choice.startswith(":"):
            subject = choice[1:].strip()
            return ('subject', subject)
        else:
            print("Invalid choice.")
            return None

    def chat (self, to_address, model, user_address = "user@localdomain", debug = False):
        subject = ''
        while True:
            # get user input; \ continues to the next line
            print(f"To:\033[94m{to_address}\033[0m Subject:\033[92m{subject}\033[0m Model:\033[93m{model}\033[0m")
            user_input = input(f"> ")
            while user_input.endswith("\\"):
                user_input = user_input[:-1] + '\n' + input("")
            user_input = user_input.strip()
            if len(user_input) == 0:
                resp = self.prompt_for_action()
                if resp is None:
                    continue
                action, param = resp
                if action == 'model':
                    model = param
                    logging.info(f"Model set to {model}")
                elif action == 'to':
                    to_address = param
                    logging.info(f"To address set to: {to_address}")
                elif action == 'subject':
                    subject = param
                    logging.info(f"Subject set to: {subject}")
                else:
                    logging.error(f"Invalid action: {action} {param}")
                continue
            if to_address is None:
                print("No to_address specified")
                continue
            message = EmailMessage()
            message["From"] = user_address
            message["To"] = to_address
            message["Subject"] = subject
            subject = ''
            if not model is None:
                message["X-Hint-Model"] = model
            message.set_content(user_input)
            self.enqueue(message)
            self.run(debug=debug)
