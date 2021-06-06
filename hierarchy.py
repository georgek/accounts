#!/usr/bin/env python

from abc import ABCMeta, abstractmethod
from pathlib import Path
from collections import namedtuple, deque


Node = namedtuple("Node", ["label", "internal"])


class Hierarchy(metaclass=ABCMeta):
    @property
    def separator(self):
        return self._separator

    @abstractmethod
    def get_subtree(self, path=[]):
        """Returns subtree at given path."""
        pass

    @abstractmethod
    def get_partial_path(self, path=[]):
        """Returns the part of path in the tree, and the rest."""
        pass


class StringHierarchy(Hierarchy):
    def __init__(self, strings, separator=""):
        self.tree = {}
        self._strings = set(strings)
        self._separator = separator
        if not separator:
            self.tree = {s: None for s in strings}
        else:
            for string in self._strings:
                segments = string.split(separator)
                current_dict = self.tree
                for segment in segments:
                    if segment not in current_dict:
                        current_dict[segment] = {}
                    current_dict = current_dict[segment]

    @property
    def separator(self):
        return self._separator

    def _dict_to_nodes(self, dictionary):
        return [Node(label=k, internal=True) if dictionary[k]
                else Node(label=k, internal=False)
                for k in dictionary]

    def get_subtree(self, path=[]):
        current_dict = self.tree
        for item in path:
            current_dict = current_dict[item]
        return self._dict_to_nodes(current_dict)

    def get_partial_path(self, path=[]):
        current_dict = self.tree
        found_path = []
        rest_path = deque(path)
        try:
            for item in path:
                new_dict = current_dict[item]
                if new_dict:
                    current_dict = new_dict
                    rest_path.popleft()
                    found_path.append(item)
                else:
                    break
        except KeyError:
            pass
        finally:
            return found_path, list(rest_path)

    def __str__(self):
        return f"<StringHierarchy: {len(self._strings)} strings>"


class DirectoryHierarchy(Hierarchy):
    def __init__(self, location="."):
        self.root = Path(location)
        self._separator = "/"

    def _loc_to_nodes(self, location):
        return [Node(label=p.name, internal=True) if p.is_dir()
                else Node(label=p.name, internal=False)
                for p in location.iterdir()]

    def get_subtree(self, path=[]):
        current_location = self.root
        for item in path:
            current_location = current_location / item
        if current_location.is_dir():
            return self._loc_to_nodes(current_location)
        else:
            return []

    def get_partial_path(self, path=[]):
        current_location = self.root
        found_path = []
        rest_path = deque(path)
        for item in path:
            new_location = current_location / item
            if new_location.is_dir():
                current_location = new_location
                rest_path.popleft()
                found_path.append(item)
            else:
                break
        return found_path, list(rest_path)
