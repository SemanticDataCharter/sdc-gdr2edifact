"""A UN/EDIFACT interchange from placements, ordered and checked by the directory.

The writer knows the syntax (ISO 9735) and the directory, and nothing about any model: the mapping file says where each
value goes, the directory's message specification says which segments and segment groups a message has, in what
order, how often each may repeat and which are mandatory, and its segment definitions say which data elements and
components a segment has, which are mandatory and how long each may be.

A message is written as a tree before it is a sequence of segments. Its root is the message type (`DESADV`); a segment
group is `SG<n>`, a segment its tag; a name may carry a qualifier after `~` (`DTM~137`, `SG1~ON`) to tell apart
segments of the same tag, which the writer drops. A segment's data are attributes, named by the directory: a simple
data element by its tag (`@3035`), a component by its composite and its tag (`@C082.3039`), a component that recurs in
its composite by its occurrence (`@C080.3036#2`). An attribute ending in `+` appends to the value already there (a
time after a date in one DTM). The interchange header is the pseudo-segment `UNB` under the root.

From those the writer
- orders every group's segments and groups as the message specification does, repeats by the declared order of the
  clusters that made them, else the record's;
- adds the trigger segment of a group when the record has nothing for it and the segment has no mandatory data
  (an empty PCI), and numbers CPS hierarchies (`#seq`);
- removes a segment that lacks mandatory data, and a group that lacks its trigger, and says which values went with
  it and why, rather than write a message that does not conform;
- continues a value too long for its component into the components of the same tag that follow it (a name over
  35 characters into the next 3036), and refuses one that does not fit at all, with the reason;
- infers a DTM's format qualifier (2379) from the value written: 102 for a date, 203 and 204 for a date and time;
- writes UNA, UNB, UNH, UNS where the message has it, UNT with the segment count, and UNZ.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from sdc_mapper import JOIN, MappingError

from .directory import Directory

REPR = re.compile(r"^(an|a|n)(\.\.)?(\d+)$")
DEFAULT_SYNTAX = ("UNOC", "3")
SERVICE = {"component": ":", "element": "+", "decimal": ".", "release": "?", "repetition": " ", "terminator": "'"}


def base(name: str) -> str:
    return name.split("~", 1)[0]


@dataclass
class Node:
    name: str
    key: tuple
    attrs: dict[str, str] = field(default_factory=dict)
    attr_positions: dict[str, int] = field(default_factory=dict)   # the value whose own text an attribute holds
    children: list["Node"] = field(default_factory=list)
    positions: set[int] = field(default_factory=set)
    item: int = -1                     # its position in the message specification, once checked
    group: bool = False

    def subtree_positions(self) -> set[int]:
        out = set(self.positions) | set(self.attr_positions.values())
        for c in self.children:
            out |= c.subtree_positions()
        return out


class Builder:
    def __init__(self, directory: Directory, message: str, order: dict[str, int] | None = None):
        self.d = directory
        self.message = message
        self.spec = directory.message(message)
        self.order = order or {}
        self.root: Node | None = None
        self.index: dict[tuple, Node] = {}
        self.appends: list[tuple] = []
        self.pruned: dict[int, str] = {}      # value position -> why it is not in the message

    # ------------------------------------------------------------ building
    def ensure(self, steps) -> Node:
        if not steps:
            raise MappingError("a placement with no target segment")
        name = steps[0][0]
        if self.root is None:
            if name != self.message:
                raise MappingError(f"the message is {self.message}, not {name}")
            self.root = Node(name, ())
        elif self.root.name != name:
            raise MappingError(f"one message, one root: {self.root.name} and {name}")
        node = self.root
        for name, key in steps[1:]:
            if key == JOIN:
                found = [c for c in node.children if c.name == name]
                if len(found) > 1:
                    raise MappingError(f"'={name}' under {node.name}: {len(found)} of that name, so which is not settled")
                if found:
                    node = found[0]
                    continue
            k = (id(node), name, key)
            child = self.index.get(k)
            if child is None:
                child = Node(name, key)
                node.children.append(child)
                self.index[k] = child
            node = child
        return node

    def ensure_under(self, parent: Node, step) -> Node:
        name, key = step
        k = (id(parent), name, key)
        if k not in self.index:
            child = Node(name, key)
            parent.children.append(child)
            self.index[k] = child
        return self.index[k]

    def find(self, steps, loose: bool = False) -> Node | None:
        """The element at steps; `loose`, the only element of a step's name where its key finds none (a group a join
        made before the cluster that names it was placed)."""
        if self.root is None or not steps or self.root.name != steps[0][0]:
            return None
        node = self.root
        for name, key in steps[1:]:
            found = [c for c in node.children if c.name == name]
            if key == JOIN:
                node = found[0] if len(found) == 1 else None
            else:
                node = self.index.get((id(node), name, key)) or (found[0] if loose and len(found) == 1 else None)
            if node is None:
                return None
        return node

    def put(self, steps, attribute: str | None, text: str, position: int | None = None) -> Node:
        if not attribute:
            raise MappingError(f"{'/'.join(n for n, _ in steps)}: a value goes in a data element or component "
                               "(an '@' step), not in a segment or group")
        node = self.ensure(steps)
        if attribute.endswith("+"):
            self.appends.append((node, attribute[:-1], text, position))
            return node
        old = node.attrs.get(attribute)
        if old is not None and old != text:
            raise MappingError(f"two values for {'/'.join(n for n, _ in steps)}/@{attribute}: give one its own segment "
                               "('+' or a '~' qualifier)")
        node.attrs[attribute] = text
        if position is not None:
            node.attr_positions[attribute] = position
            node.positions.add(position)
        return node

    # ------------------------------------------------------------ against the directory
    def segments(self) -> list[tuple[str, list[list[str]]]]:
        """The message, UNH to UNT, as segments; and the interchange header's attributes."""
        if self.root is None:
            raise MappingError("nothing to write: no value of the record reached the message")
        for node, attribute, text, position in self.appends:
            node.attrs[attribute] = node.attrs.get(attribute, "") + text
            if position is not None:
                node.positions.add(position)
        self.unb = next((c for c in self.root.children if c.name == "UNB"), None)
        self.root.children = [c for c in self.root.children if c.name != "UNB"]
        ok, why = self._group(self.root, self.spec["segment_table"], self.message)
        if not ok:
            raise MappingError(f"the {self.message} cannot be written: {why}")
        out: list[tuple[str, list[list[str]]]] = []
        seq: dict[str, int] = {}
        self._emit(self.root, out, seq)
        return out

    @staticmethod
    def _item_for(child: Node, items: list) -> int | None:
        name = base(child.name)
        for i, it in enumerate(items):
            if ("items" in it and name == f"SG{it['group']}") or ("items" not in it and name == it["tag"]):
                return i
        return None

    def _group(self, node: Node, items: list, where: str) -> tuple[bool, str]:
        kept: list[tuple[Node, int]] = []
        for child in node.children:
            i = self._item_for(child, items)
            if i is None:
                raise MappingError(f"{base(child.name)} is not part of {where} in the {self.message} of {self.d.version}")
            it = items[i]
            if "items" in it:
                ok, why = self._group(child, it["items"], f"{where}/SG{it['group']}")
            else:
                ok, why = self._segment(child)
            if ok:
                kept.append((child, i))
            else:
                for p in child.subtree_positions():
                    self.pruned.setdefault(p, why)
        counts: dict[int, int] = {}
        for _, i in kept:
            counts[i] = counts.get(i, 0) + 1
            if counts[i] > items[i]["repeat"]:
                it = items[i]
                label = f"SG{it['group']}" if "items" in it else it["tag"]
                raise MappingError(f"{self.d.version} allows {it['repeat']} {label} in {where}; the mapping places more")
        for i, it in enumerate(items):
            if counts.get(i) or it.get("tag") in ("UNH", "UNT", "UNS"):
                continue
            label = f"SG{it['group']}" if "items" in it else it["tag"]
            if i == 0 and node is not self.root:          # the group's trigger
                filled = self._fill(it)
                if filled is None:
                    return False, f"{it['tag']} must open {where.split('/')[-1]}, and the record has no value for it"
                kept.append((filled, 0))
                counts[0] = 1
            elif it["status"] == "M":
                return False, f"{self.d.version} requires {label} in {where}, and the record has no value for it"
        if not kept:
            return False, f"{where} has nothing in it"
        kept.sort(key=lambda ci: (ci[1], self._rank(ci[0].key)))
        for c, i in kept:
            c.item, c.group = i, "items" in items[i]
        node.children = [c for c, _ in kept]
        return True, ""

    def _fill(self, it) -> Node | None:
        """A trigger segment the writer can write with no value of the record: no mandatory data, or only a CPS's
        hierarchical number."""
        spec = self.d.segments[it["tag"]]
        node = Node(it["tag"], ("fill",))
        for e in spec["elements"]:
            if e["status"] != "M":
                continue
            if it["tag"] == "CPS" and e["tag"] == "7164":
                node.attrs["7164"] = "#seq"
                continue
            return None
        return node

    def _rank(self, key: tuple) -> tuple:
        return tuple(self.order[part[0]] for part in key
                     if isinstance(part, tuple) and len(part) == 2 and part[0] in self.order)

    # ------------------------------------------------------------ a segment
    def _slots(self, tag: str) -> dict[str, tuple[int, int | None, dict]]:
        """Attribute name -> (element index, component index or None, definition) for a segment."""
        spec = self.d.segments.get(tag)
        if spec is None:
            raise MappingError(f"{tag} is not a segment of {self.d.version}")
        slots: dict[str, tuple[int, int | None, dict]] = {}
        seen: dict[str, int] = {}
        for ei, e in enumerate(spec["elements"]):
            seen[e["tag"]] = seen.get(e["tag"], 0) + 1
            name = e["tag"] + (f"#{seen[e['tag']]}" if seen[e["tag"]] > 1 else "")   # PIA's second C212 is C212#2
            if e["components"]:
                cseen: dict[str, int] = {}
                for ci, c in enumerate(e["components"]):
                    cseen[c["tag"]] = cseen.get(c["tag"], 0) + 1
                    n = cseen[c["tag"]]
                    slots[f"{name}.{c['tag']}" + (f"#{n}" if n > 1 else "")] = (ei, ci, c)
            else:
                slots[name] = (ei, None, e)
        return slots

    @staticmethod
    def _limit(repr_: str) -> tuple[str, int, bool] | None:
        m = REPR.match(repr_ or "")
        return (m.group(1), int(m.group(3)), bool(m.group(2))) if m else None

    @staticmethod
    def _length(kind: str, value: str) -> int:
        return len(re.sub(r"[^0-9]", "", value)) if kind == "n" else len(value)

    def _segment(self, node: Node) -> tuple[bool, str]:
        tag = base(node.name)
        if node.children:
            raise MappingError(f"{tag} is a segment: it holds data elements, not {node.children[0].name}")
        slots = self._slots(tag)
        unknown = [a for a in node.attrs if a not in slots]
        if unknown:
            raise MappingError(f"{tag} has no {unknown[0]} in {self.d.version}")
        if tag == "DTM" and node.attrs.get("C507.2380") and "C507.2379" not in node.attrs:
            fmt = {8: "102", 12: "203", 14: "204"}.get(len(node.attrs["C507.2380"]))
            if fmt:
                node.attrs["C507.2379"] = fmt
        # a value longer than its component: continued into the components of the same tag that follow, else refused
        for attr in list(node.attrs):
            ei, ci, d = slots[attr]
            lim = self._limit(d["repr"])
            value = node.attrs[attr]
            if not lim or value == "#seq" or self._length(lim[0], value) <= lim[1]:
                continue
            kind, size, _ = lim
            follow = [a for a, (e2, c2, d2) in slots.items() if e2 == ei and c2 is not None and ci is not None
                      and c2 > ci and d2["tag"] == d["tag"] and a not in node.attrs]
            pieces = [value[i:i + size] for i in range(0, len(value), size)]
            if kind != "n" and len(pieces) <= 1 + len(follow):
                node.attrs[attr] = pieces[0]
                for a, piece in zip(follow, pieces[1:]):
                    node.attrs[a] = piece
                continue
            p = node.attr_positions.pop(attr, None)
            del node.attrs[attr]
            if p is not None:
                self.pruned.setdefault(p, f"{tag} {attr} holds at most {d['repr']}; the value is {len(value)} long")
        spec = self.d.segments[tag]
        for ei, e in enumerate(spec["elements"]):
            present = {a for a, (e2, _, _) in slots.items() if e2 == ei and a in node.attrs}
            if e["status"] == "M" and not present:
                return False, f"{tag} requires {e['tag']} ({e['name']}), and the record has no value for it"
            if e["components"] and present:
                for a, (e2, c2, d2) in slots.items():
                    if e2 == ei and d2["status"] == "M" and a not in node.attrs:
                        return False, f"{tag} {e['tag']} requires {d2['tag']} ({d2['name']}), and the record has no value for it"
        if not node.attrs:
            return False, f"{tag} has nothing in it"
        return True, ""

    def _emit(self, node: Node, out: list, seq: dict):
        uns = None
        if node is self.root:      # UNS, where the message has one: between the detail and the summary
            uns = next((i for i, it in enumerate(self.spec["segment_table"]) if it.get("tag") == "UNS"), None)
        for child in node.children:
            if uns is not None and child.item > uns:
                out.append(("UNS", [["S"]]))
                uns = None
            if child.group:
                self._emit(child, out, seq)
                continue
            tag = base(child.name)
            slots = self._slots(tag)
            spec = self.d.segments[tag]
            elements: list[list[str]] = [[""] * max(1, len(e["components"])) for e in spec["elements"]]
            for attr, value in child.attrs.items():
                if value == "#seq":
                    seq[tag] = seq.get(tag, 0) + 1
                    value = str(seq[tag])
                ei, ci, _ = slots[attr]
                elements[ei][ci or 0] = value
            out.append((tag, elements))
        if uns is not None:
            out.append(("UNS", [["S"]]))

    # ------------------------------------------------------------ the interchange
    def interchange(self, syntax: tuple[str, str] = DEFAULT_SYNTAX) -> str:
        body = self.segments()
        bgm = next((els for t, els in body if t == "BGM"), None)
        ref = re.sub(r"\W", "", (bgm[1][0] if bgm and len(bgm) > 1 and bgm[1] else "") or "")[-14:] or "1"
        u = self.unb.attrs if self.unb is not None else {}
        for need, what in (("S002.0004", "the sender's identification"), ("S003.0010", "the recipient's identification"),
                           ("S004.0017", "the date of preparation"), ("S004.0019", "the time of preparation")):
            if not u.get(need):
                raise MappingError(f"UNB requires {need} ({what}), and the record has no value for it")
        mt = self.spec
        segs = [("UNB", [[syntax[0], syntax[1]], [u["S002.0004"], u.get("S002.0007", "")],
                         [u["S003.0010"], u.get("S003.0007", "")], [u["S004.0017"], u["S004.0019"]], [u.get("0020", ref)]]),
                ("UNH", [[ref], [self.message, mt["version"] or "D", mt["release"] or self.d.version[2:], mt["agency"] or "UN"]])]
        segs += body
        segs.append(("UNT", [[str(len(body) + 2)], [ref]]))
        segs.append(("UNZ", [["1"], [u.get("0020", ref)]]))
        return serialize(segs, syntax[0])


def escape(value: str) -> str:
    out = []
    for ch in value:
        if ch in (SERVICE["component"], SERVICE["element"], SERVICE["release"], SERVICE["terminator"]):
            out.append(SERVICE["release"])
        out.append(ch)
    return "".join(out)


def serialize(segments, charset: str = "UNOC") -> str:
    """Segments to an interchange, one segment to a line; trailing empty components and elements dropped."""
    s = SERVICE
    lines = [f"UNA{s['component']}{s['element']}{s['decimal']}{s['release']}{s['repetition']}{s['terminator']}"]
    for tag, elements in segments:
        els = []
        for comps in elements:
            comps = [escape(c or "") for c in comps]
            while comps and comps[-1] == "":
                comps.pop()
            els.append(s["component"].join(comps))
        while els and els[-1] == "":
            els.pop()
        lines.append(tag + (s["element"] + s["element"].join(els) if els else "") + s["terminator"])
    text = "\n".join(lines) + "\n"
    if charset == "UNOC":
        try:
            text.encode("latin-1")
        except UnicodeEncodeError as e:
            raise MappingError(f"a value holds {text[e.start]!r}, which the UNOC character set (ISO 8859-1) cannot") from e
    return text
