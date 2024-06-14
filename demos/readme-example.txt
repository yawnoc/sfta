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
