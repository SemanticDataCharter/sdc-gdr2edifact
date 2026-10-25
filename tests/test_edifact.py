"""The directory, the writer's refusals, the independent checker, and what UN/EDIFACT cannot say."""
from __future__ import annotations

import io
from pathlib import Path

import pytest
import yaml
from lxml import etree

from sdc_mapper import ERROR, LOST, VALID, Engine, load_mapping
from sdc_gdr2edifact import Directory, DirectoryNotFound, EDIFACTMapper, mapping_path
from sdc_gdr2edifact.check import check

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "samples" / "halvorsen-order"
CT = "h8bttbt9afwzf9zs4jhae566"
RECORDS = sorted((SAMPLE / "records").glob("*.xml"))
SDC4 = "https://semanticdatacharter.com/ns/sdc4/"


@pytest.fixture(scope="module")
def engine(tmp_path_factory):
    return Engine(schema_dir=tmp_path_factory.mktemp("schemas"))


def run(engine, xml, mapping=None):
    return engine.map_record(xml, EDIFACTMapper(), mapping or load_mapping(mapping_path(CT)), directory=str(SAMPLE))


# ---------------------------------------------------------------- the directory
def test_the_directory_is_read_from_the_archive_unece_publishes():
    d = Directory.load()
    assert d.version == "D.24A"
    assert {"ORDERS", "ORDRSP", "DESADV", "RECADV", "INVOIC", "REMADV"} <= set(d.messages)
    assert d.messages["INVOIC"]["release"] == "24A"


def test_an_element_whose_name_runs_into_its_status_is_read():
    """TAX 010 reads "5283 DUTY OR TAX OR FEE FUNCTION CODE QUALIFIER M    1 an..3", one space before the status."""
    tax = Directory.load().segments["TAX"]
    assert tax["elements"][0]["tag"] == "5283" and tax["elements"][0]["status"] == "M"


@pytest.mark.no_directory
def test_no_directory_says_where_to_get_one(monkeypatch, tmp_path):
    monkeypatch.delenv("SDC_EDIFACT_DIRECTORY", raising=False)
    with pytest.raises(DirectoryNotFound, match="unece.org"):
        Directory.load(None)


# ---------------------------------------------------------------- the checker, independently of the writer
def interchange(engine) -> str:
    r = run(engine, RECORDS[0].read_bytes())
    assert r.outcome == VALID, r.errors
    return r.files["ORDERS.edi"].decode("latin-1")


def test_the_checker_finds_a_wrong_segment_count(engine):
    text = interchange(engine)
    unt = next(x for x in text.splitlines() if x.startswith("UNT+"))
    n = int(unt.split("+")[1])
    assert any("UNT counts" in e for e in check(text.replace(unt, unt.replace(f"UNT+{n}", f"UNT+{n + 1}")), Directory.load()))


def test_the_checker_finds_a_segment_out_of_place(engine):
    lines = interchange(engine).splitlines()
    bgm = next(i for i, x in enumerate(lines) if x.startswith("BGM"))
    lines.insert(len(lines) - 3, lines.pop(bgm))               # BGM after the summary
    assert check("\n".join(lines), Directory.load())


def test_the_checker_finds_a_value_too_long(engine):
    text = interchange(engine).replace("BGM+220+", "BGM+220+" + "X" * 80, 1)
    assert any("an..70" in e for e in check(text, Directory.load()))


# ---------------------------------------------------------------- the writer refuses rather than guess
def edited(tmp_path, change):
    doc = yaml.safe_load(mapping_path(CT).read_text())
    change(doc)
    p = tmp_path / "m.yaml"
    p.write_text(yaml.safe_dump(doc, sort_keys=False))
    return load_mapping(p)


def test_a_data_element_the_segment_does_not_have_is_an_error(engine, tmp_path):
    def change(doc):
        for r in doc["rules"]:
            if r.get("to") == "BGM/@C106.1004":
                r["to"] = "BGM/@C106.9999"
    r = run(engine, RECORDS[0].read_bytes(), edited(tmp_path, change))
    assert r.outcome == ERROR and "BGM has no C106.9999" in r.errors[0]["reason"]


def test_a_segment_the_group_does_not_have_is_an_error(engine, tmp_path):
    def change(doc):
        for r in doc["rules"]:
            if r.get("to") == "BGM/@C106.1004":
                r["to"] = "SG2/BGM/@C106.1004"
    r = run(engine, RECORDS[0].read_bytes(), edited(tmp_path, change))
    assert r.outcome == ERROR and "is not part of ORDERS/SG2" in r.errors[0]["reason"]


def test_a_component_with_no_rule_is_an_incomplete_mapping(engine, tmp_path):
    r = run(engine, RECORDS[0].read_bytes(),
            edited(tmp_path, lambda doc: doc.update(rules=[x for x in doc["rules"] if x.get("to") != "BGM/@C106.1004"])))
    assert r.outcome == ERROR and "Order ID" in r.errors[0]["reason"]


# ---------------------------------------------------------------- Exceptional Values: UN/EDIFACT has no null flavors
def with_ev(xml: bytes, label_path: list[str], code="ASKR", name="Asked and Refused") -> bytes:
    from sdcreader import load_package, read_model
    model = read_model(load_package(SAMPLE, CT))
    by_label: dict[str, set] = {}
    for c in model.components.values():
        by_label.setdefault(c.label, set()).add(c.ct_id)
    tree = etree.parse(io.BytesIO(xml))
    candidates = tree.getroot().iter()
    found = None
    for label in label_path:
        ids = by_label[label]
        found = next(el for el in candidates if isinstance(el.tag, str) and el.tag.startswith(f"{{{SDC4}}}ms-")
                     and el.tag.split("ms-", 1)[1] in ids)
        candidates = found.iter()
    after = found.find(f"{{{SDC4}}}act")
    if after is None:
        after = found.find("label")
    ev = etree.Element(f"{{{SDC4}}}{code}")
    etree.SubElement(ev, "ev-name").text = name
    after.addnext(ev)
    return etree.tostring(tree)


def test_an_exceptional_value_is_lost_and_the_interchange_still_written(engine):
    r = run(engine, with_ev(RECORDS[0].read_bytes(), ["Order Document", "Customer Reference"]))
    assert r.outcome == VALID, r.errors
    assert [(e["label"], e["class"]) for e in r.report.exceptional] == [("Customer Reference", LOST)]
    assert "RFF+CR" not in r.files["ORDERS.edi"].decode("latin-1")


def test_an_exceptional_value_the_envelope_requires_refuses_the_interchange(engine):
    """The buyer's identification is the interchange's sender (UNB S002): without it there is no interchange."""
    xml = with_ev(RECORDS[0].read_bytes(), ["Buyer Customer Party", "Party Identification Value"])
    r = run(engine, xml)
    assert r.outcome == ERROR and "UNB requires S002.0004" in r.errors[0]["reason"]


def test_a_mapping_that_promises_edifact_can_say_an_exceptional_value_is_refused(engine, tmp_path):
    m = edited(tmp_path, lambda doc: doc.update(exceptional_values={"ASKR": {"class": "carried"}}))
    r = run(engine, RECORDS[0].read_bytes(), m)
    assert r.outcome == ERROR and "no null flavors" in r.errors[0]["reason"]
