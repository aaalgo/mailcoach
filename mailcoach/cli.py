#!/usr/bin/env python3
import sys
from mailcoach import *
from mailcoach.robots import *

class User (Robot):
    def __init__ (self, address):
        super().__init__(address)

    def process (self, engine, msg, action):
        pass

def main ():
    import logging
    import pkg_resources
    import argparse

    SAMPLE_PATH = pkg_resources.resource_filename('mailcoach', 'data/sample0.mbox')
    parser = argparse.ArgumentParser(description='Process an mbox file.')
    parser.add_argument('-m', '--memory', default=SAMPLE_PATH, help='Path to the memory file')
    parser.add_argument('-q', '--queue', default=None, help='Path to the queue file')
    parser.add_argument('-u', '--user_address', default="user@localdomain", help='User address')
    parser.add_argument('-d', '--debug', action='store_true', help='Debug mode')
    parser.add_argument('-t', '--trace', default=None, help='Path to the trace file')
    args = parser.parse_args()
    
    logging.basicConfig(level=logging.INFO)

    if args.memory is None:
        ROOT = os.path.dirname(os.path.abspath(os.path.realpath(__file__)))
        MEMORY_PATH = os.path.join(ROOT, "memory.mbox")
        if os.path.exists(MEMORY_PATH):
            args.memory = MEMORY_PATH

    engine = Engine(args.trace, allow_new_agents = True)
    if args.queue is None:
        engine.register(User(args.user_address))
    engine.register(Shell("shell@localdomain"))
    if args.memory:
        engine.load_mbox(args.memory, ENQUEUE_MEMORY)
    if args.queue:
        engine.load_mbox(args.queue, ENQUEUE_TASK)
    
    engine.run()

    if args.queue is None:
        to_address = "swe1@localdomain"
        model = DEFAULT_MODEL
        engine.chat(to_address, model, debug=args.debug)
