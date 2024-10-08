# Slow Fault Tree Analyser (SFTA)

A slow (also shitty) fault tree analyser inspired by the idea presented in:

- Wheeler et al. (1977). Fault Tree Analysis Using Bit Manipulation.
  IEEE Transactions on Reliability, Volume R-26, Issue 2.
  <<https://doi.org/10.1109/TR.1977.5220060>>


## Text-driven

SFTA reads a textual representation of a fault tree. For example:

```txt
- time_unit: yr

Gate: FB
- label: Conway causeth floor to be buttered
- type: OR
- inputs: BF, TFBSD

Event: BF
- label: Conway knocketh butter onto floor
- rate: 0.1

Gate: TFBSD
- label: Conway knocketh toast onto floor butter side down
- type: AND
- inputs: TF, TB, BSD

Event: TF
- label: Conway knocketh toast onto floor
- rate: 0.2

Event: TB
- label: Falling toast is buttered
- probability: 0.75

Event: BSD
- label: Buttered toast landeth butter side down
- probability: 0.9
```

This allows for sensible diffing between two versions of a fault tree.


## Output

Output consists of:
- an events summary,
- a gates summary,
- cut set listings, and
- SVGs for all top gates and paged gates.

For the example above, we get the following SVG for the top gate `FB`:

<img
  alt="Nice looking SVG showing the example fault tree."
  src="https://raw.githubusercontent.com/yawnoc/sfta/master/demos/readme-example.txt.out/figures/FB.svg"
  width="640">


## Limitations

- Only supports coherent fault trees, which have only AND gates and OR gates.

- The probability or rate for a gate is approximated by simply summing the
  contributions from each minimal cut set (rare event approximation).
  The higher-order terms (subtraction of pairwise intersections, addition of
  triplet-wise intersections, etc.) have been neglected. This is conservative,
  as the first-order sum is an upper bound for the actual probability or rate.


## Installation

```bash
$ pip3 install sfta
```

- If simply using as a command line tool, do `pipx` instead of `pip3`
  to avoid having to set up a virtual environment.
- If using Windows, do `pip` instead of `pip3`.


## Usage (command line)

```bash
$ sfta [-h] [-v] ft.txt

Perform a slow fault tree analysis.

positional arguments:
  ft.txt         name of fault tree text file; output is written unto the
                 directory `{ft.txt}.out/`

optional arguments:
  -h, --help     show this help message and exit
  -v, --version  show program's version number and exit
```


## Usage (scripting example)

```python
from sfta.core import FaultTree, Gate

fault_tree = FaultTree('''
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

fault_tree.gate_from_id['AB'].quantity_value
# 0.63

fault_tree.gate_from_id['AB_C'].quantity_value
# 0.6301

fault_tree.gate_from_id['AB_C'].input_ids
# ['AB', 'C']

fault_tree.gate_from_id['AB_C'].type_ == Gate.TYPE_OR
# True
```


## License

**Copyright 2022–2024 Conway** <br>
Licensed under the GNU General Public License v3.0 (GPL-3.0-only). <br>
This is free software with NO WARRANTY etc. etc., see LICENSE. <br>
