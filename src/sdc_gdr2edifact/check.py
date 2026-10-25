"""An interchange checked against the directory, from its text, by code that shares nothing with the writer.

    errors = check(text, Directory.load())        # [] when the interchange conforms

The text is parsed afresh (the UNA service string, the release character, segments, data elements, components); the
envelope is checked (UNB first and UNZ last, one UNH to UNT message, UNT's segment count and UNZ's message count,
matching control references); the message's segment sequence is matched against the message specification's segment
table by a recursive descent over its positions (a segment position takes up to its repeat count of segments, a group
opens on its trigger segment and repeats up to its count, a mandatory position missing is an error, a segment nothing
takes is an error); and every segment against its definition (known tag, no more data elements or components than
defined, mandatory ones present, lengths and numeric representations within the directory's).
"""
from __future__ import annotations

import re

from .directory import Directory

REPR = re.compile(r"^(an|a|n)(\.\.)?(\d+)$")


def parse(text: str) -> list[tuple[str, list[list[str]]]]:
    text = text.lstrip()
    comp, elem, rel, term = ":", "+", "?", "'"
    if text.startswith("UNA"):
        comp, elem, rel, term = text[3], text[4], text[6], text[8]
        text = text[9:]
    segments, cur, comps, elements, tag = [], [], [], [], None
    i = 0
    while i < len(text):
        ch = text[i]
        if ch == rel and i + 1 < len(text):
            cur.append(text[i + 1])
            i += 2
            continue
        if ch in "\r\n" and not cur and tag is None:
            i += 1
            continue
        if ch == elem or ch == term:
            if tag is None:
                tag = "".join(cur).strip()
            else:
                comps.append("".join(cur))
                elements.append(comps)
            cur, comps = [], []
            if ch == term:
                segments.append((tag, elements))
                tag, elements = None, []
        elif ch == comp and tag is not None:
            comps.append("".join(cur))
            cur = []
        else:
            cur.append(ch)
        i += 1
    if tag is not None or cur:
        segments.append(("?", [["".join(cur)]]))
    return segments


def _value(elements, i, j=0) -> str:
    return elements[i][j] if i < len(elements) and j < len(elements[i]) else ""


def check(text: str, d: Directory) -> list[str]:
    segs = parse(text)
    errors: list[str] = []
    tags = [t for t, _ in segs]
    if not segs or tags[0] != "UNB" or tags[-1] != "UNZ":
        return ["an interchange starts with UNB and ends with UNZ"]
    if tags.count("UNH") != 1 or tags.count("UNT") != 1:
        return [f"one message expected; {tags.count('UNH')} UNH and {tags.count('UNT')} UNT"]
    h, t = tags.index("UNH"), tags.index("UNT")
    msg = segs[h:t + 1]
    unb, unh, unt, unz = segs[0][1], segs[h][1], segs[t][1], segs[-1][1]
    if _value(unt, 0) != str(len(msg)):
        errors.append(f"UNT counts {_value(unt, 0)} segments; the message has {len(msg)}")
    if _value(unt, 1) != _value(unh, 0):
        errors.append("UNT's message reference differs from UNH's")
    if _value(unz, 0) != "1" or _value(unz, 1) != _value(unb, 4):
        errors.append("UNZ's count or control reference does not match the interchange")
    for k, (i, j) in enumerate(((0, 0), (0, 1), (1, 0), (2, 0), (3, 0), (3, 1), (4, 0))):
        if not _value(unb, i, j):
            errors.append(f"UNB is missing its mandatory data at element {i + 1}, component {j + 1}")
    name = _value(unh, 1, 0)
    spec = d.messages.get(name)
    if spec is None:
        return errors + [f"{name} is not a message of {d.version}"]
    if (_value(unh, 1, 1), _value(unh, 1, 2), _value(unh, 1, 3)) != (spec["version"], spec["release"], spec["agency"]):
        errors.append(f"UNH names {':'.join(unh[1][1:4])}, the directory {spec['version']}:{spec['release']}:{spec['agency']}")
    errors += _table(spec["segment_table"], msg, name)
    errors += _segments(msg, d)
    return errors


def _table(table, segs, name) -> list[str]:
    errors: list[str] = []

    def match(items, i, where):
        for it in items:
            if "items" in it:
                trigger, n = it["items"][0]["tag"], 0
                while i < len(segs) and segs[i][0] == trigger and n < it["repeat"]:
                    i = match(it["items"], i, f"{where}/SG{it['group']}")
                    n += 1
                if n == 0 and it["status"] == "M":
                    errors.append(f"{where}: mandatory segment group {it['group']} is missing")
            else:
                n = 0
                while i < len(segs) and segs[i][0] == it["tag"] and n < it["repeat"]:
                    i += 1
                    n += 1
                if n == 0 and it["status"] == "M":
                    errors.append(f"{where}: mandatory segment {it['tag']} is missing")
        return i

    i = match(table, 0, name)
    if i < len(segs):
        errors.append(f"{name}: segment {i + 1} ({segs[i][0]}) is not where the segment table allows it")
    return errors


def _repr(value, repr_, where) -> list[str]:
    m = REPR.match(repr_ or "")
    if not m:
        return []
    kind, variable, size = m.group(1), m.group(2), int(m.group(3))
    length = len(re.sub(r"[^0-9]", "", value)) if kind == "n" else len(value)
    if length > size or (not variable and length != size):
        return [f"{where}: {length} characters, representation {repr_}"]
    if kind == "n" and not re.fullmatch(r"-?\d+(\.\d+)?", value):
        return [f"{where}: '{value[:20]}' is not numeric ({repr_})"]
    return []


def _segments(segs, d: Directory) -> list[str]:
    errors: list[str] = []
    for k, (tag, elements) in enumerate(segs, 1):
        if tag in ("UNH", "UNT", "UNS"):
            continue
        spec = d.segments.get(tag)
        if spec is None:
            errors.append(f"segment {k}: {tag} is not a segment of {d.version}")
            continue
        defs = spec["elements"]
        if len(elements) > len(defs):
            errors.append(f"segment {k} ({tag}): {len(elements)} data elements; {len(defs)} defined")
        for j, e in enumerate(defs):
            given = elements[j] if j < len(elements) else []
            present = any(c != "" for c in given)
            if e["status"] == "M" and not present:
                errors.append(f"segment {k} ({tag}): mandatory {e['tag']} is missing")
            if not present:
                continue
            if e["components"]:
                if len(given) > len(e["components"]):
                    errors.append(f"segment {k} ({tag}) {e['tag']}: {len(given)} components; {len(e['components'])} defined")
                for c, cd in enumerate(e["components"]):
                    v = given[c] if c < len(given) else ""
                    if cd["status"] == "M" and v == "":
                        errors.append(f"segment {k} ({tag}) {e['tag']}: mandatory {cd['tag']} is missing")
                    elif v:
                        errors += _repr(v, cd["repr"], f"segment {k} ({tag}) {e['tag']}/{cd['tag']}")
            else:
                if len(given) > 1:
                    errors.append(f"segment {k} ({tag}) {e['tag']} is a simple data element; it has components")
                errors += _repr(given[0], e["repr"], f"segment {k} ({tag}) {e['tag']}")
    return errors
