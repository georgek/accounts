#!/usr/bin/env python

# import sys
import argparse

from hierarchy import StringHierarchy
# from hierarchy import DirectoryHierarchy

# from pathlib import Path
import itertools
from collections import deque, namedtuple

from curtsies import Input, CursorAwareWindow, fsarray, fmtstr
from curtsies.fmtfuncs import yellow, bold

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

    def empty(self):
        self.typed = deque()
        self.cursor = 0

    def set_string(self, string):
        self.typed = deque(string)
        self.cursor = len(self.typed)

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
        if len(self.history) > self.history_pos + 1:
            return True
        else:
            return False

    def to_fsarray(self, width, prompt, tail=""):
        string = yellow(prompt) + fmtstr("".join(self.typed)) + tail
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


Completion = namedtuple("Completion", ["node", "type"])


def fuzzy_sort_type(typed, candidate):
    """Returns the type of the match as a CompletionType."""
    typed, candidate = typed.lower(), candidate.lower()
    if typed == candidate:
        return 3                # exact
    elif candidate.startswith(typed):
        return 2                # prefix
    elif typed in candidate:
        return 1                # fuzzy
    else:
        return 0                # no match


def narrow_completions(typed, nodes):
    """Makes Completions from given Nodes according to typed."""
    completions = (Completion(node, fuzzy_sort_type(typed, node.label))
                   for node in nodes)

    def sort_key(completion):
        return (-completion.type, completion.node.label)

    return sorted((completion for completion in completions
                   if completion.type > 0),
                  key=sort_key)


def complete(completions):
    """Returns the common prefix of given strings."""
    strings = [completion.node.label for completion in completions
               if completion.type > 1]
    chars_it = itertools.takewhile(lambda chars: len(set(chars)) <= 1,
                                   zip(*strings))
    string = "".join(chars[0] for chars in chars_it)
    return string


def pathstring(path, separator):
    return separator.join(path)


def prompt_string(prompt, path, separator):
    pstr = pathstring(path, separator)
    if pstr:
        return f"{prompt}{pstr}{separator}"
    else:
        return prompt


def completion_string(completions, separator="", current=0):
    completions = [fmtstr(t.node.label+separator) if t.node.internal
                   else fmtstr(t.node.label)
                   for t in completions]
    if current < len(completions):
        completions[current] = yellow(bold(completions[current]))
    string = fmtstr(" | ").join(completions)
    return fmtstr("{") + string + fmtstr("}")


def get_input(completion_tree, prompt="", forbidden=[], history=[]):
    separator = completion_tree.separator
    with CursorAwareWindow(hide_cursor=False) as win, \
         Input(keynames="curtsies",
               disable_terminal_start_stop=True) as input_generator:
        editor = Editor(initial_string="",
                        forbidden=forbidden,
                        history=history)
        current_path = []
        nodes = completion_tree.get_subtree(current_path)
        # current_completions = narrow("", completions)
        narrowed_completions = narrow_completions("", nodes)
        completion_selected = 0
        editor.render_to(win,
                         prompt_string(prompt, current_path,
                                       separator),
                         completion_string(narrowed_completions,
                                           separator,
                                           completion_selected))
        try:
            for key in input_generator:
                if key == "<Ctrl-d>":
                    # EOF
                    return None
                elif key == "<Ctrl-j>" and narrowed_completions:
                    # Completing Enter
                    selected_node = narrowed_completions[completion_selected].node
                    if selected_node.internal:
                        current_path.append(selected_node.label)
                        nodes = completion_tree.get_subtree(current_path)
                        narrowed_completions = narrow_completions("", nodes)
                        completion_selected = 0
                        editor.empty()
                    else:
                        win.render_to_terminal([])
                        pstr = pathstring(current_path, separator)
                        if pstr:
                            return f"{pstr}{separator}{selected_node.label}"
                        else:
                            return selected_node.label
                elif key == "<Esc+j>" or key == "<Ctrl-j>":
                    # Immediate Enter
                    pstr = pathstring(current_path, separator)
                    if pstr:
                        return f"{pstr}{separator}{editor.to_string()}"
                    else:
                        return editor.to_string()
                elif key in ["<Ctrl-h>", "<BACKSPACE>"]:
                    if len(editor.to_string()) == 0 and current_path:
                        current_path.pop()
                        nodes = completion_tree.get_subtree(current_path)
                        narrowed_completions = narrow_completions("", nodes)
                        completion_selected = 0
                    else:
                        editor.edit_string(key, narrowed_completions)
                        narrowed_completions = narrow_completions(
                            editor.to_string(), nodes)
                        completion_selected = 0
                elif key == "<Ctrl-n>" \
                     or (key == "<Ctrl-p>" and editor.has_more_history()):
                    editor.edit_string(key, narrowed_completions)
                    recalled_path = editor.to_string().split(separator)
                    current_path, rest_path = completion_tree.get_partial_path(
                        recalled_path)
                    rest = separator.join(rest_path)
                    editor.set_string(rest)
                    nodes = completion_tree.get_subtree(current_path)
                    narrowed_completions = narrow_completions(
                        editor.to_string(), nodes)
                    completion_selected = 0
                elif key == "<Ctrl-s>":
                    completion_selected = ((completion_selected+1)
                                           % len(narrowed_completions))
                elif key == "<Ctrl-r>":
                    completion_selected = ((completion_selected-1)
                                           % len(narrowed_completions))
                else:
                    editor.edit_string(key, narrowed_completions)
                    narrowed_completions = narrow_completions(editor.to_string(),
                                                              nodes)
                    completion_selected = 0
                # we could have a single completed string here, if it's an
                # internal node then go to the next level
                if len(narrowed_completions) == 1:
                    completion = narrowed_completions[0]
                    if completion.node.label == editor.to_string() \
                       and completion.node.internal:
                        current_path.append(completion.node.label)
                        nodes = completion_tree.get_subtree(current_path)
                        narrowed_completions = narrow_completions("", nodes)
                        completion_selected = 0
                        editor.empty()
                editor.render_to(win,
                                 prompt_string(prompt, current_path,
                                               separator),
                                 completion_string(narrowed_completions,
                                                   separator,
                                                   completion_selected))
        except KeyboardInterrupt:
            return None


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
        typed = get_input(hierarchy,
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
