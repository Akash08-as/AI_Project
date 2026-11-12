#!/usr/bin/env python3
"""
Treasure Hunt Simulator -- interactive GUI (pygame) for BFS and UCS.

Run:   pip install pygame
       python3 treasure_hunt_gui.py

CONTROLS
  Mouse : click the buttons; with a map tool selected, click/drag on the grid to paint.
  Keys  : B = run BFS   U = run UCS   SPACE = pause/resume   R = reset
          N = random map   D = default map   + / - = speed   C = show both paths
"""
import heapq
import math
import random
import time
from collections import deque

import pygame

# ----------------------------------------------------------------------------
# Map and search (pure logic, no pygame)
# ----------------------------------------------------------------------------
DEFAULT_MAP = [
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
MOVES = [(-1, 0), (1, 0), (0, -1), (0, 1)]


def step_cost(ch):
    return 5 if ch == "~" else 1


def find_items(grid):
    start, treasures = None, []
    for r, row in enumerate(grid):
        for c, ch in enumerate(row):
            if ch == "S":
                start = (r, c)
            elif ch == "T":
                treasures.append((r, c))
    return start, treasures


def reachable(grid, start):
    seen, stack = {start}, [start]
    while stack:
        r, c = stack.pop()
        for dr, dc in MOVES:
            nr, nc = r + dr, c + dc
            if 0 <= nr < len(grid) and 0 <= nc < len(grid[0]) \
                    and grid[nr][nc] != "#" and (nr, nc) not in seen:
                seen.add((nr, nc))
                stack.append((nr, nc))
    return seen


def validate(grid):
    """Return an error message, or None if the map can be solved."""
    start, treasures = find_items(grid)
    if start is None:
        return "Place a start cell (Start tool)."
    if not treasures:
        return "Place at least one treasure."
    lost = [t for t in treasures if t not in reachable(grid, start)]
    if lost:
        return f"Treasure at row {lost[0][0]}, col {lost[0][1]} is unreachable."
    return None


def solve(grid, algo):
    """Run BFS or UCS. Returns a dict with the path and statistics."""
    start, treasures = find_items(grid)
    tindex = {t: i for i, t in enumerate(treasures)}
    full = (1 << len(treasures)) - 1
    rows, cols = len(grid), len(grid[0])

    def collect(mask, pos):
        return mask | (1 << tindex[pos]) if pos in tindex else mask

    def successors(state):
        r, c, mask = state
        for dr, dc in MOVES:
            nr, nc = r + dr, c + dc
            if 0 <= nr < rows and 0 <= nc < cols and grid[nr][nc] != "#":
                yield (nr, nc, collect(mask, (nr, nc))), step_cost(grid[nr][nc])

    s0 = (*start, collect(0, start))
    parent, order, goal = {s0: None}, [], None
    t0 = time.perf_counter()

    if algo == "BFS":
        queue = deque([s0])
        while queue:
            state = queue.popleft()
            order.append(state[:2])
            if state[2] == full:
                goal = state
                break
            for nxt, _ in successors(state):
                if nxt not in parent:
                    parent[nxt] = state
                    queue.append(nxt)
    else:  # UCS
        best, heap, tie = {s0: 0}, [(0, 0, s0)], 0
        while heap:
            g, _, state = heapq.heappop(heap)
            if g > best[state]:
                continue
            order.append(state[:2])
            if state[2] == full:
                goal = state
                break
            for nxt, step in successors(state):
                if g + step < best.get(nxt, float("inf")):
                    best[nxt] = g + step
                    parent[nxt] = state
                    tie += 1
                    heapq.heappush(heap, (g + step, tie, nxt))

    ms = (time.perf_counter() - t0) * 1000
    path, state = [], goal
    while state:
        path.append(state[:2])
        state = parent[state]
    path.reverse()
    seen, torder = set(), []
    for p in path:
        if p in tindex and p not in seen:
            seen.add(p)
            torder.append(p)
    return dict(algo=algo, path=path, order=order, expanded=len(order), ms=ms,
                moves=len(path) - 1,
                cost=sum(step_cost(grid[r][c]) for r, c in path[1:]),
                torder=torder)


def random_map(rows=13, cols=20, treasures=5):
    """Random walled map with mud patches; retried until every treasure is reachable."""
    while True:
        g = [["#"] * cols for _ in range(rows)]
        for r in range(1, rows - 1):
            for c in range(1, cols - 1):
                g[r][c] = "#" if random.random() < 0.22 else "."
        for _ in range(random.randint(2, 4)):                  # mud patches
            pr, pc = random.randint(2, rows - 3), random.randint(2, cols - 4)
            for r in range(pr, pr + random.randint(2, 3)):
                for c in range(pc, pc + random.randint(2, 4)):
                    if 0 < r < rows - 1 and 0 < c < cols - 1:
                        g[r][c] = "~"
        free = [(r, c) for r in range(1, rows - 1) for c in range(1, cols - 1)]
        spots = random.sample(free, treasures + 1)
        for r, c in spots:
            g[r][c] = "."
        g[spots[0][0]][spots[0][1]] = "S"
        for r, c in spots[1:]:
            g[r][c] = "T"
        if validate(g) is None:
            return g


# ----------------------------------------------------------------------------
# GUI
# ----------------------------------------------------------------------------
W, H = 1120, 700
GRID_X, GRID_Y, GRID_W, GRID_H = 20, 84, 800, 540
PANEL_X = 846

BG = (14, 17, 28)
PANEL = (22, 27, 44)
TEXT = (232, 236, 248)
MUTED = (130, 140, 168)
GOLD = (255, 205, 70)
ALGO_COLOR = {"BFS": (70, 200, 255), "UCS": (255, 120, 190)}
GROUND_A, GROUND_B = (34, 42, 66), (38, 47, 73)
WALL_TOP, WALL_SIDE = (84, 94, 126), (52, 58, 82)
MUD_A, MUD_B = (96, 64, 40), (73, 48, 30)


class Button:
    def __init__(self, rect, label, action, color=(52, 62, 96), toggle_group=None, key=None):
        self.rect = pygame.Rect(rect)
        self.label, self.action, self.color = label, action, color
        self.group, self.key = toggle_group, key
        self.active = False

    def draw(self, surf, font, mouse):
        hover = self.rect.collidepoint(mouse)
        col = tuple(min(255, v + (28 if hover else 0)) for v in self.color)
        if self.active:
            col = tuple(min(255, v + 55) for v in self.color)
        pygame.draw.rect(surf, col, self.rect, border_radius=9)
        if self.active:
            pygame.draw.rect(surf, GOLD, self.rect, 2, border_radius=9)
        txt = font.render(self.label, True, TEXT)
        surf.blit(txt, txt.get_rect(center=self.rect.center))


class Game:
    def __init__(self, headless=False):
        pygame.init()
        pygame.display.set_caption("Treasure Hunt Simulator  -  BFS vs UCS")
        self.screen = pygame.display.set_mode((W, H))
        self.clock = pygame.time.Clock()
        self.f_title = pygame.font.Font(None, 44)
        self.f_big = pygame.font.Font(None, 30)
        self.f = pygame.font.Font(None, 24)
        self.f_small = pygame.font.Font(None, 20)
        self.grid = [list(r) for r in DEFAULT_MAP]
        self.tool = None
        self.speed = 3
        self.results = {}
        self.show_both = False
        self.msg, self.msg_t = "Pick BFS or UCS to start the hunt!", 6.0
        self.t = 0.0
        self.particles = []
        self.reset_run()
        self.make_buttons()
        self.running = True

    # ---- run state ---------------------------------------------------------
    def reset_run(self):
        self.mode = "idle"            # idle | exploring | walking | done
        self.current = None
        self.heat = {}
        self.explore_i = 0
        self.walk_pos = 0.0
        self.paused = False
        self.collected = set()

    def toast(self, text, secs=4.0):
        self.msg, self.msg_t = text, secs

    def start_search(self, algo):
        err = validate(self.grid)
        if err:
            self.toast(err)
            return
        self.reset_run()
        res = solve(self.grid, algo)
        self.results[algo] = res
        self.current = res
        self.mode = "exploring"
        self.toast(f"{algo}: exploring the map ...")

    # ---- layout -------------------------------------------------------------
    @property
    def rows(self):
        return len(self.grid)

    @property
    def cols(self):
        return len(self.grid[0])

    @property
    def cell(self):
        return min(GRID_W // self.cols, GRID_H // self.rows)

    def cell_rect(self, r, c):
        cs = self.cell
        ox = GRID_X + (GRID_W - cs * self.cols) // 2
        oy = GRID_Y + (GRID_H - cs * self.rows) // 2
        return pygame.Rect(ox + c * cs, oy + r * cs, cs, cs)

    def cell_at(self, pos):
        for r in range(self.rows):
            for c in range(self.cols):
                if self.cell_rect(r, c).collidepoint(pos):
                    return r, c
        return None

    def center(self, r, c):
        return self.cell_rect(r, c).center

    # ---- buttons --------------------------------------------------------------
    def make_buttons(self):
        x, w = PANEL_X + 14, 220 - 28 + 28
        self.buttons = []
        tools = [("Wall", "#"), ("Mud", "~"), ("Treasure", "T"), ("Start", "S"), ("Erase", ".")]
        y = 112
        for i, (label, ch) in enumerate(tools):
            bx = x + (i % 2) * 108
            by = y + (i // 2) * 34
            self.buttons.append(Button((bx, by, 100, 28), label,
                                       lambda ch=ch: self.set_tool(ch), toggle_group="tool"))
        self.tool_buttons = [b for b in self.buttons if b.group == "tool"]
        self.tool_chars = [ch for _, ch in tools]
        y = 244
        self.buttons += [
            Button((x, y, 208, 36), "Run BFS  (B)", lambda: self.start_search("BFS"), (28, 96, 128)),
            Button((x, y + 42, 208, 36), "Run UCS  (U)", lambda: self.start_search("UCS"), (136, 52, 96)),
            Button((x, y + 84, 100, 30), "Pause", self.toggle_pause),
            Button((x + 108, y + 84, 100, 30), "Reset", self.do_reset),
            Button((x, y + 122, 100, 30), "Random", self.new_random),
            Button((x + 108, y + 122, 100, 30), "Default", self.default_map),
            Button((x, y + 160, 40, 28), "-", lambda: self.change_speed(-1)),
            Button((x + 168, y + 160, 40, 28), "+", lambda: self.change_speed(1)),
        ]
        self.btn_pause = self.buttons[-6]

    def set_tool(self, ch):
        self.tool = None if self.tool == ch else ch
        for b, c in zip(self.tool_buttons, self.tool_chars):
            b.active = (self.tool == c)
        if self.tool:
            self.toast("Click or drag on the grid to paint.")

    def toggle_pause(self):
        if self.mode in ("exploring", "walking"):
            self.paused = not self.paused

    def do_reset(self):
        self.reset_run()
        self.results.clear()
        self.toast("Reset.")

    def new_random(self):
        self.grid = random_map()
        self.reset_run()
        self.results.clear()
        self.toast("New random map generated.")

    def default_map(self):
        self.grid = [list(r) for r in DEFAULT_MAP]
        self.reset_run()
        self.results.clear()
        self.toast("Default map restored.")

    def change_speed(self, d):
        self.speed = max(1, min(6, self.speed + d))

    # ---- events -----------------------------------------------------------------
    def paint(self, pos):
        if not self.tool:
            return
        cell = self.cell_at(pos)
        if not cell:
            return
        r, c = cell
        if r in (0, self.rows - 1) or c in (0, self.cols - 1):
            return                                    # keep the border wall
        if self.mode != "idle":
            self.reset_run()
        self.results.clear()
        if self.tool == "S":
            for rr in range(self.rows):
                for cc in range(self.cols):
                    if self.grid[rr][cc] == "S":
                        self.grid[rr][cc] = "."
        self.grid[r][c] = self.tool

    def handle_event(self, e):
        if e.type == pygame.QUIT:
            self.running = False
        elif e.type == pygame.KEYDOWN:
            k = e.key
            if k == pygame.K_ESCAPE:
                self.running = False
            elif k == pygame.K_b:
                self.start_search("BFS")
            elif k == pygame.K_u:
                self.start_search("UCS")
            elif k == pygame.K_SPACE:
                self.toggle_pause()
            elif k == pygame.K_r:
                self.do_reset()
            elif k == pygame.K_n:
                self.new_random()
            elif k == pygame.K_d:
                self.default_map()
            elif k == pygame.K_c:
                self.show_both = not self.show_both
            elif k in (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS):
                self.change_speed(1)
            elif k in (pygame.K_MINUS, pygame.K_KP_MINUS):
                self.change_speed(-1)
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            for b in self.buttons:
                if b.rect.collidepoint(e.pos):
                    b.action()
                    return
            self.paint(e.pos)
        elif e.type == pygame.MOUSEMOTION and e.buttons[0]:
            self.paint(e.pos)

    # ---- update -------------------------------------------------------------------
    def update(self, dt):
        self.t += dt
        self.msg_t = max(0.0, self.msg_t - dt)
        for p in self.particles:
            p[0] += p[2] * dt
            p[1] += p[3] * dt
            p[3] += 260 * dt
            p[4] -= dt
        self.particles = [p for p in self.particles if p[4] > 0]
        if self.paused or not self.current:
            return
        res = self.current
        if self.mode == "exploring":
            per_frame = max(1, int(res["expanded"] / 160 * self.speed / 3))
            for _ in range(per_frame):
                if self.explore_i >= len(res["order"]):
                    break
                p = res["order"][self.explore_i]
                self.heat[p] = self.heat.get(p, 0) + 1
                self.explore_i += 1
            if self.explore_i >= len(res["order"]):
                self.mode = "walking"
                self.walk_pos = 0.0
                self.toast(f"{res['algo']}: following the path ...")
        elif self.mode == "walking":
            path = res["path"]
            self.walk_pos = min(len(path) - 1, self.walk_pos + dt * (3 + 5 * self.speed))
            i = int(self.walk_pos)
            for p in path[:i + 1]:
                if p in res["torder"] and p not in self.collected:
                    self.collected.add(p)
                    self.burst(p)
            if self.walk_pos >= len(path) - 1:
                self.mode = "done"
                self.toast(f"{res['algo']} finished: {res['moves']} moves, cost {res['cost']}", 8)

    def burst(self, pos):
        x, y = self.center(*pos)
        for _ in range(22):
            a, s = random.uniform(0, math.tau), random.uniform(60, 220)
            self.particles.append([x, y, math.cos(a) * s, math.sin(a) * s - 80,
                                   random.uniform(0.4, 0.9)])

    # ---- drawing --------------------------------------------------------------------
    def draw_tile(self, r, c):
        rect, ch = self.cell_rect(r, c), self.grid[r][c]
        cs = rect.w
        if ch == "#":
            pygame.draw.rect(self.screen, WALL_SIDE, rect)
            pygame.draw.rect(self.screen, WALL_TOP, rect.inflate(-6, -10).move(0, -2), border_radius=5)
        elif ch == "~":
            pygame.draw.rect(self.screen, MUD_A if (r + c) % 2 else MUD_B, rect)
            for k in range(2):
                yy = rect.y + cs * (0.35 + 0.3 * k)
                pts = [(rect.x + 4 + i * cs / 6, yy + math.sin(self.t * 2 + i + k) * 2.5)
                       for i in range(6)]
                pygame.draw.lines(self.screen, (130, 92, 60), False, pts, 2)
        else:
            pygame.draw.rect(self.screen, GROUND_A if (r + c) % 2 else GROUND_B, rect)

    def draw_treasure(self, r, c):
        rect = self.cell_rect(r, c)
        cx, cy = rect.center
        cs = rect.w
        if (r, c) in self.collected:
            pygame.draw.circle(self.screen, (60, 120, 80), (cx, cy), cs // 4, 3)
            pygame.draw.lines(self.screen, (120, 230, 150), False,
                              [(cx - cs // 7, cy), (cx - 2, cy + cs // 8), (cx + cs // 6, cy - cs // 8)], 3)
            return
        glow = int(cs * (0.42 + 0.06 * math.sin(self.t * 3 + r + c)))
        s = pygame.Surface((cs * 2, cs * 2), pygame.SRCALPHA)
        pygame.draw.circle(s, (255, 200, 60, 55), (cs, cs), glow)
        self.screen.blit(s, (cx - cs, cy - cs))
        body = pygame.Rect(0, 0, int(cs * 0.64), int(cs * 0.42)).move(cx - int(cs * 0.32), cy - int(cs * 0.04))
        lid = pygame.Rect(body.x, body.y - int(cs * 0.17), body.w, int(cs * 0.22))
        pygame.draw.rect(self.screen, (150, 92, 40), body, border_radius=4)
        pygame.draw.rect(self.screen, GOLD, lid, border_radius=6)
        pygame.draw.rect(self.screen, (110, 66, 28), body, 2, border_radius=4)
        pygame.draw.rect(self.screen, (255, 240, 170), (cx - 3, body.y + 3, 6, 9), border_radius=2)

    def draw_start(self, r, c):
        rect = self.cell_rect(r, c)
        cx, cy = rect.center
        pygame.draw.circle(self.screen, (50, 170, 110), (cx, cy), rect.w // 2 - 4, 3)
        t = self.f_small.render("START", True, (120, 235, 170))
        self.screen.blit(t, t.get_rect(center=(cx, cy)))

    def draw_path_line(self, res, upto=None, alpha=210, width=6):
        pts = [self.center(*p) for p in res["path"]]
        if upto is not None:
            i = int(upto)
            pts = pts[:i + 1]
            if i < len(res["path"]) - 1:
                a, b, f = res["path"][i], res["path"][i + 1], upto - i
                (ax, ay), (bx, by) = self.center(*a), self.center(*b)
                pts.append((ax + (bx - ax) * f, ay + (by - ay) * f))
        if len(pts) > 1:
            s = pygame.Surface((W, H), pygame.SRCALPHA)
            col = (*ALGO_COLOR[res["algo"]], alpha)
            pygame.draw.lines(s, col, False, pts, width)
            self.screen.blit(s, (0, 0))

    def draw_grid(self):
        for r in range(self.rows):
            for c in range(self.cols):
                self.draw_tile(r, c)
        # exploration heat
        if self.current and self.heat:
            col = ALGO_COLOR[self.current["algo"]]
            cs = self.cell
            ov = pygame.Surface((cs, cs), pygame.SRCALPHA)
            for (r, c), n in self.heat.items():
                if self.grid[r][c] == "#":
                    continue
                ov.fill((*col, int(min(150, 40 + n * 14) * (0.55 if self.mode in ("walking", "done") else 1))))
                self.screen.blit(ov, self.cell_rect(r, c).topleft)
        # finished paths of both algorithms (toggle) and the current one
        if self.show_both:
            for res in self.results.values():
                self.draw_path_line(res, alpha=120, width=5)
        if self.current and self.mode == "walking":
            self.draw_path_line(self.current, self.walk_pos)
        elif self.current and self.mode == "done":
            self.draw_path_line(self.current)
        for r in range(self.rows):
            for c in range(self.cols):
                if self.grid[r][c] == "T":
                    self.draw_treasure(r, c)
                elif self.grid[r][c] == "S":
                    self.draw_start(r, c)
        # agent
        if self.current and self.mode in ("walking", "done"):
            path = self.current["path"]
            i = int(self.walk_pos)
            x, y = self.center(*path[i])
            if i < len(path) - 1:
                (bx, by), f = self.center(*path[i + 1]), self.walk_pos - i
                x, y = x + (bx - x) * f, y + (by - y) * f
            col = ALGO_COLOR[self.current["algo"]]
            pygame.draw.circle(self.screen, (255, 255, 255), (int(x), int(y)), self.cell // 3 + 3)
            pygame.draw.circle(self.screen, col, (int(x), int(y)), self.cell // 3)
            pygame.draw.circle(self.screen, (20, 24, 40), (int(x) - 4, int(y) - 3), 3)
            pygame.draw.circle(self.screen, (20, 24, 40), (int(x) + 4, int(y) - 3), 3)
        for x, y, _, _, life in self.particles:
            pygame.draw.circle(self.screen, GOLD, (int(x), int(y)), max(1, int(life * 5)))
        pygame.draw.rect(self.screen, (60, 70, 105),
                         (GRID_X - 3, GRID_Y - 3, GRID_W + 6, GRID_H + 6), 2, border_radius=6)

    def draw_panel(self):
        mouse = pygame.mouse.get_pos()
        pygame.draw.rect(self.screen, PANEL, (PANEL_X, 84, 254, 540), border_radius=14)
        x = PANEL_X + 14

        def head(txt, y):
            self.screen.blit(self.f_small.render(txt.upper(), True, MUTED), (x, y))

        head("Map tools (paint on grid)", 92)
        head("Search", 224)
        for b in self.buttons:
            b.draw(self.screen, self.f, mouse)
        self.btn_pause.label = "Resume" if self.paused else "Pause"
        lab = self.f.render(f"Speed {self.speed}", True, TEXT)
        self.screen.blit(lab, lab.get_rect(center=(x + 104, 244 + 160 + 14)))
        # results table
        y = 470
        head("Results", y - 22)
        for algo in ("BFS", "UCS"):
            res = self.results.get(algo)
            col = ALGO_COLOR[algo]
            pygame.draw.rect(self.screen, col, (x, y + 2, 5, 58), border_radius=2)
            self.screen.blit(self.f_big.render(algo, True, col), (x + 12, y))
            if res:
                other = self.results.get("UCS" if algo == "BFS" else "BFS")
                for i, (label, key, best) in enumerate((("moves", "moves", other and res["moves"] < other["moves"]),
                                                        ("cost", "cost", other and res["cost"] < other["cost"]))):
                    t = self.f_small.render(f"{label} {res[key]}", True, TEXT)
                    self.screen.blit(t, (x + 12, y + 22 + 16 * i))
                    if best:
                        self.screen.blit(self.f_small.render("best", True, GOLD),
                                         (x + 12 + t.get_width() + 8, y + 22 + 16 * i))
                self.screen.blit(self.f_small.render(
                    f"{res['expanded']} states  {res['ms']:.0f} ms", True, MUTED), (x + 12, y + 56))
            else:
                self.screen.blit(self.f_small.render("not run yet", True, MUTED), (x + 12, y + 26))
            y += 70

    def draw_header(self):
        self.screen.blit(self.f_title.render("TREASURE HUNT", True, GOLD), (22, 18))
        sub = self.f.render("Pathfinding simulator  -  BFS vs UCS", True, MUTED)
        self.screen.blit(sub, (310, 30))
        tot = len(find_items(self.grid)[1])
        got = len(self.collected)
        badge = pygame.Rect(PANEL_X, 22, 254, 44)
        pygame.draw.rect(self.screen, PANEL, badge, border_radius=12)
        t = self.f_big.render(f"Treasures  {got} / {tot}", True, GOLD if got == tot and tot else TEXT)
        self.screen.blit(t, t.get_rect(center=badge.center))

    def draw_footer(self):
        y = 636
        if self.msg_t > 0:
            t = self.f.render(self.msg, True, GOLD)
            self.screen.blit(t, (22, y))
        else:
            hint = "B/U run  |  SPACE pause  |  R reset  |  N random  |  D default  |  C both paths  |  +/- speed"
            self.screen.blit(self.f_small.render(hint, True, MUTED), (22, y + 3))
        # legend
        lx, ly = 22, 664
        items = [((54, 64, 98), "ground 1"), (MUD_A, "mud 5"), (WALL_TOP, "wall"), (GOLD, "treasure")]
        for col, name in items:
            pygame.draw.rect(self.screen, col, (lx, ly, 16, 16), border_radius=4)
            self.screen.blit(self.f_small.render(name, True, MUTED), (lx + 22, ly + 1))
            lx += 110
        if self.paused:
            t = self.f_big.render("PAUSED", True, (255, 150, 150))
            self.screen.blit(t, (GRID_X + GRID_W - 110, y))

    def draw(self):
        self.screen.fill(BG)
        self.draw_header()
        self.draw_grid()
        self.draw_panel()
        self.draw_footer()
        pygame.display.flip()

    def run(self):
        while self.running:
            dt = self.clock.tick(60) / 1000
            for e in pygame.event.get():
                self.handle_event(e)
            self.update(dt)
            self.draw()
        pygame.quit()


if __name__ == "__main__":
    Game().run()
