# =============================================================================
# TREASURE HUNT: finding ALL treasures with BFS and UCS
# =============================================================================
# PROBLEM MODELLING (search problem formulation)
#
# Environment : a 2D grid map. Each cell is one of
#                 '#' wall (cannot enter)      '.' ground (move cost 1)
#                 '~' mud/water (move cost 5)  'S' start   'T' treasure
#               The agent moves 1 cell at a time: up, down, left or right.
#
# State       : (row, col, treasures_found)
#               row, col         = the agent's current cell
#               treasures_found  = the set of treasures collected so far.
#               Position alone is not enough: the same cell means something
#               different before and after collecting a treasure. Remembering
#               which treasures are collected lets the search plan the order
#               in which to visit them.
#
# Initial state : (start_row, start_col, empty set)
#
# Actions       : move Up / Down / Left / Right into a neighbouring cell
#                 that is not a wall.
#
# Transition    : the agent moves to the new cell; if that cell holds a
#                 treasure, it is added to treasures_found.
#
# Step cost     : cost of the cell being entered (1 for ground, 5 for mud).
#                 BFS ignores this and counts every move as 1.
#
# Goal test     : treasures_found == all treasures on the map
#                 (the agent may finish on any cell).
#
# Solution      : the sequence of cells from the start to a goal state.
#
# ALGORITHMS
#   BFS : explores states level by level (queue, FIFO). With every move
#         counted as 1 it is optimal in the NUMBER OF MOVES, but it ignores
#         terrain cost, so its path may cross expensive mud.
#   UCS : explores the state with the lowest total path cost first (priority
#         queue). It is optimal in TOTAL COST (for non-negative step costs),
#         so it avoids mud when a cheaper route exists, even if it needs
#         more moves.
#
# Both algorithms keep a "parent" table (to rebuild the path) and avoid
# revisiting a state, so they terminate. State space size is at most
# rows * cols * 2^(number of treasures).
# =============================================================================

# Treasure Hunt: find ALL treasures using BFS and UCS.
# Run with:  python3 treasure_hunt_simple.py
from collections import deque
import heapq

# Map: # wall, . ground (cost 1), ~ mud (cost 5), S start, T treasure
MAP = [
    "####################",
    "#S..#......~~~.....#",
    "#.#.#.####.~~~.###.#",
    "#.#...#..T.~~~.#...#",
    "#.#####.##.....#.#.#",
    "#.....#....###.#.#.#",
    "#.###.####.#T..#.#.#",
    "#.#.........#..###.#",
    "#.#.######.##.#T...#",
    "#...#T.....~~.#.####",
    "#.###.####.~~.#....#",
    "#.....#T...~~...##.#",
    "####################",
]

ROWS, COLS = len(MAP), len(MAP[0])
START = next((r, c) for r in range(ROWS) for c in range(COLS) if MAP[r][c] == "S")
TREASURES = {(r, c) for r in range(ROWS) for c in range(COLS) if MAP[r][c] == "T"}


def cost(r, c):
    return 5 if MAP[r][c] == "~" else 1


def next_states(state):
    """From (row, col, treasures_found) return each possible move and its cost."""
    r, c, found = state
    for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
        nr, nc = r + dr, c + dc
        if MAP[nr][nc] != "#":                      # walls surround the map
            new_found = found | ({(nr, nc)} & TREASURES)
            yield (nr, nc, frozenset(new_found)), cost(nr, nc)


def is_goal(state):
    return state[2] == TREASURES                    # all treasures collected


def bfs():
    """Fewest moves (every move counts as 1)."""
    start = (*START, frozenset())
    parent = {start: None}
    queue = deque([start])
    while queue:
        state = queue.popleft()
        if is_goal(state):
            return build_path(parent, state)
        for nxt, _ in next_states(state):
            if nxt not in parent:
                parent[nxt] = state
                queue.append(nxt)


def ucs():
    """Lowest total cost (mud costs more than ground)."""
    start = (*START, frozenset())
    parent = {start: None}
    best = {start: 0}
    heap = [(0, 0, start)]                          # (cost so far, tie-breaker, state)
    n = 0
    while heap:
        g, _, state = heapq.heappop(heap)
        if g > best[state]:
            continue                                # old, worse entry
        if is_goal(state):
            return build_path(parent, state)
        for nxt, step in next_states(state):
            if g + step < best.get(nxt, float("inf")):
                best[nxt] = g + step
                parent[nxt] = state
                n += 1
                heapq.heappush(heap, (g + step, n, nxt))


def build_path(parent, state):
    path = []
    while state:
        path.append(state[:2])
        state = parent[state]
    return path[::-1]


def show(name, path):
    moves = len(path) - 1
    total = sum(cost(r, c) for r, c in path[1:])
    print(f"\n{name}: {moves} moves, total cost {total}")

    # Split the full path into legs: start -> 1st treasure -> 2nd treasure -> ...
    print("Path to each treasure:")
    leg, last, number, seen = [path[0]], path[0], 0, set()
    for step in path[1:]:
        leg.append(step)
        if step in TREASURES and step not in seen:
            seen.add(step)
            number += 1
            print(f"  {number}. {last} -> {step}: {len(leg) - 1} moves")
            print("     " + " ".join(str(p) for p in leg))
            leg, last = [step], step
    print("Full path:", " ".join(str(p) for p in path))
    for r in range(ROWS):
        print("".join("*" if (r, c) in path and MAP[r][c] in ".~" else MAP[r][c]
                      for c in range(COLS)))


show("BFS (fewest moves)", bfs())
show("UCS (lowest cost)", ucs())
