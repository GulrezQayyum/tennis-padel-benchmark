"""
Tennis vs Padel state-tracking benchmark - CLEAN VERSION FOR PUBLISHING
Paste into a NEW notebook from https://www.kaggle.com/benchmarks/tasks/new
Each "# %%" block = one cell. The very last cell must be:   %choose tennis_padel_state_tracking
"""
# %%
import random
import re

import pandas as pd
import kaggle_benchmarks as kbench

# %%
# =====================================================================
# 1. SCORE ENGINE  (side 0 = "A", side 1 = "B")
# =====================================================================
PT = ["0", "15", "30", "40"]
NAMES = ["A", "B"]


class Match:
    """Best of 3 sets. Tiebreak at 6-6 (to 7, win by 2) counts as one game.
    golden=False -> tennis advantage scoring. golden=True -> padel golden point.
    Side A serves the first game. The serving side alternates every game.
    Tiebreak: first server serves 1 point, then 2 each, alternating."""

    def __init__(self, golden=False):
        self.golden = golden
        self.sets = [0, 0]
        self.games = [0, 0]
        self.pts = [0, 0]
        self.game_server = 0   # server of the current game (= first server in a tiebreak)
        self.in_tb = False
        self.done = False

    def server(self):
        if not self.in_tb:
            return self.game_server
        k = self.pts[0] + self.pts[1]
        f = self.game_server
        return f if ((k + 1) // 2) % 2 == 0 else 1 - f

    def point(self, w):
        if self.done:
            raise ValueError("match already finished")
        self.pts[w] += 1
        a, b = self.pts[w], self.pts[1 - w]
        if self.in_tb:
            game_won = a >= 7 and a - b >= 2
        elif self.golden:
            game_won = a >= 4
        else:
            game_won = a >= 4 and a - b >= 2
        if game_won:
            self._win_game(w)

    def _win_game(self, w):
        self.games[w] += 1
        self.pts = [0, 0]
        self.in_tb = False
        self.game_server = 1 - self.game_server  # tiebreak counts as a game too
        g, h = self.games[w], self.games[1 - w]
        if (g >= 6 and g - h >= 2) or (g == 7 and h == 6):
            self.sets[w] += 1
            self.games = [0, 0]
            if self.sets[w] == 2:
                self.done = True
        elif self.games == [6, 6]:
            self.in_tb = True

    def points_display(self):
        a, b = self.pts
        if self.in_tb:
            return f"{a}-{b}"
        if a >= 3 and b >= 3:
            if a == b:
                return "40-40"
            return "AD-40" if a > b else "40-AD"
        return f"{PT[a]}-{PT[b]}"

    def answer(self):
        return (f"sets={self.sets[0]}-{self.sets[1]}; games={self.games[0]}-{self.games[1]}; "
                f"points={self.points_display()}; server={NAMES[self.server()]}")


def self_test():
    # plain game, 4-0
    m = Match(); [m.point(0) for _ in range(4)]
    assert m.answer() == "sets=0-0; games=1-0; points=0-0; server=B", m.answer()
    # tennis deuce / advantage
    m = Match()
    for w in [0, 0, 0, 1, 1, 1]: m.point(w)
    assert m.points_display() == "40-40"
    m.point(0); assert m.points_display() == "AD-40"
    m.point(1); assert m.points_display() == "40-40"
    m.point(1); assert m.points_display() == "40-AD"
    m.point(1); assert m.games == [0, 1] and m.pts == [0, 0]
    # padel golden point: next point at 40-40 wins the game
    m = Match(golden=True)
    for w in [0, 0, 0, 1, 1, 1]: m.point(w)
    assert m.points_display() == "40-40"
    m.point(1); assert m.games == [0, 1] and m.pts == [0, 0]
    # tiebreak server pattern for first server A: A, B,B, A,A, B,B, A,A
    m = Match()
    m.games = [6, 6]; m.in_tb = True; m.game_server = 0
    seq = []
    for _ in range(9):
        seq.append(m.server()); m.point(0 if len(seq) % 2 else 1)  # keep it unfinished
        if m.done or not m.in_tb: break
    assert seq[:9] == [0, 1, 1, 0, 0, 1, 1, 0, 0], seq
    # win a tiebreak 7-0 -> set to A, B serves next game (A served first in tb)
    m = Match(); m.games = [6, 6]; m.in_tb = True; m.game_server = 0
    for _ in range(7): m.point(0)
    assert m.sets == [1, 0] and m.games == [0, 0] and m.server() == 1
    # 7-5 set (no tiebreak)
    m = Match(); m.games = [6, 5]
    for _ in range(4): m.point(0)
    assert m.sets == [1, 0], (m.sets, m.games)
    print("self_test passed")


# =====================================================================
# 2. CASE GENERATOR
# =====================================================================
RULES_TENNIS = (
    "Rules: standard tennis scoring. Points inside a game are 0, 15, 30, 40. A game is won by the first "
    "side to win 4 points with a lead of at least 2 (at 40-40 it is deuce; the next point gives AD to that "
    "side). A set is won by the first side to 6 games with a lead of at least 2; at 6-6 in games a "
    "tiebreak is played to 7 points (win by 2), scored 0,1,2,... and counted as one game. The match is "
    "best of 3 sets. The serving side alternates every game. In a tiebreak the side due to serve serves "
    "1 point, then the other side serves 2 points, then they alternate every 2 points. The side that served "
    "first in a tiebreak does not serve first in the next set."
)
RULES_PADEL = (
    "Rules: padel with golden point scoring. Points inside a game are 0, 15, 30, 40. At 40-40 the next "
    "point decides the game (golden point). A set is won by the first team to 6 games with a lead of at "
    "least 2; at 6-6 in games a tiebreak is played to 7 points (win by 2), scored 0,1,2,... and counted as "
    "one game. The match is best of 3 sets. Each side is a team of two; only the serving TEAM matters. "
    "The serving team alternates every game. In a tiebreak the team due to serve serves 1 point, then the "
    "other team serves 2 points, then they alternate every 2 points. The team that served first in a "
    "tiebreak does not serve first in the next set."
)
HEADER_NO_RULES = {
    "tennis": "Sport: tennis (standard rules, best of 3 sets, tiebreak at 6-6 in games).",
    "padel": "Sport: padel (golden point scoring, best of 3 sets, tiebreak at 6-6 in games).",
}
SIDE_WORD = {"tennis": "player", "padel": "team"}


def build_prompt(sport, winners, rules_given):
    side = SIDE_WORD[sport]
    head = (RULES_TENNIS if sport == "tennis" else RULES_PADEL) if rules_given else HEADER_NO_RULES[sport]
    seq = " ".join(NAMES[w] for w in winners)
    return (
        f"{head}\n\n"
        f"{side.capitalize()} A serves the first game of the match. Below, each letter is the {side} that "
        f"won that point, in order ({len(winners)} points):\n\n{seq}\n\n"
        f"Give the state of the match right after the final point. If the final point ended a game or set, "
        f"report the NEW game/set (points 0-0 and the {side} who serves next).\n"
        f"Use points notation 0/15/30/40/AD inside a normal game, and plain numbers inside a tiebreak.\n"
        f"Think as long as you need, then finish with exactly one line in this format:\n"
        f"ANSWER: sets=<A>-<B>; games=<A>-<B>; points=<A>-<B>; server=<A or B>"
    )


def _play(winners, golden):
    m = Match(golden)
    for w in winners:
        if m.done:
            return None
        m.point(w)
    return m


def regular_case(rng, golden, n_points):
    while True:
        p = rng.uniform(0.4, 0.6)
        winners = [0 if rng.random() < p else 1 for _ in range(n_points)]
        m = _play(winners, golden)
        if m is not None and not m.done:
            return winners, m


def tiebreak_case(rng, golden, k):
    """Rig 12 games so it is 6-6, then play k random tiebreak points (unfinished)."""
    while True:
        winners = []
        for g in range(12):
            w = g % 2
            loser_pts = rng.randint(0, 2)
            body = [w] * 3 + [1 - w] * loser_pts
            rng.shuffle(body)
            winners += body + [w]
        winners += [rng.randint(0, 1) for _ in range(k)]
        m = _play(winners, golden)
        if m is not None and not m.done and m.in_tb:
            return winners, m


def build_dataset(n_per_cell=5, seed=7, lengths=(10, 30, 60, 100)):
    rng = random.Random(seed)
    rows = []
    for sport in ("tennis", "padel"):
        golden = sport == "padel"
        specs = [("regular", L) for L in lengths] + [("tiebreak", None)]
        for category, L in specs:
            for i in range(n_per_cell):
                if category == "regular":
                    winners, m = regular_case(rng, golden, L)
                else:
                    winners, m = tiebreak_case(rng, golden, rng.randint(3, 8))
                for rules_given in (True, False):   # paired: same points, with/without rules
                    rows.append(dict(
                        case_id=f"{sport}-{category}-{L or 'tb'}-{i}",
                        sport=sport, category=category, n_points=len(winners),
                        rules_given=rules_given,
                        prompt=build_prompt(sport, winners, rules_given),
                        expected=m.answer(),
                    ))
    return pd.DataFrame(rows)


# %%
# ===== Answer parsing + the scored task =====
def extract_answer(text):
    hits = re.findall(r"ANSWER:\s*(.*)", text or "", flags=re.IGNORECASE)
    return hits[-1].strip() if hits else ""


def norm(s):
    return re.sub(r"[\s*`_]", "", s).upper()


@kbench.task(name="sport_state_case", store_task=False)
def case_task(llm, prompt: str, expected: str, sport: str, category: str,
              rules_given: bool, n_points: int) -> dict:
    got = extract_answer(llm.prompt(prompt))
    ok = norm(got) == norm(expected)
    kbench.assertions.assert_true(ok, expectation=f"Expected {expected}")
    return {"correct": ok, "got": got, "expected": expected, "sport": sport,
            "category": category, "rules_given": rules_given, "n_points": n_points}


# %%
# ===== Dataset: 48 cases (tennis + padel, 30/60/100 points + tiebreaks, rules shown / not shown) =====
self_test()
df = build_dataset(n_per_cell=3, lengths=(30, 60, 100))
cols = ["prompt", "expected", "sport", "category", "rules_given", "n_points"]
data = df[cols]
print(len(data), "cases")

# %%
# ===== The ONE task the leaderboard runs: accuracy over all 48 cases =====
@kbench.task(name="tennis_padel_state_tracking")
def tennis_padel_state_tracking(llm) -> float:
    """Given a point-by-point tennis or padel sequence, report sets, games, points and next server."""
    r = case_task.evaluate(llm=[llm], evaluation_data=data, n_jobs=4, timeout=300,
                           max_attempts=2, retry_delay=10, on_failure="continue")
    rows = pd.DataFrame(list(r.completed_runs.as_dataframe().result))
    return float(rows.correct.mean())

# %%
# Quick check (optional, takes ~10 min). Comment out before saving if you want a faster notebook run:
# tennis_padel_state_tracking.run(kbench.llm)

# %%
# LAST CELL - type this on its own in a new cell (it is a notebook magic, so it is not in this file):
#   %choose tennis_padel_state_tracking
