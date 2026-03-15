#!/usr/bin/env python3
import json
import sys

# Parameters
OFFSET = {'SOFT': -1.65, 'MEDIUM': 0.0, 'HARD': 1.05}
DEG    = {'SOFT': 0.3,  'MEDIUM': 0.1,  'HARD': 0.005}
THRESH = {'SOFT': 2,     'MEDIUM': 10,   'HARD': 28}
TEMP_EXP = 0.3


def simulate(race):
    config     = race['race_config']
    strategies = race['strategies']
    base       = config['base_lap_time']
    pit_time   = config['pit_lane_time']
    temp       = config['track_temp']
    n_laps     = config['total_laps']
    temp_scale = (temp / 30.0) ** TEMP_EXP

    driver_times = {}
    for pos_key, strat in strategies.items():
        driver_id   = strat['driver_id']
        pit_stops   = {ps['lap']: ps['to_tire'] for ps in strat['pit_stops']}
        current     = strat['starting_tire']
        tire_age    = 0
        total       = 0.0

        for lap in range(1, n_laps + 1):
            tire_age += 1
            eff_age   = max(0, tire_age - THRESH[current])
            deg       = DEG[current] * eff_age * temp_scale
            total    += base + OFFSET[current] + deg
            if lap in pit_stops:
                current  = pit_stops[lap]
                tire_age = 0
                total   += pit_time

        driver_times[driver_id] = total

    finishing = sorted(driver_times, key=driver_times.__getitem__)
    return {'race_id': race['race_config']['race_id'], 'finishing_positions': finishing}


if __name__ == '__main__':
    race = json.load(sys.stdin)
    print(json.dumps(simulate(race)))
