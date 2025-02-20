#!/usr/bin/env python3
import argparse
from mailcoach_lite import Engine


def main ():
    parser = argparse.ArgumentParser(description='Process an mbox file.')
    parser.add_argument('-m', '--mbox', default=None, help='Path to the mbox file')
    args = parser.parse_args()

    engine = Engine(args.mbox)
    engine.save_mbox("/dev/stdout")

if __name__ == "__main__":
    main()
