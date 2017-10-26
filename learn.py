#!/usr/bin/env python

import sys
import argparse
import csv
import iterfzf

import numpy as np

import itertools
from operator import itemgetter
from collections import Counter

from sklearn.feature_extraction.text import CountVectorizer
from sklearn.feature_extraction.text import TfidfTransformer
from sklearn.linear_model import SGDClassifier
from sklearn.pipeline import Pipeline
from sklearn.model_selection import GridSearchCV
from sklearn import metrics

from typing import List, Iterable

import accounts as ac


def get_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="""Learn account names from payee names.""")
    parser.add_argument("payee_file", type=argparse.FileType("r"),
                        help="Payee list.")
    return parser.parse_args()


def uniq(iterator: Iterable) -> Iterable:
    return map(itemgetter(0), itertools.groupby(iterator))


def remove_small_groups(sources, targets, min_size=5):
    tcount = Counter(targets)
    new_st = [(s, t) for s, t in zip(sources, targets)
              if tcount[t] >= min_size]
    return tuple(zip(*new_st))


def print_confusion_matrix(matrix: np.ndarray,
                           labels: List[str],
                           fileout=sys.stdout) -> None:
    assert(matrix.shape[0] == len(labels))
    mm = np.max(matrix)
    ml = len(str(mm))
    ll = max(len(lab) for lab in labels)
    fileout.write(" " * (ll+1))
    tinylabs = (lab.split(":")[-1][0] for lab in labels)
    for tinylab in tinylabs:
        fileout.write(f"{tinylab:>{ml+1}s}")
    fileout.write("\n")
    for label, row in zip(labels, matrix):
        fileout.write(f"{label:>{ll+1}s}")
        for v in row:
            fileout.write(f"{v:>{ml+1}d}")
        fileout.write("\n")


def main(payee_file: Iterable[str]) -> None:
    payeereader = csv.reader(payee_file, delimiter=",", quotechar='"')
    payees = []
    paccs = []
    for payee, account in payeereader:
        payees.append(payee)
        paccs.append(account)
    accounts = list(set(paccs))
    accountdict = dict(zip(accounts, range(len(accounts))))
    accids = [accountdict[acc] for acc in paccs]

    payees, accids = remove_small_groups(payees, accids, min_size=8)

    train_size = 500
    payee_train = payees[:train_size]
    accids_train = accids[:train_size]
    payee_test = payees[train_size:]
    accids_test = accids[train_size:]

    text_clf = Pipeline([("vect", CountVectorizer(analyzer="char",
                                                  ngram_range=(5, 9))),
                         ("tfidf", TfidfTransformer(use_idf=False)),
                         ("clf", SGDClassifier(loss="hinge", penalty="l2",
                                               alpha=0.001, random_state=42,
                                               max_iter=4, tol=None))])

    text_clf.fit(payee_train, accids_train)

    account_bits = ac.account_bits(accounts)
    for payee in payee_test:
        predicted = text_clf.predict([payee])
        predicted_account = accounts[predicted[0]]
        typed, selected = iterfzf.iterfzf(sorted(account_bits,
                                                 key=ac.account_nlevels),
                                          query=predicted_account,
                                          case_sensitive=False,
                                          multi=False, print_query=True,
                                          prompt=f"{payee} : ")
        if typed is None and selected is None:
            # user quit
            break
        elif selected is None:
            # a new account is typed
            sys.stdout.write(f"{typed}\n")
        elif selected[-1] == ":":
            # a partial account is typed
            account_end = input(selected)
            sys.stdout.write(f"{selected}{account_end}\n")
        else:
            # an existing account is selected
            sys.stdout.write(f"{selected}\n")


if __name__ == '__main__':
    args = get_args()
    main(**vars(args))
