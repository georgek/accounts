#!/usr/bin/env python

import itertools
from collections import deque, namedtuple
from curtsies import fsarray, fmtstr
from curtsies.fmtfuncs import yellow


Completion = namedtuple("Completion", ["node", "type"])


def complete(completions):
    """Returns the common prefix of given strings."""
    if len(completions) == 1:
        return completions[0].node.label
    strings = [completion.node.label for completion in completions
               if completion.type > 1]
    chars_it = itertools.takewhile(lambda chars: len(set(chars)) <= 1,
                                   zip(*strings))
    string = "".join(chars[0] for chars in chars_it)
    return string


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

    def empty(self):
        """Set the string to empty."""
        self.typed = deque()
        self.cursor = 0

    def set_string(self, string):
        """Set the string to the given string."""
        self.typed = deque(string)
        self.cursor = len(self.typed)

    def edit_string(self, key, completions):
        """Edit string and move cursor according to given key."""
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
        elif key in ["<Ctrl-b>", "<LEFT>"]:
            self.cursor = max(0, self.cursor-1)
        elif key == "<Ctrl-e>":
            self.cursor = len(self.typed)
        elif key in ["<Ctrl-f>", "<RIGHT>"]:
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
            self.cursor = self.backward_word()
        elif key == "<Esc+f>":
            self.cursor = self.forward_word()
        elif key in ["<Ctrl-BACKSPACE>", "<Esc+BACKSPACE>"]:
            p = self.backward_word()
            lst = list(self.typed)
            self.typed = deque(lst[:p] + lst[self.cursor:])
            self.killring.append(lst[p:self.cursor])
            self.cursor = p

    def find_forwards(self, char):
        """Finds next character in forward direction, or end."""
        try:
            p = list(self.typed).index(char, self.cursor+1)
            return p
        except ValueError:
            return len(self.typed)

    def find_backwards(self, char):
        """Finds next character in backward direction, or start."""
        try:
            # position of cursor in reverse list
            c = len(self.typed) - self.cursor
            p = list(reversed(self.typed)).index(char, c+1)
            return len(self.typed) - p
        except ValueError:
            return 0

    def forward_word(self):
        """Finds next position forwards of a non-alphabetic character."""
        for i in range(self.cursor+1, len(self.typed)):
            if not self.typed[i].isalpha():
                return i
        else:
            return len(self.typed)

    def backward_word(self):
        """Finds next position backwards of a non-alphabetic character."""
        for i in range(self.cursor-2, -1, -1):
            if not self.typed[i].isalpha():
                return i+1
        else:
            return 0

    def has_more_history(self):
        """Returns True if there is further history, otherwise False."""
        if len(self.history) > self.history_pos + 1:
            return True
        else:
            return False

    def to_fsarray(self, width, prompt, tail=""):
        """Returns wrapped and coloured output as an fsarray. Includes the given
prompt and tail and fits in the given width."""
        string = yellow(prompt) + fmtstr("".join(self.typed)) + tail
        chunks = [string[i:i+width] for i in range(0, len(string), width)]
        return fsarray(chunks)

    def to_string(self):
        """Returns the contents as a string."""
        return "".join(self.typed)

    def cursor_pos(self, width, prompt):
        """Gives the cursor position on the final line of the wrapped output."""
        cursor = self.cursor + len(prompt)
        return (cursor//width, cursor % width)

    def render_to(self, win, prompt="", tail=""):
        """Renders the output to the given curtsies CursorAwareWindow."""
        fsa = self.to_fsarray(win.width, prompt, tail)
        cur = self.cursor_pos(win.width, prompt)
        win.render_to_terminal(fsa, cur)
