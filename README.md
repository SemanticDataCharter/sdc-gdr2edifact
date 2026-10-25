# sdc-gdr2edifact

Governed Data Records as UN/EDIFACT D.24A interchanges. A target mapper for
[sdc-mapper](https://github.com/SemanticDataCharter/sdc-mapper): the core validates the record, resolves every value
against its model and reports each one; this package says where each value goes in a message and writes the
interchange, UNA to UNZ. Outbound only. Apache 2.0.

**Status:** 4.0.2. Every document of the business documents library has a mapping:

| Model | ct_id | Message | Rules |
|---|---|---|---|
| Order | `h8bttbt9afwzf9zs4jhae566` | ORDERS | 213 |
| Torvale Order (profile) | `cq1fjrvyn0fxl1kyk9y3kr1w` | ORDERS | 216 |
| Order Response | `kuntv2wlkw54h7nxe0kqhvi2` | ORDRSP | 291 |
| Despatch Advice | `cacl4njrwanj15g3p3so8t6h` | DESADV | 181 |
| Receipt Advice | `tog0v0p1zit1xwpxysxwpf3d` | RECADV | 175 |
| Invoice | `u19w614300a8ot4a7qnn2o1c` | INVOIC (380) | 249 |
| Credit Note | `jkuyr38hydqaiwlq5vhp2rjr` | INVOIC (381) | 256 |
| Remittance Advice | `fgtbf38cj0bwxppxn69etcci` | REMADV | 115 |

## Use

The directory is not part of this package (see the terms below). Download the D.24A archive from UNECE
(https://unece.org/trade/uncefact/unedifact/download) and point the mapper at the zip, unchanged:

```
export SDC_EDIFACT_DIRECTORY=/path/to/d24a.zip
sdc-map map edifact despatch-advice.xml --package DIR --mapping "$(python -c 'from sdc_gdr2edifact import mapping_path; print(mapping_path("cacl4njrwanj15g3p3so8t6h"))')"
```

```python
from sdc_mapper import Engine, load_mapping
from sdc_gdr2edifact import EDIFACTMapper, mapping_path

mapper = EDIFACTMapper("/path/to/d24a.zip")          # or $SDC_EDIFACT_DIRECTORY
result = Engine().map_record(xml, mapper, load_mapping(mapping_path("cacl4njrwanj15g3p3so8t6h")))
result.files["DESADV.edi"]                           # UNA ... UNB ... UNH ... UNT ... UNZ, ISO 8859-1 (UNOC)
result.report                                        # every value: declared, lookup or not representable, and why
```

Through sdc-mapper's MCP server the mapper is the target `edifact`.

## The target and its terms

**UN/EDIFACT**, the United Nations rules for electronic data interchange: the syntax is ISO 9735, and UNECE publishes
the directory (UNTDID: data elements, composites, segments, code lists, message specifications) twice a year. This
package writes **D.24A**, read from the archive UNECE published on 9 October 2024.

The directory comes with UNECE's license agreement (`LICENAGR.TXT` in the archive). It grants use of the directory
within the organization, in the country where it was acquired or where the organization is located; copies for use and
backup within the organization; and distribution of copies of the original file as downloaded, with the license. It
does not allow selling, sub-licensing, renting, leasing or assigning the directory, or modifying it and distributing
the result, without the UN's written permission. So:

- **This package carries no part of the directory.** It reads the archive the user downloaded, as downloaded, and
  keeps its extraction as a working copy in the user's cache (`~/.cache/sdc-gdr2edifact/`), on the user's machine.
- **This repository** does not carry the directory either: the tests read the archive from `SDC_EDIFACT_DIRECTORY`.
- **GS1's EANCOM** (UN/EDIFACT's retail subset) is not a target until its terms are confirmed.

Every interchange this package writes conforms to the D.24A message specification, or is not written.

## Where values go: declared, one mapping file per model

The business documents library links its components to UBL, not to UN/EDIFACT, so where a value goes in a message (the
segment, its qualifier, the data element) is stated in a mapping file, `src/sdc_gdr2edifact/mappings/<document>-<ct_id>.yaml`,
bound to the model's schema by its SHA-256. The qualifiers are the UN-EDIFACT library's mappings (`mapping/*.json`,
reviewed by hand on 4 October 2026, from which the library's D.24A qualifier tokens were published).

Where the model binds a value to a code list the directory uses, the value is a **lookup**: the business documents bind
the payment means to UBL 2.3's PaymentMeansCode list, which is UNCL 4461 code for code (checked against D.24A), so
PAI's 4461 is the model's own code. The handling unit and packaging types are bound to the UN/ECE Recommendations'
page without a code, so their Recommendation 21 codes are declared, as the Recommendation 20 unit codes are. The
allowance and charge reason is bound to UBL's AllowanceChargeReasonCode, which is UNCL 4465 (adjustment reasons); ALC
identifies an allowance with a different list (5189), so the reason travels as ALC's text (C214 7160) and its code
does not.

The mapping files are written with `tools/build_mapping.py` from a spec in the model's labels (`tools/specs/`: one per
message, composed with the rules every library document shares in `common.py`), which checks that every value the
model can hold reaches a rule: placed, or omitted with a reason.

**DESADV and the library's writer.** For all 52 Despatch Advice records, this mapping and the UN-EDIFACT library's
hand-written DESADV writer (`edifact/desadv.py`) produce the same segments with the same data, and the library's reader
reads the same values from both; the order of repeated segments within a group (references, dates, measurements) is
the record's here. Five are kept in `tests/golden/`. The other five messages had paper mappings only; their
placements are this package's first writers.

## What UN/EDIFACT cannot say

- **Exceptional Values.** UN/EDIFACT has no null flavors. A free text segment could hold the words, but no qualifier
  the directory defines says "this value was asked for and refused" in a way a receiving system would act on, so an
  Exceptional Value is **lost**, every ISO 21090 code alike, and the report says so. A mapping file cannot promise
  otherwise. Where the directory requires the value, the segment or group cannot be written and its other values are
  reported with the reason; where the interchange requires it (the sender's or the recipient's identification in
  UNB), there is no interchange, and the call ends as an error that says which element.
- **The record's provenance and audit**, the validity windows and recording times (act, vtb, vte, tr), and the
  definitions each component is bound to.
- Across the 293 sample records, 80.9% of the business values are placed (44,308 declared, 189 lookups) and 10,478 are
  not representable, each with its reason. The largest: the UBL-facing identifiers (customization, profile, UUID),
  which UNH and BGM already settle; a document reference's type and description (a reference group carries a number
  and a date); an address's use, a party's endpoint and a contact's department; a tax scheme's own identifier and a
  tax category's name (TAX codes them); flags with no element (partial delivery, back order, free of charge); a
  receipt check's result (CDI states a condition by a code a partner agrees); a pallet build pattern.

