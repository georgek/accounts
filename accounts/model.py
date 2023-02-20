"""Model for predicting account name based on payee string. When run the
module does a K-fold validation to test the model.

"""

import sys
import csv
import argparse
import re
from datetime import datetime, timedelta, MINYEAR

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

DEFAULT_LEDGER_MAXIMUM_AGE = 180


def get_args():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description="Test the current model performance using test data.")
    parser.add_argument("training_data", type=argparse.FileType("r"),
                        help="Ledger file to use for training data "
                        "and accounts names.")
    parser.add_argument("account_name", type=str,
                        help="Name of this account.")
    parser.add_argument("-m", "--ledger-maximum-age", type=int,
                        default=DEFAULT_LEDGER_MAXIMUM_AGE,
                        help="Maximum age, in days, of entries in ledger file "
                        "to use for training.")
    return parser.parse_args()


def remove_small_groups(sources, targets, min_size=5):
    """Returns sources and targets with small target groups removed."""
    tcount = Counter(targets)
    new_st = [(s, t) for s, t in zip(sources, targets)
              if tcount[t] >= min_size]
    if new_st:
        return tuple(zip(*new_st))
    else:
        return ([], [])


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
                                                  ngram_range=(3, 9))),
                         ("tfidf", TfidfTransformer(use_idf=False)),
                         ("clf", SGDClassifier(loss="hinge", penalty="l2",
                                               alpha=0.001, random_state=42,
                                               max_iter=4, tol=None))])
    return text_clf


def read_csv_file(csv_file, delimiter=",", quotechar='"'):
    """Returns X, y and target_names for training CSV."""
    csv_reader = csv.reader(csv_file, delimiter=delimiter, quotechar=quotechar)
    payees, accounts = zip(*csv_reader)
    X, y, target_names = payees_accounts_to_X_y(payees, accounts)
    return X, y, target_names


LEDGER_PAYEE_LINE = r"^([0-9\-]+)(=[0-9\-]+)?(?:\s+([\*!]))?"\
                                    "(?:\s+(\([^\)]*\)))?\s+(.*)$"
LEDGER_ACCOUNT_LINE = r"\s+[\[\(]?(\S+)[\]\)]?(?:\s+(\S+))?"


def parse_ledger_file(ledger_file, account_name, begin_date=None):
    """Parse ledger_file to retrieve account completion data and training
data. Training data is retrieved only for the "other side" of the transaction
for the given account_name. Only entries on or after the begin_date are
considered.

    """
    if begin_date is None:
        begin_date = datetime(MINYEAR, 1, 1)

    all_accounts = set()
    payees, accounts = [], []
    skip_section = False

    current_date = None
    for i, line in enumerate(ledger_file, 1):
        line = line[:-1]
        if re.match(r"^~", line):
            skip_section = True

        elif re.match(r"^\d", line):
            # date/payee line
            skip_section = False
            match = re.match(LEDGER_PAYEE_LINE, line)
            if match is None:
                raise Exception(f"Bad payee line, line {i}.")
            try:
                current_date = datetime.strptime(match.group(1),
                                                 "%Y-%m-%d")
            except ValueError as e:
                raise Exception(f"Bad date, line {i}.") from e
            current_payee = match.group(5)
            current_accounts = []

        elif skip_section:
            continue

        elif re.match(r"^\s", line):
            # account lines (only need to match the account name, no amounts)
            match = re.match(LEDGER_ACCOUNT_LINE, line)
            if match is None:
                raise Exception(f"Bad account line, line {i}.")
            account = match.group(1)
            if account != account_name:
                current_accounts.append(account)

        elif line == "" and current_date and current_date >= begin_date:
            all_accounts.update(current_accounts)
            if len(current_accounts) == 1:
                payees.append(current_payee)
                accounts.append(current_accounts[0])

    return all_accounts, payees, accounts


def payees_accounts_to_X_y(payees, accounts):
    """Converts lists of payees and names to X, y and target_names for use in
models."""
    payees, accounts = remove_small_groups(payees, accounts)
    account_dict = OrderedDict((name, i) for i, name in enumerate(set(accounts)))

    X = np.array([clean_string(s) for s in payees])
    y = np.array([account_dict[account] for account in accounts])
    target_names = list(account_dict.keys())
    return X, y, target_names


def run(training_data,
         account_name,
         ledger_maximum_age=DEFAULT_LEDGER_MAXIMUM_AGE):
    begin_date = datetime.today() - timedelta(days=ledger_maximum_age)
    all_accounts, payees, accounts = parse_ledger_file(
        training_data, account_name, begin_date=begin_date)
    X, y, target_names = payees_accounts_to_X_y(payees, accounts)
    if len(X) < 1:
        sys.exit("Nothing to classify. Only small groups?")

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


def main():
    args = get_args()
    run(**vars(args))
