import os
import csv

class Table:
    def __init__(self, field_names, rows):
        self.field_names = field_names
        self.rows = rows

    def write_tsv(self, file_name):
        with open(file_name, "w", encoding="utf-8", newline="") as file:
            writer = csv.writer(file, delimiter="\t", lineterminator=os.linesep)
            writer.writerow(self.field_names)
            writer.writerows(self.rows)
