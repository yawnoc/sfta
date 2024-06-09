#!/usr/bin/env python3

import argparse
import os
import sys

from src.output_handling import create_directory_robust, write_output_files
from src.context_manager import DeepRecurse
from src.data_models.fault_tree import FaultTree
from src.data_models.exceptions.base import FaultTreeTextException


__version__ = '0.6.2'
DESCRIPTION = 'Perform a slow fault tree analysis.'


def parse_command_line_arguments():
    argument_parser = argparse.ArgumentParser(description=DESCRIPTION)
    argument_parser.add_argument(
        '-v',
        '--version',
        action='version',
        version=f'{argument_parser.prog} version {__version__}',
    )
    argument_parser.add_argument(
        'fault_tree_text_file_name',
        help='name of fault tree text file; output is written unto the directory `{ft.txt}.out/`',
        metavar='ft.txt',
    )
    return argument_parser.parse_args()


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
        with DeepRecurse(recursion_limit=10**4):
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

    output_directory_name = f'{text_file_name}.out'
    create_directory_robust(output_directory_name)
    write_output_files(fault_tree, output_directory_name)


if __name__ == '__main__':
    main()
