#!/usr/bin/env python

from curtsies import Input, CursorAwareWindow, fmtstr
from curtsies.fmtfuncs import yellow, bold

from editor import Editor, Completion


def narrow_completions(typed, nodes):
    """Makes Completions from given Nodes according to typed."""
    completions = (Completion(node, fuzzy_sort_type(typed, node.label))
                   for node in nodes)

    def sort_key(completion):
        return (-completion.type, completion.node.label)

    return sorted((completion for completion in completions
                   if completion.type > 0),
                  key=sort_key)


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
    return fmtstr(" {") + string + fmtstr("}")


def pydo_input(completion_tree, prompt="", initial_string="",
               forbidden=[], history=[]):
    separator = completion_tree.separator
    with CursorAwareWindow(hide_cursor=False) as win, \
         Input(keynames="curtsies",
               disable_terminal_start_stop=True) as input_generator:
        editor = Editor(initial_string=initial_string,
                        forbidden=forbidden,
                        history=history)
        current_path = []
        nodes = completion_tree.get_subtree(current_path)
        narrowed_completions = narrow_completions(initial_string, nodes)
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
                elif key in ["<Esc+j>", "<Ctrl-j>"]:
                    # Immediate Enter
                    pstr = pathstring(current_path, separator)
                    if pstr:
                        return f"{pstr}{separator}{editor.to_string()}"
                    else:
                        return editor.to_string()
                elif key == separator:
                    # we might need to to go the next level
                    if narrowed_completions and narrowed_completions[0].type == 3:
                        # just remove other completions to pick it up later
                        narrowed_completions = narrowed_completions[0:1]
                    else:
                        editor.edit_string(key, narrowed_completions)
                        narrowed_completions = narrow_completions(
                            editor.to_string(), nodes)
                        completion_selected = 0
                elif key in ["<Ctrl-h>", "<BACKSPACE>",
                             "<Ctrl-BACKSPACE>", "<Esc+BACKSPACE>"]:
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
                elif (key == "<Ctrl-n>"
                      or (key == "<Ctrl-p>" and editor.has_more_history())):
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
