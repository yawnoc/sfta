#!/usr/bin/env python3


import textwrap


def main():
    """
    Generate a staircase-like fault tree:
    - AND_n has inputs [A_n, OR_n], where n = 1, ..., 10000
    - OR_n has inputs [O_n, AND_(n+1)], where n = 1, ..., 9999
    - OR_10000 has inputs [O_10000, L].
    """
    n_max = 10
    n_values = range(1, 1 + n_max)

    and_gates = ''.join(
        textwrap.dedent(f'''
            Gate: AND_{n}
            - type: AND
            - inputs: A_{n}, OR_{n}
        ''')
        for n in n_values
    )

    or_gates = ''.join(
        textwrap.dedent(f'''
            Gate: OR_{n}
            - type: OR
            - inputs: O_{n}, {f'AND_{n+1}' if n < n_max else 'L'}
        ''')
        for n in n_values
    )

    a_events = ''.join(
        textwrap.dedent(f'''
            Event: A_{n}
            - probability: 0.1
        ''')
        for n in n_values
    )

    o_events = ''.join(
        textwrap.dedent(f'''
            Event: O_{n}
            - probability: 0.1
        ''')
        for n in n_values
    )

    l_event = (
        textwrap.dedent(f'''
            Event: L
            - probability: 0.1
        ''')
    )

    all_objects = ''.join([and_gates, or_gates, a_events, o_events, l_event])

    with open('staircase.txt', 'w', encoding='utf-8') as file:
        file.write(all_objects)


if __name__ == '__main__':
    main()
