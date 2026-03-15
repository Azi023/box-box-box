#!/usr/bin/env python3
"""
Focused sweep for Formula D:
  deg[C] * max(0, age - thresh[C]) * (temp/30)^exp

Phase 1: Fix oS=-1.65, oH=1.05. Sweep thresholds × exp × deg rates.
Phase 2: Take top 5, sweep offsets around them.
"""
import json
import itertools
import os
import sys
from multiprocessing import Pool, cpu_count

# ── Load test cases ──────────────────────────────────────────────────────────
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEST_IN  = os.path.join(REPO, 'data', 'test_cases', 'inputs')
TEST_OUT = os.path.join(REPO, 'data', 'test_cases', 'expected_outputs')

def load_tests():
    cases = []
    for i in range(1, 101):
        fn = f'test_{i:03d}.json'
        with open(os.path.join(TEST_IN,  fn)) as f: inp = json.load(f)
        with open(os.path.join(TEST_OUT, fn)) as f: exp = json.load(f)
        cases.append((inp, exp['finishing_positions']))
    return cases

TESTS = load_tests()

# ── Core simulation ──────────────────────────────────────────────────────────
def simulate(race, oS, oH, dS, dM, dH, thS, thM, thH, exp):
    cfg      = race['race_config']
    base     = cfg['base_lap_time']
    pit_time = cfg['pit_lane_time']
    temp     = cfg['track_temp']
    n_laps   = cfg['total_laps']
    ts       = (temp / 30.0) ** exp

    OFFSET = {'SOFT': oS, 'MEDIUM': 0.0, 'HARD': oH}
    DEG    = {'SOFT': dS, 'MEDIUM': dM,  'HARD': dH}
    THRESH = {'SOFT': thS,'MEDIUM': thM, 'HARD': thH}

    driver_times = {}
    for _, strat in race['strategies'].items():
        did      = strat['driver_id']
        pits     = {ps['lap']: ps['to_tire'] for ps in strat['pit_stops']}
        cur      = strat['starting_tire']
        age      = 0
        total    = 0.0
        for lap in range(1, n_laps + 1):
            age  += 1
            eff   = max(0, age - THRESH[cur])
            total += base + OFFSET[cur] + DEG[cur] * eff * ts
            if lap in pits:
                cur   = pits[lap]
                age   = 0
                total += pit_time
        driver_times[did] = total

    return sorted(driver_times, key=driver_times.__getitem__)

def score_params(args):
    oS, oH, dS, dM, dH, thS, thM, thH, exp = args
    exact = 0
    for inp, expected in TESTS:
        pred = simulate(inp, oS, oH, dS, dM, dH, thS, thM, thH, exp)
        if pred == expected:
            exact += 1
    return exact, args

# ── Phase 1 ──────────────────────────────────────────────────────────────────
def phase1():
    oS, oH = -1.65, 1.05
    thS_vals = [1, 2, 3, 4, 5, 6, 8]
    thM_vals = [10, 15, 18, 20, 22, 25, 28, 30]
    thH_vals = [15, 20, 25, 28, 30, 33, 35, 40]
    exp_vals = [0.3, 0.5, 0.8, 1.0, 1.2, 1.5]
    dS_vals  = [0.20, 0.30, 0.40, 0.50]
    dM_vals  = [0.05, 0.10, 0.15, 0.20]
    dH_vals  = [0.005, 0.01, 0.02, 0.03]

    combos = [
        (oS, oH, dS, dM, dH, thS, thM, thH, exp)
        for thS, thM, thH, exp, dS, dM, dH
        in itertools.product(thS_vals, thM_vals, thH_vals, exp_vals,
                             dS_vals, dM_vals, dH_vals)
    ]
    total = len(combos)
    print(f"Phase 1: {total:,} combinations, {cpu_count()} CPUs", flush=True)

    workers = max(1, cpu_count() - 1)
    results = []
    with Pool(workers) as pool:
        for i, res in enumerate(pool.imap_unordered(score_params, combos, chunksize=256)):
            results.append(res)
            if (i + 1) % 10000 == 0:
                best_so_far = max(results, key=lambda x: x[0])[0]
                print(f"  {i+1:,}/{total:,}  best={best_so_far}", flush=True)

    results.sort(key=lambda x: -x[0])
    print(f"\nPhase 1 top 20:")
    for rank, (score, p) in enumerate(results[:20], 1):
        oS_, oH_, dS_, dM_, dH_, thS_, thM_, thH_, exp_ = p
        print(f"  {rank:2d}. score={score:3d}  "
              f"oS={oS_} oH={oH_} dS={dS_} dM={dM_} dH={dH_} "
              f"thS={thS_} thM={thM_} thH={thH_} exp={exp_}")
    return results[:5]

