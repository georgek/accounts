#!/usr/bin/env python

import itertools
from collections import deque

from curtsies import Input, CursorAwareWindow, fsarray

HISTORY_SIZE = 10


class Editor():
    def __init__(self,
                 forbidden=[],
                 initial_string="",
                 history=[],
                 killring_size=5):
        self.typed = deque(initial_string)
        self.cursor = len(self.typed)
        self.forbidden = forbidden
        self.killring = deque([], killring_size)
        self.history = history
        self.history_pos = -1
        self.new_history = None

    def edit_string(self, key, completions):
        """Edit string and move cursor according to given key.  Return new string and
    cursor.
        """
        if self.cursor > len(self.typed):
            self.cursor = len(self.typed)
        if len(key) == 1:
            if key not in self.forbidden:
                self.typed.insert(self.cursor, key)
                self.cursor += 1
        elif key == "<SPACE>":
            if " " not in self.forbidden:
                self.typed.insert(self.cursor, " ")
                self.cursor += 1
        elif key == "<TAB>":
            if self.cursor == len(self.typed):
                completed = complete(completions)
                if completed:
                    self.typed = deque(completed)
                    self.cursor = len(self.typed)
        elif key == "<Ctrl-a>":
            self.cursor = 0
        elif key == "<Ctrl-b>":
            self.cursor = max(0, self.cursor-1)
        elif key == "<Ctrl-e>":
            self.cursor = len(self.typed)
        elif key == "<Ctrl-f>":
            self.cursor = min(len(self.typed), self.cursor+1)
        elif key in ["<Ctrl-h>", "<BACKSPACE>"]:
            if self.cursor > 0:
                del self.typed[self.cursor-1]
                self.cursor -= 1
        elif key == "<Ctrl-k>":
            lst = list(self.typed)
            self.typed = deque(lst[:self.cursor])
            self.killring.append(lst[self.cursor:])
        elif key == "<Ctrl-l>":
            self.typed.clear()
            self.cursor = 0
        elif key in ["<Ctrl-n>", "<DOWN>"]:
            if self.history_pos > 0:
                self.history_pos -= 1
                self.typed = deque(self.history[self.history_pos])
                self.cursor = len(self.typed)
            elif self.history_pos == 0:
                self.history_pos -= 1
                self.typed = self.new_history
                self.cursor = len(self.typed)
        elif key in ["<Ctrl-p>", "<UP>"]:
            if len(self.history) > self.history_pos + 1:
                if self.history_pos == -1:
                    self.new_history = self.typed
                self.history_pos += 1
                self.typed = deque(self.history[self.history_pos])
                self.cursor = len(self.typed)
        elif key == "<Ctrl-y>":
            lst = list(self.typed)
            yanked = self.killring[-1]
            self.typed = deque(lst[:self.cursor] + yanked + lst[self.cursor:])
            self.cursor += len(yanked)
        elif key == "<Esc+b>":
            self.cursor = self.find_backwards(" ")
        elif key == "<Esc+f>":
            self.cursor = self.find_forwards(" ")
        elif key in ["<Ctrl-BACKSPACE>", "<Esc+BACKSPACE>"]:
            p = self.find_backwards(" ")
            lst = list(self.typed)
            self.typed = deque(lst[:p] + lst[self.cursor:])
            self.killring.append(lst[p:self.cursor])
            self.cursor = p

    def find_forwards(self, char):
        try:
            p = list(self.typed).index(char, self.cursor+1)
            return p
        except ValueError:
            return len(self.typed)

    def find_backwards(self, char):
        try:
            # position of cursor in reverse list
            c = len(self.typed) - self.cursor
            p = list(reversed(self.typed)).index(char, c+1)
            return len(self.typed) - p
        except ValueError:
            return 0

    def to_fsarray(self, width, prompt, tail=""):
        string = prompt + "".join(self.typed) + tail
        chunks = [string[i:i+width] for i in range(0, len(string), width)]
        return fsarray(chunks)

    def to_string(self):
        return "".join(self.typed)

    def cursor_pos(self, width, prompt):
        cursor = self.cursor + len(prompt)
        return (cursor//width, cursor % width)

    def render_to(self, win, prompt="", tail=""):
        fsa = self.to_fsarray(win.width, prompt, tail)
        cur = self.cursor_pos(win.width, prompt)
        win.render_to_terminal(fsa, cur)


def narrow(typed, completions):
    """Returns narrowed list of completions based on typed."""
    completions = sorted(s for s in completions if s.startswith(typed))
    return completions


def complete(strings):
    """Returns the common prefix of given strings."""
    it_tw = itertools.takewhile(lambda t: len(set(t)) <= 1,
                                zip(*strings))
    string = "".join(t[0] for t in it_tw)
    return string


def completion_string(completions):
    string = ", ".join(completions)
    return f" <{string}>"


def get_input(prompt="", completions=[], separator="/",
              forbidden=[], history=[]):
    with CursorAwareWindow(hide_cursor=False) as win:
        with Input(keynames="curtsies") as input_generator:
            editor = Editor(initial_string="",
                            forbidden=forbidden,
                            history=history)
            current_completions = narrow("", completions)
            editor.render_to(win, prompt,
                             completion_string(current_completions))
            try:
                for key in input_generator:
                    if key == "<Ctrl-d>":
                        return None
                    elif key == "<Ctrl-j>":
                        win.render_to_terminal([])
                        return "".join(editor.typed)
                    else:
                        editor.edit_string(key, current_completions)
                        current_completions = narrow(editor.to_string(),
                                                     completions)
                    editor.render_to(win, prompt,
                                     completion_string(current_completions))
            except KeyboardInterrupt:
                return None


def main():
    history = deque([], HISTORY_SIZE)
    while True:
        typed = get_input(prompt="Input: ",
                          completions=["this", "that", "account", "name"],
                          separator="/",
                          forbidden=[" "],
                          history=history)
        if typed:
            history.appendleft(typed)
            print(typed)
        else:
            return


if __name__ == '__main__':
    main()
