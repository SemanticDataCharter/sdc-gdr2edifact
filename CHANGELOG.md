# Changelog

## 4.0.1 (2026-10-25)

Rebuilt with the release job's pip pinned by hash: CI and the release workflow install pip 26.2.2 from a hash-pinned
wheel before anything else is fetched (the eMudhra/emSign CA compromise: pip before 26.2.2 trusts the compromised root
through its vendored certifi). No change to the package.

## 4.0.0 (2026-10-25)

The second target mapper of the sdc-mapper line: Governed Data Records as UN/EDIFACT D.24A interchanges.

- **The directory, read from the archive UNECE publishes** (`Directory.load`, `$SDC_EDIFACT_DIRECTORY`): extracted in
  memory and cached on the user's machine; no part of it ships with the package, as its license requires. The
  extraction reads a data element whose name runs into its status column (TAX's 5283), which an earlier reading
  missed.
- **The writer**, driven by the directory: segment groups ordered as the message specification does, triggers added
  when they need no data, CPS hierarchies numbered, segments and groups that lack mandatory data left out with the
  reason, long values continued into the components that follow, DTM formats inferred, the envelope written with its
  counts.
- **The checker** (`sdc_gdr2edifact.check`), independent of the writer: envelope, segment table, segment definitions.
- **Mappings for all eight business documents models**: ORDERS (Order, Torvale Order), ORDRSP, DESADV, RECADV,
  INVOIC (Invoice, Credit Note), REMADV. All 293 sample records map to conformant interchanges; the DESADV is
  equivalent to the UN-EDIFACT library's writer for all 52 records.
- **Exceptional Values are lost**: UN/EDIFACT has no null flavors. Where the interchange requires the value, there is
  no interchange, and the error says which element.