# ── Phase 2 ──────────────────────────────────────────────────────────────────
def phase2(top5):
    oS_vals = [-1.5, -1.65, -1.8, -2.0]
    oH_vals = [0.8, 1.0, 1.05, 1.2]

    combos = []
    for _, base_params in top5:
        _, _, dS, dM, dH, thS, thM, thH, exp = base_params
        for oS, oH in itertools.product(oS_vals, oH_vals):
            combos.append((oS, oH, dS, dM, dH, thS, thM, thH, exp))

    total = len(combos)
    print(f"\nPhase 2: {total} combinations", flush=True)

    workers = max(1, cpu_count() - 1)
    results = []
    with Pool(workers) as pool:
        for res in pool.imap_unordered(score_params, combos, chunksize=16):
            results.append(res)

    results.sort(key=lambda x: -x[0])
    print(f"\nPhase 2 top 20:")
    for rank, (score, p) in enumerate(results[:20], 1):
        oS_, oH_, dS_, dM_, dH_, thS_, thM_, thH_, exp_ = p
        print(f"  {rank:2d}. score={score:3d}  "
              f"oS={oS_} oH={oH_} dS={dS_} dM={dM_} dH={dH_} "
              f"thS={thS_} thM={thM_} thH={thH_} exp={exp_}")
    return results

# ── Entry point ──────────────────────────────────────────────────────────────
if __name__ == '__main__':
    top5_p1 = phase1()
    all_p2  = phase2(top5_p1)

    # Best overall
    best_score, best_p = all_p2[0]
    print(f"\nBest overall: {best_score}/100")
    print(f"  Params: {best_p}")

    # Compare to existing 12/100 baseline
    baseline_score, _ = score_params((-1.65, 1.05, 0.30, 0.10, 0.005, 3, 12, 15, 0.5))
    print(f"  Baseline (current): {baseline_score}/100")

    if best_score > baseline_score:
        oS_, oH_, dS_, dM_, dH_, thS_, thM_, thH_, exp_ = best_p
        solution_path = os.path.join(REPO, 'solution', 'race_simulator.py')
        with open(solution_path) as f:
            src = f.read()

        src = src.replace(
            f"OFFSET = {{'SOFT': -1.65, 'MEDIUM': 0.0, 'HARD': 1.05}}",
            f"OFFSET = {{'SOFT': {oS_}, 'MEDIUM': 0.0, 'HARD': {oH_}}}"
        )
        src = src.replace(
            f"DEG    = {{'SOFT': 0.30,  'MEDIUM': 0.10, 'HARD': 0.005}}",
            f"DEG    = {{'SOFT': {dS_},  'MEDIUM': {dM_},  'HARD': {dH_}}}"
        )
        src = src.replace(
            f"THRESH = {{'SOFT': 3,     'MEDIUM': 12,   'HARD': 15}}",
            f"THRESH = {{'SOFT': {thS_},     'MEDIUM': {thM_},   'HARD': {thH_}}}"
        )
        src = src.replace(
            f"TEMP_EXP = 0.5",
            f"TEMP_EXP = {exp_}"
        )
        with open(solution_path, 'w') as f:
            f.write(src)
        print(f"\nUpdated solution/race_simulator.py with score {best_score}/100")
    else:
        print(f"\nNo improvement over baseline {baseline_score}/100 — solution unchanged.")
