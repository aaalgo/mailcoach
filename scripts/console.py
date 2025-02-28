#!/usr/bin/env python3
import sys
import argparse
from mailcoach_lite import *
from mailcoach_lite.robots import *

class User (Robot):
    def __init__ (self, address):
        super().__init__(address)

    def process (self, engine, msg, action):
        pass

def main ():
    parser = argparse.ArgumentParser(description='Process an mbox file.')
    parser.add_argument('-m', '--memory', default=None, help='Path to the memory file')
    parser.add_argument('-q', '--queue', default=None, help='Path to the queue file')
    parser.add_argument('-c', '--chat', action='store_true', help='Chat mode')
    parser.add_argument('-u', '--user_address', default="user@localdomain", help='User address')
    args = parser.parse_args()

    if args.memory is None:
        ROOT = os.path.dirname(os.path.abspath(os.path.realpath(__file__)))
        MEMORY_PATH = os.path.join(ROOT, "memory.mbox")
        if os.path.exists(MEMORY_PATH):
            args.memory = MEMORY_PATH

    engine = Engine(allow_new_agents = True)
    engine.register(User(args.user_address))
    engine.register(Shell("shell@localdomain"))
    engine.register(Editor("editor@localdomain"))
    if args.memory:
        engine.load_mbox(args.memory, ENQUEUE_MEMORY)
    if args.queue:
        engine.load_mbox(args.queue, ENQUEUE_TASK)
    engine.run()

    if args.chat:
        to_address = "swe1@agents.localdomain"
        model = DEFAULT_MODEL
        engine.chat(to_address, model)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logging.info("Mailcoach Lite Console")
    main()

