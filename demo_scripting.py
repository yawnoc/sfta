#!/usr/bin/env python3

import textwrap

from sfta.core import FaultTree


def main():
    fault_tree_text = textwrap.dedent('''
        Event: A
        - rate: 0.9

        Event: B
        - probability: 0.7

        Event: C
        - rate: 1e-4

        Gate: AB
        - label: This be an AND gate.
        - type: AND
        - inputs: A, B

        Gate: AB_C
        - label: This be an OR gate.
        - type: OR
        - inputs: AB, C
    ''')

    fault_tree = FaultTree(fault_tree_text)
    print(fault_tree.gate_from_id['AB_C'].quantity_value)

    print(end='\n\n')

    print('## Fault tree', end='\n\n')
    print(fault_tree, end='\n\n\n')

    print('## Events table', end='\n\n')
    print(fault_tree.get_events_table(), end='\n\n\n')

    print('## Gates table', end='\n\n')
    print(fault_tree.get_gates_table(), end='\n\n\n')


if __name__ == '__main__':
    main()
