#!/usr/bin/env python3

from sfta.core import FaultTree


def main():
    with open('demos/readme-example.txt', 'r', encoding='utf-8') as file:
        fault_tree_text = file.read()

    fault_tree = FaultTree(fault_tree_text)

    print('## Fault tree', end='\n\n')
    print(fault_tree, end='\n\n\n')

    print('## Events table', end='\n\n')
    print(fault_tree.get_events_table(), end='\n\n\n')

    print('## Gates table', end='\n\n')
    print(fault_tree.get_gates_table(), end='\n\n\n')


if __name__ == '__main__':
    main()
