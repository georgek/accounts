#!/usr/bin/env python

import sys
import argparse
import csv
from collections import deque
import re

import model
from hierarchy import StringHierarchy
from pydo import pydo_input

HISTORY_SIZE = 100

DEFAULT_CURRENCY = "£"


def get_args():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description="Makes ledger from CSV file semi-automatically. "
        "If training data is provided then a model is trained and used "
        "to predict classes.")
    parser.add_argument("csv_file", type=argparse.FileType("r"),
                        help="CSV file containing date, payee, and "
                        "amount (relative to this account).")
    parser.add_argument("account_name", type=str,
                        help="Name of this account.")
    parser.add_argument("ledger_output", type=argparse.FileType("x"),
                        help="Output Ledger file.")
    parser.add_argument("-t", "--training_data", type=argparse.FileType("r"),
                        help="CSV file containing training data of form "
                        "payee_string,account_name")
    parser.add_argument("-n", "--new_training_data_output",
                        type=argparse.FileType("x"),
                        help="File to write new training data generated during "
                        "this session.")
    parser.add_argument("-c", "--currency", type=str, default=DEFAULT_CURRENCY,
                        help="Currency symbol to use.")
    return parser.parse_args()


def clean_date(date_string):
    """Makes a proper date string as long as the year is four digits and it's not
some stupid American format."""
    if "-" in date_string:
        components = date_string.split("-")
    elif "/" in date_string:
        components = date_string.split("/")
    else:
        raise Exception(f"Date format not recognised: {date_string}.")
    assert(len(components) == 3)
    if len(components[0]) == 4:
        year, month, day = components
    elif len(components[2]) == 4:
        day, month, year = components
    else:
        raise Exception(f"Date format not recognised: {date_string}.")
    return "-".join([year, month, day])


def format_amount(amount, currency, negative=True):
    if negative:
        amount = re.sub(r"^-", "", amount)
    return f"{currency}{amount}"


def format_transaction(date, payee, account_in, account_out, amount, currency):
    date = clean_date(date)
    amount = format_amount(amount, currency)
    s = f"{date} {payee}\n    {account_in:<36}{amount:>12}\n    {account_out}\n"
    return s


def main(csv_file,
         account_name,
         ledger_output,
         training_data=None,
         new_training_data_output=None,
         currency=DEFAULT_CURRENCY):
    if training_data:
        clf = model.make_model()
        X, y, target_names = model.read_csv_file(training_data)
        target_set = set(target_names)
        clf.fit(X, y)
    else:
        clf = None
        target_set = set()

    if new_training_data_output:
        new_training_data_writer = csv.writer(new_training_data_output)

    history = deque([], HISTORY_SIZE)
    hierarchy = StringHierarchy(target_names, separator=":")
    for i, record in enumerate(csv.reader(csv_file)):
        try:
            date, payee, amount = record
        except ValueError as e:
            sys.exit(f"Error on line {i}: {e}")

        if clf:
            cleaned = model.clean_string(payee)
            prediction_id = clf.predict([cleaned])[0]
            prediction = target_names[prediction_id]
        else:
            prediction = ""

        typed = pydo_input(hierarchy,
                           prompt=f"{payee} ({amount}): ",
                           initial_string=prediction,
                           forbidden=[" "],
                           history=history)
        if typed:
            if len(history) == 0 or typed != history[0]:
                history.appendleft(typed)
                target_set.add(typed)
                hierarchy = StringHierarchy(target_set, separator=":")

            entry = format_transaction(date, payee, typed, account_name,
                                       amount, currency)
            print(entry, file=ledger_output)
            if new_training_data_output:
                new_training_data_writer.writerow([payee, typed])
        else:
            break

    print("Bye.")


if __name__ == '__main__':
    args = get_args()
    main(**vars(args))
