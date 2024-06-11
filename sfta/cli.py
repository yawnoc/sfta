"""
# Slow Fault Tree Analyser: cli.py

Command-line interface.

**Copyright 2022–2024 Conway**
Licensed under the GNU General Public License v3.0 (GPL-3.0-only).
This is free software with NO WARRANTY etc. etc., see LICENSE.
"""

import argparse
import os
import shutil
import sys

from sfta._version import __version__
from sfta.core import FaultTreeTextException, FaultTree, Index


class DeepRecurse:
    """
    Context manager for raising maximum recursion depth.
    """
    def __init__(self, recursion_limit):
        self.recursion_limit = recursion_limit

    def __enter__(self):
        self.old_recursion_limit = sys.getrecursionlimit()
        sys.setrecursionlimit(self.recursion_limit)

    def __exit__(self, exception_type, exception_value, traceback):
        sys.setrecursionlimit(self.old_recursion_limit)


def parse_command_line_arguments():
    argument_parser = argparse.ArgumentParser(
        description='Perform a slow fault tree analysis.'
    )
    argument_parser.add_argument(
        '-v', '--version',
        action='version',
        version=f'{argument_parser.prog} version {__version__}',
    )
    argument_parser.add_argument(
        'fault_tree_text_file_name',
        help=(
          'name of fault tree text file; '
          'output is written unto the directory `{ft.txt}.out/`'
        ),
        metavar='ft.txt',
    )

    return argument_parser.parse_args()


def create_directory_robust(directory_name):
    if os.path.isfile(directory_name):
        os.remove(directory_name)
    if os.path.isdir(directory_name):
        shutil.rmtree(directory_name)
    os.mkdir(directory_name)


def main():
    parsed_arguments = parse_command_line_arguments()
    text_file_name = parsed_arguments.fault_tree_text_file_name

    if os.path.isdir(text_file_name):
        print(
            f'Error: `{text_file_name}` is a directory, not a file',
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        with open(text_file_name, 'r', encoding='utf-8') as file:
            fault_tree_text = file.read()
    except FileNotFoundError:
        print(f'Error: file `{text_file_name}` existeth not', file=sys.stderr)
        sys.exit(1)

    try:
        with DeepRecurse(recursion_limit=10 ** 4):
            fault_tree = FaultTree(fault_tree_text)
    except FaultTreeTextException as exception:
        line_number = exception.line_number
        message = exception.message

        if line_number:
            error_location_str = f'at line {line_number} '
        else:
            error_location_str = ''

        print(
            f'Error {error_location_str}in `{text_file_name}`:\n  {message}',
            file=sys.stderr,
        )
        sys.exit(1)

    events_table = fault_tree.get_events_table()
    gates_table = fault_tree.get_gates_table()
    cut_set_table_from_gate_id = fault_tree.get_cut_set_tables()
    contribution_table_from_gate_id = fault_tree.get_contribution_tables()
    figure_from_id = fault_tree.get_figures()

    output_directory_name = f'{text_file_name}.out'
    cut_sets_directory_name = f'{output_directory_name}/cut-sets'
    contributions_directory_name = f'{output_directory_name}/contributions'
    figures_directory_name = f'{output_directory_name}/figures'

    create_directory_robust(output_directory_name)
    create_directory_robust(cut_sets_directory_name)
    create_directory_robust(contributions_directory_name)
    create_directory_robust(figures_directory_name)

    figure_index = Index(figure_from_id, figures_directory_name)

    events_table.write_tsv(f'{output_directory_name}/events.tsv')
    gates_table.write_tsv(f'{output_directory_name}/gates.tsv')
    for gate_id, cut_set_table in cut_set_table_from_gate_id.items():
        cut_set_table.write_tsv(f'{cut_sets_directory_name}/{gate_id}.tsv')
    for gate_id, contribution_table in contribution_table_from_gate_id.items():
        contribution_table.write_tsv(
            f'{contributions_directory_name}/{gate_id}.tsv'
        )
    for figure_id, figure in figure_from_id.items():
        figure.write_svg(f'{figures_directory_name}/{figure_id}.svg')
    figure_index.write_html(f'{figures_directory_name}/index.html')


if __name__ == '__main__':
    main()
