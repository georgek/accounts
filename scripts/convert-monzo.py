#! /usr/bin/env python

# date, payee, amount

import csv
import sys


if __name__ == "__main__":
    reader = csv.DictReader(sys.stdin)
    writer = csv.writer(sys.stdout)
    for row in reader:
        date = row["Date"]
        name = row["Name"] or row["Description"]
        amount = row["Money Out"] or row["Money In"]

        writer.writerow([date, name, amount])