## How the writer works

A message is written as a tree first: its root is the message type, `SG<n>` a segment group, a tag a segment, and
`~x` after either tells apart segments of the same tag (`DTM~137`, `SG1~ON`). A segment's data are attributes named by
the directory: `@3035`, `@C082.3039`, `@C080.3036#2` for a component's second occurrence, `@C212#2.7140` for a
composite's second occurrence in its segment; a trailing `+` appends (a time after a date). From the directory the
writer orders every group as the message specification does; adds a group's trigger segment when it has no mandatory
data (an empty PCI) and numbers CPS hierarchies; removes a segment that lacks mandatory data, and a group that lacks its
trigger, with the reason; continues a value too long for its component into the components of the same tag that
follow (a long name across C080's 3036s, shipping marks across PCI's 7102s); infers a DTM's format (102, 203, 204); and
writes UNA, UNB, UNH, UNS where the message has one, UNT with the segment count, and UNZ. The interchange and message
control references are the document's number (its last 14 word characters).

**The check is independent.** `sdc_gdr2edifact.check` parses the interchange from its text, by code that shares
nothing with the writer, and checks the envelope (counts, references), the segment sequence against the message
specification's segment table, and every segment against its definition; the tests also parse every interchange with
[pydifact](https://github.com/nerdocs/pydifact) (MIT), which has no D.24A definitions but reads the syntax.

## Tests

```
pip install -e ".[dev]"
SDC_EDIFACT_DIRECTORY=/path/to/d24a.zip python -m pytest
```

Without `SDC_EDIFACT_DIRECTORY`, every test that needs the directory is skipped and says so.

Every sample record of the eight models is mapped, checked and parsed; the DESADV is compared with the library's
writer; Exceptional Values, refused mappings and a tampered interchange are exercised.
