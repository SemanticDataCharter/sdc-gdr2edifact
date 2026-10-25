"""The UN/EDIFACT mapper: a Governed Data Record as a D.24A interchange, by a mapping file.

The business documents library links its components to UBL, not to UN/EDIFACT, so where a value goes in a message
(a segment, a qualifier, a data element) is declared in a mapping file, one per model. Where the model does bind a
value to a code list the directory uses, the mapping's `binding` transform takes the code from the model and the value
is a lookup: UBL 2.3's PaymentMeansCode list is UNCL 4461, code for code, and the packaging types are UN/ECE
Recommendation 21 codes.

UN/EDIFACT has no null flavors. A free text segment could hold the words, but no qualifier the directory defines says
"this value was asked for and refused" in a way a receiving system would act on, so an Exceptional Value is lost, and
where the directory requires the value, the segment, the group or the message cannot be written, and the report says
which and why.
"""
from __future__ import annotations

import os

from sdc_mapper import (DECLARED, LOOKUP, LOOKUP_TRANSFORMS, LOST, NOT_REPRESENTABLE, EVRule, IncompleteMapping,
                        MapResult, MappingError, ValueOutcome, join_depth, place)
from sdcreader.record import EXCEPTIONAL_VALUES

from . import __version__
from .check import check
from .directory import ENV, Directory
from .writer import Builder

CANNOT_HOLD = [
    "Exceptional Values: UN/EDIFACT has no null flavors",
    "validity windows and the time a value was recorded (act, vtb, vte, tr)",
    "the definitions the model binds each component to",
    "the record's provenance and audit clusters",
]


class EDIFACTMapper:
    name = "edifact"
    target = "UN/EDIFACT"
    target_version = "D.24A"
    package = "sdc-gdr2edifact"
    version = __version__
    ev_table = {code: EVRule(LOST) for code in EXCEPTIONAL_VALUES}

    def __init__(self, directory: str | os.PathLike | Directory | None = None):
        self._directory = directory

    @property
    def directory(self) -> Directory:
        if not isinstance(self._directory, Directory):
            self._directory = Directory.load(self._directory or os.environ.get(ENV))
        return self._directory

    def map(self, record, mapping) -> MapResult:
        if mapping is None:
            raise MappingError("UN/EDIFACT needs a mapping file: the model does not say where its values go in a message")
        if mapping.carry_rejected:
            raise MappingError("UN/EDIFACT has no agreed place to carry a rejected value; carry_rejected is not available")
        for code, override in mapping.exceptional_values.items():
            if override["class"] != LOST:
                raise MappingError(f"UN/EDIFACT cannot say {code}: it has no null flavors, so an Exceptional Value is lost")
        placements, clusters = place(record, mapping)
        message = next((p.steps[0][0] for p in placements if p.steps), None)
        if message is None:
            raise MappingError("nothing to write: no value of the record reached the message")
        b = Builder(self.directory, message, mapping.cluster_order)
        notes: dict[int, str] = {}
        later = []
        for p in placements:
            v = p.value
            if v.exceptional or p.omitted or p.rule is None or not p.steps:
                continue
            if p.text is None:
                notes[v.position] = p.note or "no value to write"
                continue
            writes = [(p.steps, p.attribute, p.text, v.position, p)]
            writes += [(e.steps, e.attribute, e.text, None, None) for e in p.extras if e.text is not None]
            for w in writes:
                if join_depth(w[0]) >= 0:
                    later.append(w)
                else:
                    self._write(b, *w)
        # a join waits for the elements it may join: sdc-mapper's join_depth, shallowest first
        later.sort(key=lambda w: join_depth(w[0]))
        for w in later:
            self._write(b, *w)
        # A cluster's constant data (a NAD's party qualifier, a CPS's packaging level) go on its segment; the segment is
        # written when the cluster's group holds anything of the record's, though no value lands in the segment itself.
        for c in clusters:
            if not c.attributes:
                continue
            node = b.find(c.steps, loose=True)
            parent = b.find(c.steps[:-1], loose=True) if len(c.steps) > 2 else None
            if node is None and parent is not None and parent.children:
                node = b.ensure_under(parent, c.steps[-1])
            if node is not None:
                for k, val in c.attributes.items():
                    node.attrs.setdefault(k, val)
        text = b.interchange()
        errors = check(text, self.directory)
        if errors:
            raise MappingError(f"the {message} does not conform to {self.directory.version}: {errors[0]}")
        outcomes, missing = [], []
        for p in placements:
            v = p.value
            if v.exceptional:
                outcomes.append(ValueOutcome(v.position, LOST, note="UN/EDIFACT has no null flavors"))
            elif p.omitted:
                outcomes.append(ValueOutcome(v.position, NOT_REPRESENTABLE, note=p.omitted_by.reason or ""))
            elif p.rule is None:
                missing.append(f"{' / '.join(v.path_labels + [v.label])} ({v.ct_id})")
            elif v.position in notes:
                outcomes.append(ValueOutcome(v.position, NOT_REPRESENTABLE, note=notes[v.position]))
            elif v.position in b.pruned:
                outcomes.append(ValueOutcome(v.position, NOT_REPRESENTABLE, note=b.pruned[v.position]))
            else:
                cls = LOOKUP if p.rule.transform in LOOKUP_TRANSFORMS else DECLARED
                where = "/".join(n for n, _ in p.steps) + (f"/@{p.attribute}" if p.attribute else "")
                outcomes.append(ValueOutcome(v.position, cls, location=where))
        if missing:
            raise IncompleteMapping(f"mapping {mapping.id} has no rule for {len(missing)} value(s): " + "; ".join(missing[:5]))
        return MapResult(files={f"{message}.edi": text.encode("latin-1")}, outcomes=outcomes,
                         cannot_hold=list(CANNOT_HOLD))

    @staticmethod
    def _write(b: Builder, steps, attribute, text, position, p):
        node = b.put(steps, attribute, text, position)
        if p is not None:
            for k, val in p.attributes.items():
                node.attrs.setdefault(k, val)
            if p.units_attribute and p.units_text is not None:
                node.attrs[p.units_attribute] = p.units_text
