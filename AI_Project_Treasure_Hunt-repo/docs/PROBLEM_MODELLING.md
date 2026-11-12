# Problem Modelling

The Treasure Hunt is formulated as a standard state-space search problem.

| Element | Definition |
|---|---|
| **Environment** | A 2D grid. `#` wall, `.` ground (cost 1), `~` mud/water (cost 5), `S` start, `T` treasure. |
| **State** | `(row, col, treasures_found)`. `treasures_found` is the set of treasures collected so far (a bitmask in the code). |
| **Initial state** | The start cell with no treasures collected (or the treasure on the start cell, if any). |
| **Actions** | Move up, down, left or right into a neighbouring cell that is not a wall. |
| **Transition** | The agent moves to the new cell. If it holds a treasure, that treasure is added to `treasures_found`. |
| **Step cost** | Cost of the cell being entered: 1 for ground, 5 for mud. BFS ignores this and counts every move as 1. |
| **Goal test** | `treasures_found` contains every treasure on the map. The agent may finish on any cell. |
| **Solution** | The sequence of cells from the start to a goal state. |

## Why the state includes the collected treasures

The agent has to visit *all* treasures, so the same cell means something different before and after a
treasure has been picked up. Remembering which treasures are already held lets the search decide the visiting
order on its own. The state space has at most `rows x cols x 2^(number of treasures)` states.

## Algorithms

**Breadth-First Search (BFS)** explores states level by level with a FIFO queue. With every move counted as 1
it finds the path with the **fewest moves**. It does not look at terrain cost, so its path may cross mud.

**Uniform-Cost Search (UCS)** always expands the state with the lowest total path cost so far, using a priority
queue. With non-negative step costs it finds the path with the **lowest total cost**, even if that means more
moves.

Both keep a `parent` table to rebuild the path and never revisit a state, so they terminate.

## Results on the default map (5 treasures, 13 x 20 grid)

| Algorithm | Moves | Total cost | States expanded | Treasure order (row, col) |
|---|---|---|---|---|
| BFS | 58 | 78 | 3394 | (9,5) -> (11,7) -> (8,15) -> (6,12) -> (3,9) |
| UCS | 59 | 59 | 2609 | (9,5) -> (11,7) -> (3,9) -> (6,12) -> (8,15) |

BFS wins on moves (58 vs 59) but walks through mud, so it costs 78. UCS accepts one extra move and pays 59,
which is the cheapest possible.

## How the results were verified

During development both algorithms were cross-checked against an independent method: shortest paths between
every pair of treasures, tried over every visiting order. BFS matched the fewest moves, UCS matched the lowest
cost, and every returned path was valid (adjacent steps, no walls, all treasures visited). This was done on the
default map and on 40 random maps.
