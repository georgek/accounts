#!/usr/bin/env python

"""Model for predicting account name based on payee string. When run the
module does a K-fold validation to test the model.

"""

import sys
import csv
import argparse
import re

from collections import Counter, OrderedDict

import numpy as np

from sklearn.feature_extraction.text import CountVectorizer
from sklearn.feature_extraction.text import TfidfTransformer
from sklearn.linear_model import SGDClassifier
from sklearn.pipeline import Pipeline
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import confusion_matrix, classification_report

import colored
from colored import stylize


def get_args():
    parser = argparse.ArgumentParser(
        description="Test the current model performance using test data.")
    parser.add_argument("training_data", type=argparse.FileType("r"),
                        help="CSV file containing training data of form "
                        "payee_string,account_name.")
    return parser.parse_args()


def remove_small_groups(sources, targets, min_size=5):
    """Returns sources and targets with small target groups removed."""
    tcount = Counter(targets)
    new_st = [(s, t) for s, t in zip(sources, targets)
              if tcount[t] >= min_size]
    return tuple(zip(*new_st))


def clean_string(string):
    string = re.sub(r"\d", "0", string)
    return string.upper().strip()


def print_confusion_matrix(matrix, labels, fileout=sys.stdout):
    """Pretty print confusion matrix."""
    assert(matrix.shape[0] == len(labels))
    mm = np.max(matrix)
    ml = len(str(mm))
    ll = max(len(lab) for lab in labels)
    fileout.write(" " * ll)
    tinylabs = (lab.split(":")[-1][0] for lab in labels)
    for tinylab in tinylabs:
        fileout.write(f"{tinylab:>{ml+1}s}")
    fileout.write("\n")
    for j, (label, row) in enumerate(zip(labels, matrix)):
        fileout.write(f"{label:>{ll}s}")
        for i, v in enumerate(row):
            if i == j:
                fg = "green_1"
            elif v > 0:
                fg = "red_1"
            else:
                fg = "grey_50"
            if fileout.isatty():
                fileout.write(stylize(f"{v:>{ml+1}d}", colored.fg(fg)))
            else:
                fileout.write(f"{v:>{ml+1}d}")

        fileout.write("\n")


def make_model():
    text_clf = Pipeline([("vect", CountVectorizer(analyzer="char",
                                                  ngram_range=(5, 9))),
                         ("tfidf", TfidfTransformer(use_idf=False)),
                         ("clf", SGDClassifier(loss="hinge", penalty="l2",
                                               alpha=0.001, random_state=42,
                                               max_iter=4, tol=None))])
    return text_clf


def read_csv_file(csv_file, delimiter=",", quotechar='"'):
    """Returns X, y and target_names for training CSV."""
    csv_reader = csv.reader(csv_file, delimiter=delimiter, quotechar=quotechar)
    payee_strings, account_names = zip(*csv_reader)
    payee_strings, account_names = remove_small_groups(
        payee_strings, account_names)
    account_dict = OrderedDict((name, i)
                               for i, name in enumerate(set(account_names)))

    X = np.array([clean_string(s) for s in payee_strings])
    y = np.array([account_dict[account_name] for account_name in account_names])
    target_names = list(account_dict.keys())
    return X, y, target_names


def main(training_data):
    X, y, target_names = read_csv_file(training_data)

    text_clf = make_model()

    skf = StratifiedKFold(n_splits=3, shuffle=True, random_state=42)
    pred = np.empty_like(y)
    for train_index, test_index in skf.split(X, y):
        text_clf.fit(X[train_index], y[train_index])
        pred[test_index] = text_clf.predict(X[test_index])

    cm = confusion_matrix(y, pred)
    print_confusion_matrix(cm, target_names)
    print()
    print(classification_report(y, pred, target_names=target_names))


if __name__ == '__main__':
    args = get_args()
    main(**vars(args))
