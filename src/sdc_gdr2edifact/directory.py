"""The UN/EDIFACT directory: read from the archive UNECE publishes, never shipped with this package.

UNECE licenses each directory (UNTDID: the data elements EDED, composites EDCD, segments EDSD, code lists UNCL and
message specifications EDMD) for use within the organization that downloads it, and lets the original file be passed
on with its license; a modified directory may not be distributed. So this package carries no part of a directory:

    d = Directory.load()                              # $SDC_EDIFACT_DIRECTORY, or a path given to load()
    d = Directory.load("/data/edifact/d24a.zip")      # the zip downloaded from unece.org, unchanged

The archive is read as downloaded (its parts are zips inside the zip), extracted in memory, and the extraction kept as
a working copy in the user's cache directory, keyed by the archive's SHA-256, for use on that machine.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import re
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import ClassVar

ENV = "SDC_EDIFACT_DIRECTORY"
EXTRACTION = 2          # the extraction's own version: a change to how the text files are read is a new cache entry
DASH = re.compile(r"^-{20,}\s*$")


class DirectoryNotFound(Exception):
    pass


def _cache_dir() -> Path:
    base = os.environ.get("XDG_CACHE_HOME") or os.path.join(os.path.expanduser("~"), ".cache")
    return Path(base) / "sdc-gdr2edifact"


# ---------------------------------------------------------------- reading the text files
def _text(raw: bytes) -> str:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.decode("latin-1", errors="replace")
    return text.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')


def _blocks(text: str):
    cur: list[str] = []
    for line in text.splitlines():
        if DASH.match(line):
            if cur:
                yield cur
            cur = []
        else:
            cur.append(line)
    if cur:
        yield cur


def _joined(lines: list[str]) -> str:
    return re.sub(r"\s+", " ", " ".join(x.strip() for x in lines)).strip()


def _field(lines: list[str], name: str) -> str:
    out, on = [], False
    for x in lines:
        m = re.match(rf"^\s*{name}:\s*(.*)$", x)
        if m:
            out.append(m.group(1))
            on = True
            continue
        if on:
            if x.strip() == "" or re.match(r"^\s*(Desc|Repr|Note|Function|Notes?):", x) or re.match(r"^\d{3}\s", x):
                on = False
            else:
                out.append(x)
    return _joined(out)


ELEMENT_HEAD = re.compile(r"^[+*#|X\-]?\s{1,6}(\d{4})\s{2}(.+?)\s{2,}\[([BIC])\]\s*$")
COMPOSITE_HEAD = re.compile(r"^[+*#|X\-]?\s{1,8}(C\d{3})\s+(.+?)\s*$")
# A name can run into the status column with a single space ("...FUNCTION CODE QUALIFIER M    1 an..3"), so the
# status is found as a lone M or C before the repeat count or representation, not after two spaces.
COMPONENT = re.compile(r"^(\d{3})\s+(\d{4})\s+(.+?)\s+([MC])\s+(\S+)\s*$")
SEGMENT_HEAD = re.compile(r"^[+*#|X\-]?\s{1,8}([A-Z]{3})\s{2}(.+?)\s*$")
SEG_ELEMENT = re.compile(r"^(\d{3})\s+(C\d{3}|\d{4})\s+(.+?)\s+([MC])\s+(\d+)(?:\s+(\S+))?\s*$")
SEG_SUB = re.compile(r"^\s{4,}(\d{4})\s+(.+?)\s+([MC])\s+(\S+)\s*$")
CODE_LINE = re.compile(r"^[+*#|X\-]?\s{1,6}(\S{1,3})\s{2,}(.+?)\s*$")
GROUP = re.compile(r"^(\d{5})\s+-+\s+Segment group\s+(\d+)\s+-+\s+([MC])\s+(\d+)\s*-*\+\|*\s*$")
SEGLINE = re.compile(r"^(\d{5})\s+([A-Z]{3})\s+(.+?)\s{2,}([MC])\s+(\d+)\s*(-*)(\++)?\s*\|*\s*$")


def _elements(text: str) -> dict:
    out = {}
    for b in _blocks(text):
        head = next((x for x in b if ELEMENT_HEAD.match(x)), None)
        if head:
            m = ELEMENT_HEAD.match(head)
            out[m.group(1)] = {"tag": m.group(1), "name": m.group(2).strip(), "repr": _field(b, "Repr")}
    return out


def _composites(text: str) -> dict:
    out = {}
    for b in _blocks(text):
        head = next((x for x in b if COMPOSITE_HEAD.match(x) and not x.strip().startswith("Desc")), None)
        if not head:
            continue
        m = COMPOSITE_HEAD.match(head)
        comps, pending = [], None
        for x in b:
            cm = COMPONENT.match(x)
            if cm:
                comps.append({"tag": cm.group(2), "name": cm.group(3).strip(), "status": cm.group(4), "repr": cm.group(5)})
                pending = None
            elif re.match(r"^(\d{3})\s+(\d{4})\s+(.+)$", x):
                pending = re.match(r"^(\d{3})\s+(\d{4})\s+(.+)$", x)
            elif pending and x.strip():
                tail = re.match(r"^\s*(.+?)\s{2,}([MC])\s+(\S+)\s*$", x)
                if tail:
                    comps.append({"tag": pending.group(2), "name": f"{pending.group(3).strip()} {tail.group(1).strip()}",
                                  "status": tail.group(2), "repr": tail.group(3)})
                    pending = None
        out[m.group(1)] = {"tag": m.group(1), "name": m.group(2).strip(), "components": comps}
    return out


def _segments(text: str) -> dict:
    out = {}
    for b in _blocks(text):
        head = next((x for x in b if SEGMENT_HEAD.match(x) and x.strip()[:3].isalpha() and x.strip()[:3].isupper()
                     and not x.strip().startswith(("Function", "Desc", "Note"))), None)
        if not head or "Function:" not in "\n".join(b):
            continue
        m = SEGMENT_HEAD.match(head)
        items, pending = [], None
        for x in b:
            em = SEG_ELEMENT.match(x)
            if em:
                items.append({"tag": em.group(2), "name": em.group(3).strip(), "status": em.group(4),
                              "repeat": int(em.group(5)), "repr": em.group(6) or "", "components": []})
                pending = None
                continue
            sm = SEG_SUB.match(x)
            if sm and items and items[-1]["tag"].startswith("C"):
                items[-1]["components"].append({"tag": sm.group(1), "name": sm.group(2).strip(), "status": sm.group(3),
                                                "repr": sm.group(4)})
                pending = None
                continue
            wm = re.match(r"^(\d{3})\s+(C\d{3}|\d{4})\s+(.+)$", x)
            if wm:
                pending = ("item", wm)
                continue
            wsm = re.match(r"^\s{4,}(\d{4})\s{2}(.+)$", x)
            if wsm and items and items[-1]["tag"].startswith("C"):
                pending = ("sub", wsm)
                continue
            if pending and x.strip():
                tail = re.match(r"^\s*(.+?)\s{2,}([MC])\s+(\d+)?\s*(\S+)?\s*$", x)
                if tail:
                    kind, pm = pending
                    if kind == "item":
                        items.append({"tag": pm.group(2), "name": f"{pm.group(3).strip()} {tail.group(1).strip()}",
                                      "status": tail.group(2), "repeat": int(tail.group(3) or 1), "repr": tail.group(4) or "",
                                      "components": []})
                    else:
                        items[-1]["components"].append({"tag": pm.group(1), "name": f"{pm.group(2).strip()} {tail.group(1).strip()}",
                                                        "status": tail.group(2), "repr": tail.group(4) or tail.group(3) or ""})
                pending = None
        out[m.group(1)] = {"tag": m.group(1), "name": m.group(2).strip(), "elements": items}
    return out


def _codelists(text: str) -> dict:
    out = {}
    for b in _blocks(text):
        head = next((x for x in b if ELEMENT_HEAD.match(x)), None)
        if not head:
            continue
        tag = ELEMENT_HEAD.match(head).group(1)
        codes, started = [], False
        for x in b:
            if x is head:
                started = True
                continue
            if not started or re.match(r"^\s*(Desc|Repr|Note):", x):
                continue
            cm = CODE_LINE.match(x)
            if cm and (len(x) - len(x.lstrip(" +*#|X-")) <= 6) and not x.startswith("              "):
                codes.append({"value": cm.group(1), "name": cm.group(2).strip()})
        out[tag] = {"tag": tag, "codes": codes}
    return out


def _message(text: str, name: str) -> dict:
    lines = text.splitlines()
    head = {}
    for key, pat in (("type", r"Message Type\s*:\s*(\S+)"), ("version", r"Version\s*:\s*(\S+)"),
                     ("release", r"Release\s*:\s*(\S+)"), ("agency", r"Contr\. Agency\s*:\s*(\S+)")):
        m = re.search(pat, text)
        head[key] = m.group(1) if m else ""
    n = max((i for i, x in enumerate(lines) if re.match(r"^\s*Pos\s+Tag\s+Name", x)), default=None)
    root = {"group": 0, "status": "M", "repeat": 1, "items": []}
    if n is not None:
        stack = [root]
        for x in lines[n + 1:]:
            gm = GROUP.match(x)
            if gm:
                g = {"group": int(gm.group(2)), "status": gm.group(3), "repeat": int(gm.group(4)), "items": []}
                stack[-1]["items"].append(g)
                stack.append(g)
                continue
            sm = SEGLINE.match(x)
            if sm:
                stack[-1]["items"].append({"tag": sm.group(2), "name": sm.group(3).strip(), "status": sm.group(4),
                                           "repeat": int(sm.group(5))})
                for _ in range(len(sm.group(7) or "")):
                    if len(stack) > 1:
                        stack.pop()
    return {"type": head["type"] or name.split("_")[0], "version": head["version"], "release": head["release"],
            "agency": head["agency"], "segment_table": root["items"]}


def extract(archive: bytes) -> dict:
    """A directory archive (the zip as downloaded from UNECE) to its definitions."""
    outer = zipfile.ZipFile(io.BytesIO(archive))
    parts = {}
    for name in outer.namelist():
        if name.lower().endswith(".zip"):
            parts[name.lower().split("/")[-1][:-4]] = zipfile.ZipFile(io.BytesIO(outer.read(name)))

    def one(part: str, prefix: str) -> tuple[str, str]:
        z = parts[part]
        name = next(n for n in z.namelist() if n.upper().split("/")[-1].startswith(prefix + ".")
                    and not n.upper().split("/")[-1].startswith(prefix + "I"))
        return name, _text(z.read(name))

    eded_name, eded = one("eded", "EDED")
    suffix = eded_name.split(".")[-1].upper()                      # 24A
    version = f"D.{suffix}"
    messages = {}
    for name in parts["edmd"].namelist():
        if name.endswith("/"):
            continue
        m = _message(_text(parts["edmd"].read(name)), name.split("/")[-1])
        messages[m["type"]] = m
    return {"version": version, "elements": _elements(eded), "composites": _composites(one("edcd", "EDCD")[1]),
            "segments": _segments(one("edsd", "EDSD")[1]), "codelists": _codelists(one("uncl", "UNCL")[1]),
            "messages": messages}


@dataclass
class Directory:
    version: str
    elements: dict
    composites: dict
    segments: dict
    codelists: dict
    messages: dict
    sha256: str = ""
    _cache: dict = field(default_factory=dict, repr=False)

    _loaded: ClassVar[dict] = {}

    @classmethod
    def load(cls, path: str | os.PathLike | None = None) -> "Directory":
        path = path or os.environ.get(ENV)
        if not path:
            raise DirectoryNotFound(
                f"the UN/EDIFACT directory is needed: download the D.24A archive from UNECE "
                f"(https://unece.org/trade/uncefact/unedifact/download) and set {ENV} to the zip's path")
        p = Path(path)
        if not p.exists():
            raise DirectoryNotFound(f"no UN/EDIFACT directory archive at {p}")
        raw = p.read_bytes()
        sha = hashlib.sha256(raw).hexdigest()
        if sha in cls._loaded:
            return cls._loaded[sha]
        cache = _cache_dir() / f"{sha}-{EXTRACTION}.json"
        if cache.exists():
            data = json.loads(cache.read_text(encoding="utf-8"))
        else:
            data = extract(raw)
            cache.parent.mkdir(parents=True, exist_ok=True)
            cache.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        obj = cls(data["version"], data["elements"], data["composites"], data["segments"], data["codelists"],
                  data["messages"], sha256=sha)
        cls._loaded[sha] = obj
        return obj

    def message(self, name: str) -> dict:
        if name not in self.messages:
            raise KeyError(f"{name} is not a message of {self.version}")
        return self.messages[name]

    def code(self, element: str, value: str) -> dict | None:
        cl = self.codelists.get(element)
        return next((c for c in cl["codes"] if c["value"] == value), None) if cl else None
