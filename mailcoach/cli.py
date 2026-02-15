#!/usr/bin/env python3
import sys
from mailcoach import *
from mailcoach.robots import *

class User (Entity):
    def __init__ (self, address):
        super().__init__(address)

    def process (self, engine, msg, action):
        self.context.append(msg)
        pass

def main (args = None, robots=None, stop_conditions=[]):
    import logging
    import pkg_resources

    if args is None:
        import argparse

        SAMPLE_PATH = pkg_resources.resource_filename('mailcoach', 'data/sample0.mbox')
        parser = argparse.ArgumentParser(description='Process an mbox file.')
        parser.add_argument('-m', '--memory', default=SAMPLE_PATH, help='Path to the memory file, or directory')
        parser.add_argument('-q', '--queue', default=None, help='Path to the queue file')
        parser.add_argument('-u', '--user_address', default="user@localdomain", help='User address')
        parser.add_argument('-t', '--trace', default=None, help='Path to the output trace directory')
        parser.add_argument('--budget', default=None, type=float, help='Autopilot budget')
        parser.add_argument('-c', '--chat', action='store_true', help='Enter chat after processing the queue')
        parser.add_argument('--auto', action='store_true', help='Autopilot mode')
        parser.add_argument('--debug', action='store_true', help='Debug mode')
        args = parser.parse_args()
    
    logging.basicConfig(level=logging.INFO)

    if args.auto:
        assert args.budget is not None, "Budget (e.g. --budget 0.1) is required for autopilot mode."

    if args.memory is None:
        ROOT = os.path.dirname(os.path.abspath(os.path.realpath(__file__)))
        MEMORY_PATH = os.path.join(ROOT, "memory.mbox")
        if os.path.exists(MEMORY_PATH):
            args.memory = MEMORY_PATH

    if args.trace is None:
        args.trace = f"./mailcoach.{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
    os.makedirs(args.trace, exist_ok=True)
    engine = Engine(os.path.join(args.trace, 'trace'), allow_new_agents = True)
    SHELL_ADDRESS = "shell@localdomain"
    if not args.auto:
        engine.register(User(args.user_address))
    if robots is None:
        engine.register(Shell(SHELL_ADDRESS, None))
    else:
        for robot in robots:
            engine.register(robot)

    if args.memory:
        if os.path.isdir(args.memory):
            for filename in os.listdir(args.memory):
                if filename.endswith('.mbox'):
                    address = filename[:-5]  # Remove the '.mbox' extension to get the address
                    agent = engine.entities.get(address, None)
                    if agent is None:
                        agent = Agent(address)
                        engine.register(agent)

                    agent.load_mbox(os.path.join(args.memory, filename), append=False)
        else:
            engine.load_mbox(args.memory, ENQUEUE_MEMORY)

    if args.queue:
        if isinstance(args.queue, str):
            engine.load_mbox(args.queue, ENQUEUE_TASK)
        else:
            # load it as a list of messages
            for msg in args.queue:
                assert isinstance(msg, EmailMessage)
                engine.enqueue(msg, ENQUEUE_TASK)


    def check_budget (engine):
        return engine.total_cost >= args.budget
    
    if args.budget is not None:
        stop_conditions = stop_conditions + [check_budget]
    
    engine.run(stop_conditions, args.debug)

    if args.queue is None or args.chat:
        entities = set(engine.entities.keys())
        entities.remove(args.user_address)
        entities.remove(SHELL_ADDRESS)
        entities = list(entities)
        assert len(entities) > 0, "No agents found."
        to_address = entities[0]
        model = DEFAULT_MODEL
        engine.chat(to_address, model, debug=args.debug)

    for entity in engine.entities.values():
        if not hasattr(entity, 'context'):
            continue
        save_mbox(os.path.join(args.trace, f"{entity.address}.mbox"), entity.context)

