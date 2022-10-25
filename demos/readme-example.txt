Gate: SYS
- label: System fails
- type: OR
- inputs: A, SUB

Event: A
- label: Component A fails
- probability: 0.01

Gate: SUB
- label: Subsystem fails
- type: AND
- inputs: B, C

Event: B
- label: Component B fails
- probability: 0.2

Event: C
- label: Component C fails
- probability: 0.3
