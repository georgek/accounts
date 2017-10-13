#!/usr/bin/env python

import sys
import argparse
import csv
import iterfzf


def get_args():
    parser = argparse.ArgumentParser(
        description="Makes ledger from CSV file semi-automatically.")
    parser.add_argument("csv_file", type=argparse.FileType("r"),
                        help="CSV file containing date, payee, and "
                        "amount (relative to this account).")
    parser.add_argument("account_name", type=str,
                        help="Name of this account.")
    return parser.parse_args()


def read_csv_file(csv_file, delimiter=",", quotechar='"'):
    csv_reader = csv.reader(csv_file, delimiter=delimiter, quotechar=quotechar)
    return csv_reader


def account_bits(accounts):
    names = set()
    for account in accounts:
        bits = account.strip().split(":")
        chunk = ""
        for bit in bits[:-1]:
            chunk += bit + ":"
            names.add(chunk)
        names.add(chunk + bits[-1])
    return names


def account_nlevels(account_name):
    return len([acc for acc in account_name.split(":") if len(acc) > 0])


def main(csv_file,
         account_name):
    whole_accounts = [line.strip() for line in sys.stdin]
    names = account_bits(whole_accounts)
    for date, payee, amount in read_csv_file(csv_file):
        print(date)
        print(payee)
        print(amount)
        typed, selected = iterfzf.iterfzf(sorted(names, key=account_nlevels),
                                          multi=False, print_query=True)
        if typed or selected:
            sys.stdout.write(f"Typed: {typed}\nSelected: {selected}\n")
        else:
            break


if __name__ == '__main__':
    args = get_args()
    main(**vars(args))
