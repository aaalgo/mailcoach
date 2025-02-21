#!/usr/bin/env python3
import sys
import argparse
from mailcoach_lite import *

class User (Robot):
    def __init__ (self):
        super().__init__()

    def process (self, engine, msg, action):
        pass

def main ():
    parser = argparse.ArgumentParser(description='Process an mbox file.')
    parser.add_argument('-m', '--memory', default=None, help='Path to the memory file')
    parser.add_argument('-q', '--queue', default=None, help='Path to the queue file')
    parser.add_argument('-c', '--chat', action='store_true', help='Chat mode')
    args = parser.parse_args()

    engine = Engine()
    engine.register("user@localdomain", User())
    if args.memory:
        engine.load_mbox(args.memory, ENQUEUE_MEMORY)
    if args.queue:
        engine.load_mbox(args.queue, ENQUEUE_TASK)
    engine.run()

    if args.chat:
        to_address = "a100@agents.localdomain"
        model = 'openai/gpt-4o-mini'
        engine.chat(to_address, model)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logging.info("Mailcoach Lite Console")
    main()

