#!/usr/bin/env python

from abc import ABCMeta, abstractmethod
from pathlib import Path


class Hierarchy(metaclass=ABCMeta):
    @property
    def separator(self):
        return self._separator

    @abstractmethod
    def get_subtree(self, path=[]):
        pass


class StringHierarchy(Hierarchy):
    def __init__(self, strings, separator=""):
        self.tree = {}
        self._separator = separator
        if not separator:
            self.tree = {s: None for s in strings}
        else:
            for string in strings:
                segments = string.split(separator)
                current_dict = self.tree
                for segment in segments:
                    if segment not in current_dict:
                        current_dict[segment] = {}
                    current_dict = current_dict[segment]

    @property
    def separator(self):
        return self._separator

    def get_subtree(self, path=[]):
        current_dict = self.tree
        for item in path:
            current_dict = current_dict[item]
        return [(k, "internal") if current_dict[k] else (k, "leaf")
                for k in current_dict]


class DirectoryHierarchy(Hierarchy):
    def __init__(self, location="."):
        self.root = Path(location)
        self._separator = "/"

    def get_subtree(self, path=[]):
        current_location = self.root
        for item in path:
            current_location = current_location / item
        if current_location.is_dir():
            return [(p.name, "internal") if p.is_dir() else (p.name, "leaf")
                    for p in current_location.iterdir()]
        else:
            return []
