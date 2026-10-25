"""Every published mapping: a conformant D.24A interchange for every sample record, checked by the package's own
checker and parsed by an independent one (pydifact); the DESADV equivalent to the UN-EDIFACT library's writer."""
from __future__ import annotations

import warnings
from collections import Counter
from pathlib import Path

import pytest

from sdc_mapper import DECLARED, LOOKUP, NOT_REPRESENTABLE, VALID, Engine, load_mapping
from sdc_gdr2edifact import Directory, EDIFACTMapper, mapping_path
from sdc_gdr2edifact.check import check, parse

ROOT = Path(__file__).resolve().parents[1]
SDC4 = "https://semanticdatacharter.com/ns/sdc4/"
#: (sample directory, model, message)
MODELS = [
    ("halvorsen-order", "h8bttbt9afwzf9zs4jhae566", "ORDERS"),
    ("halvorsen-torvale-order", "cq1fjrvyn0fxl1kyk9y3kr1w", "ORDERS"),
    ("halvorsen-order-response", "kuntv2wlkw54h7nxe0kqhvi2", "ORDRSP"),
    ("halvorsen-despatch-advice", "cacl4njrwanj15g3p3so8t6h", "DESADV"),
    ("halvorsen-receipt-advice", "tog0v0p1zit1xwpxysxwpf3d", "RECADV"),
    ("halvorsen-invoice", "u19w614300a8ot4a7qnn2o1c", "INVOIC"),
    ("halvorsen-credit-note", "jkuyr38hydqaiwlq5vhp2rjr", "INVOIC"),
    ("halvorsen-remittance-advice", "fgtbf38cj0bwxppxn69etcci", "REMADV"),
]


@pytest.fixture(scope="module")
def engine(tmp_path_factory):
    return Engine(schema_dir=tmp_path_factory.mktemp("schemas"))


@pytest.fixture(scope="module")
def mapper():
    return EDIFACTMapper()


def run(engine, mapper, sample, ct, xml: bytes):
    return engine.map_record(xml, mapper, load_mapping(mapping_path(ct)), directory=str(ROOT / "samples" / sample))


def records(sample):
    return sorted((ROOT / "samples" / sample / "records").glob("*.xml"))


@pytest.mark.parametrize("sample,ct,message", MODELS, ids=lambda x: x if isinstance(x, str) and "-" in x else None)
def test_every_record_is_a_conformant_interchange(engine, mapper, sample, ct, message):
    from pydifact.segmentcollection import Interchange
    d = Directory.load()
    for f in records(sample):
        r = run(engine, mapper, sample, ct, f.read_bytes())
        assert r.outcome == VALID, (f.name, r.errors)
        text = r.files[f"{message}.edi"].decode("latin-1")
        assert check(text, d) == [], f.name
        with warnings.catch_warnings():               # pydifact warns that it has no D.24A segment definitions
            warnings.simplefilter("ignore")
            ic = Interchange.from_str(text)
            msgs = list(ic.get_messages())
        assert [m.type for m in msgs] == [message], f.name
        segs = parse(text)
        assert segs[0][0] == "UNB" and segs[-1][0] == "UNZ"


@pytest.mark.parametrize("sample,ct,message", MODELS, ids=lambda x: x if isinstance(x, str) and "-" in x else None)
def test_the_report_accounts_for_every_value(engine, mapper, sample, ct, message):
    r = run(engine, mapper, sample, ct, records(sample)[0].read_bytes())
    assert {v["class"] for v in r.report.values} <= {DECLARED, LOOKUP, NOT_REPRESENTABLE}
    assert all(v.get("note") for v in r.report.values if v["class"] == NOT_REPRESENTABLE), "every loss says why"
    payment = [v for v in r.report.values if v["label"] == "Payment Means"]
    assert all(v["class"] == LOOKUP for v in payment), "UBL's PaymentMeansCode is UNCL 4461: a lookup"


GOLDEN = sorted((ROOT / "tests" / "golden" / "despatch-advice").glob("*.edi"))


@pytest.mark.parametrize("golden", GOLDEN, ids=lambda p: p.stem)
def test_desadv_equivalent_to_the_library_writer(engine, mapper, golden):
    """The same segments, with the same data, as the UN-EDIFACT library's hand-written DESADV writer; the order of
    repeats within a group (references, dates, measurements) is the record's here."""
    sample, ct = "halvorsen-despatch-advice", "cacl4njrwanj15g3p3so8t6h"
    r = run(engine, mapper, sample, ct, (ROOT / "samples" / sample / "records" / f"{golden.stem}.xml").read_bytes())
    ours = Counter((t, str(e)) for t, e in parse(r.files["DESADV.edi"].decode("latin-1")))
    theirs = Counter((t, str(e)) for t, e in parse(golden.read_text(encoding="latin-1")))
    assert ours == theirs


def test_long_text_continues_in_the_next_component(engine, mapper):
    """Shipping marks over 35 characters continue in PCI's next 7102, as the directory allows, instead of being cut."""
    sample, ct = "halvorsen-despatch-advice", "cacl4njrwanj15g3p3so8t6h"
    r = run(engine, mapper, sample, ct, records(sample)[0].read_bytes())
    pci = [e for t, e in parse(r.files["DESADV.edi"].decode("latin-1")) if t == "PCI"]
    assert pci and all(len(c) <= 35 for e in pci for comps in e for c in comps)
    assert any(len(e[1]) > 1 for e in pci if len(e) > 1)
