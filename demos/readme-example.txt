- time_unit: yr

Gate: FB
- label: Floor buttered
- type: OR
- inputs: BF, TFBSD

Event: BF
- label: Butter knocked unto floor
- rate: 0.1

Gate: TFBSD
- label: Toast knocked unto floor butter side down
- type: AND
- inputs: TF, TB, BSD

Event: TF
- label: Toast knocked unto floor
- rate: 0.2

Event: TB
- label: Toast buttered
- probability: 0.75

Event: BSD
- label: Buttered toast landeth butter side down
- probability: 0.9
