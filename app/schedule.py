# -*- coding: utf-8 -*-
"""赛程模块：时间解析、排序、上下移动、冲突检测。

冲突分两级（第二轮要求）：
- 项目时间重叠（黄色）：同一天同时段，两个项目时间差 <= 阈值分钟。
- 运动员冲突（红色）：同一运动员的两个项目时间差 <= 阈值分钟。
- check_all()：一键检测，把两种合并跑完并设置标记。
时间解析兼容全角冒号“8：40”、“8.40”等写法。
"""
from collections import defaultdict


def _to_minutes(t):
    s = str(t or "").strip()
    for ch in ("：", "．", "。", ".", "－", "-"):
        if ch in s:
            s = s.replace(ch, ":")
    s = s.replace(" ", "")
    if not s:
        return None
    parts = s.split(":")
    if len(parts) == 2:
        try:
            return int(parts[0]) * 60 + int(parts[1])
        except ValueError:
            return None
    if len(parts) == 1 and parts[0].isdigit():
        try:
            return int(parts[0]) * 60
        except ValueError:
            return None
    return None


def sort_events(events):
    """按 天 -> 上午/下午(空白最后) -> 时间 -> order 排序。"""
    def key(e):
        sess = {"上午": 0, "下午": 1}.get(e.session, 2)
        return (e.day or "zzz", sess, e.time or "99:99", e.order)
    return sorted(events, key=key)


def move_event(events, eid, direction):
    ordered = sort_events(events)
    idx = next((i for i, e in enumerate(ordered) if e.eid == eid), None)
    if idx is None:
        return False
    target = ordered[idx]
    group = [e for e in ordered
             if (e.day, e.session, e.time) == (target.day, target.session, target.time)]
    gi = group.index(target)
    ni = gi + direction
    if 0 <= ni < len(group):
        group[gi], group[ni] = group[ni], group[gi]
        for k, e in enumerate(group):
            e.order = k
        return True
    return False


def detect_event_overlaps(events, threshold_minutes=20):
    """项目时间重叠（黄色）。返回 {项目名: [重叠的其他项目名...]}。

    说明：同时段（上午/下午都填了才比）且同一天才比较；空白时段不比。
    """
    res = {}
    evs = [e for e in events
           if e.day and e.session and _to_minutes(e.time) is not None]
    for i in range(len(evs)):
        for j in range(i + 1, len(evs)):
            a, b = evs[i], evs[j]
            if a.day == b.day and a.session == b.session \
                    and abs(_to_minutes(a.time) - _to_minutes(b.time)) <= threshold_minutes:
                res.setdefault(a.name, []).append(b.name)
                res.setdefault(b.name, []).append(a.name)
    return res


def detect_conflicts(records, events, threshold_minutes=20):
    """运动员冲突（红色）。返回冲突记录 id 集合。"""
    conflict_ids = set()
    person_events = defaultdict(set)
    for r in records:
        if r.person and r.event:
            person_events[(r.class_name, r.person)].add(r.event)
    ev_time = {}
    for e in events:
        if e.time:
            ev_time[e.name] = (e.day, _to_minutes(e.time))

    for r in records:
        r.conflict = False

    for (cls, person), evs in person_events.items():
        evs = [e for e in evs if e in ev_time and ev_time[e][1] is not None]
        evs = sorted(evs, key=lambda e: ev_time[e])
        for i in range(len(evs)):
            for j in range(i + 1, len(evs)):
                d1, t1 = ev_time[evs[i]]
                d2, t2 = ev_time[evs[j]]
                if d1 == d2 and t1 is not None and t2 is not None \
                        and abs(t1 - t2) <= threshold_minutes:
                    for r in records:
                        if r.class_name == cls and r.person == person \
                                and r.event in (evs[i], evs[j]):
                            r.conflict = True
                            conflict_ids.add(r.rid)
    return conflict_ids


def check_all(records, events, threshold_minutes=20):
    """一键检测：运动员冲突（红）+ 项目重叠（黄）。

    返回 (conflict_ids, overlaps_dict, report_text)。
    """
    conflict_ids = detect_conflicts(records, events, threshold_minutes)
    overlaps = detect_event_overlaps(events, threshold_minutes)
    for e in events:
        e.overlap = e.name in overlaps
    people = sorted({(r.class_name, r.person) for r in records if r.conflict})
    lines = []
    if people:
        lines.append(f"运动员时间冲突（红色）{len(people)} 人：")
        for c, p in people:
            evs = [r.event for r in records
                   if r.conflict and r.class_name == c and r.person == p]
            lines.append(f"  {c} {p}：{'、'.join(sorted(set(evs)))}")
    if overlaps:
        lines.append(f"项目时间重叠（黄色）{len(overlaps)} 个：")
        for name, others in overlaps.items():
            lines.append(f"  {name} 与 {'、'.join(sorted(set(others)))} 时间过近")
    if not lines:
        lines.append("未发现冲突。")
    return conflict_ids, overlaps, "\n".join(lines)
