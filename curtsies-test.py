#!/usr/bin/env python

import argparse

from collections import deque

from hierarchy import StringHierarchy
from pydo import pydo_input

HISTORY_SIZE = 10


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("strings_file", type=argparse.FileType("r"))
    return parser.parse_args()


def main(strings_file):
    history = deque([], HISTORY_SIZE)
    # dir_contents = [str(p) for p in Path(".").iterdir()]
    # hierarchy = DirectoryHierarchy(".")
    # hierarchy = StringHierarchy(["a/b/c", "a/b/c/2", "a/b/c1", "a/d/2"],
    #                             separator="/")
    names = [line.strip() for line in strings_file]
    hierarchy = StringHierarchy(names, separator=":")
    while True:
        typed = pydo_input(hierarchy,
                           prompt="Input: ",
                           forbidden=[" "],
                           history=history)
        if typed:
            if len(history) == 0 or typed != history[0]:
                history.appendleft(typed)
            print(typed)
        else:
            return


if __name__ == '__main__':
    args = get_args()
    main(**vars(args))
