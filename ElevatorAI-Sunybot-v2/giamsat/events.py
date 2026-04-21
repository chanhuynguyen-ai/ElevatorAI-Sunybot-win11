# events.py
from dataclasses import dataclass, field
from typing import Dict, List, Tuple
import config


@dataclass
class EventState:
    tid_hold_last_fire: Dict[int, float] = field(default_factory=dict)


def detect_bottle_holding(tracks, bottles):
    tid_holding = {int(t[4]): False for t in tracks} if len(tracks) else {}
    if not len(tracks) or not bottles:
        return tid_holding

    for x1, y1, x2, y2, tid in tracks:
        tid = int(tid)
        pcx = (x1 + x2) / 2
        pcy = (y1 + y2) / 2
        pw = (x2 - x1) + 1e-6

        hold = False
        for bx1, by1, bx2, by2, _score in bottles:
            bcx = (bx1 + bx2) / 2
            bcy = (by1 + by2) / 2
            dist = ((bcx - pcx) ** 2 + (bcy - pcy) ** 2) ** 0.5
            if dist <= config.HOLD_DIST_RATIO * pw:
                hold = True
                break
        tid_holding[tid] = hold

    return tid_holding


def fire_events(es: EventState, now: float, tid_holding: Dict[int, bool]) -> List[Tuple[str, int]]:
    fired: List[Tuple[str, int]] = []
    for tid, hold in tid_holding.items():
        if not hold:
            continue
        last = es.tid_hold_last_fire.get(tid, 0.0)
        if now - last >= config.HOLD_COOLDOWN_SEC:
            fired.append(("bottle", tid))
            es.tid_hold_last_fire[tid] = now
    return fired