"""The business documents library's Despatch Advice model as a UN/EDIFACT D.24A DESADV.

The placements follow the UN-EDIFACT library's DESADV writer (edifact/desadv.py) and its reviewed mapping
(mapping/desadv.json): the shipment is the first consignment packing sequence (CPS 1, packaging level 5) and holds the
document's note and the lines; each transport handling unit is a CPS of its own under it (level 3) with a PAC for the
unit and one for the packages on it; the pallet's identifiers and the SSCC are the unit's GIN.
"""
from common import (DOCUMENT_STATUS, LINE_STATUS, REC20, REC21, UBL_IDENTIFIERS, C, OMIT, OMIT_C, V, const,
                    count, date, issue_date_time, item, location_party, measure, parties, qty, record, ref, ref_date,
                    text)

TITLE = "Despatch Advice (business documents library) to UN/EDIFACT D.24A DESADV"
ID = "despatch-advice-edifact-d24a"
VERSION = 1
AUTHOR = "Axius SDC, Inc."
DATE = "2026-10-25"
DESCRIPTION = ("The Despatch Advice model's values in a D.24A DESADV. Declared: the library links its components to "
               "UBL, not to UN/EDIFACT.")
MESSAGE = "DESADV"
M = f"/{MESSAGE}/"
PALLET_GIN = {"Global Returnable Asset Identifier (GS1)": "DB", "Pool operator number": "ZZZ",
              "Shipper's number": "ZZZ", "Mutually agreed": "ZZZ"}
PALLET_SCHEME_NAME = {"Global Returnable Asset Identifier (GS1)": "", "Pool operator number": "Pool operator number",
                      "Shipper's number": "Shipper's number", "Mutually agreed": "Mutually agreed"}
THU = "Transport Handling Unit"

RULES = [
    *record("Despatch Advice Governed Record", "Despatch Advice", MESSAGE),
    C("Despatch Advice Document", "."),
    *UBL_IDENTIFIERS,
    *issue_date_time(MESSAGE),
    V("Despatch Advice ID", "BGM/@C106.1004"),
    V("Despatch Advice Type", "BGM/@C002.1001", "code", table={"Delivery": "351", "Return": "729", "Consignment": "748"}),
    V("Document Status", "BGM/@1225", "code", table=DOCUMENT_STATUS),
    # DESADV has no header free text: the document's note is the shipment's (CPS 1)
    text("Note", "AAI", at="=SG11~ship/"),
    count("Line Count", "2"),

    C("Order Reference", "."),
    ref("Order ID", "ON", "SG1"),
    ref_date("Issue Date", "ON", "SG1", within=["Order Reference"]),
    ref("Sales Order ID", "VN", "SG1"),
    OMIT("Order Type", "DESADV refers to the order by its number (RFF ON); the order's type is the order's"),
    C("Additional Document Reference", "."),
    C("Document Reference", "."),
    ref("Document Reference ID", "ACD", "SG1", within=["Additional Document Reference"]),
    ref_date("Document Reference Issue Date", "ACD", "SG1", within=["Additional Document Reference"]),
    OMIT("Document Type", "a reference group carries a reference number and its date, not the document's type"),
    OMIT("Document Description", "a reference group carries a reference number and its date, not a description"),

    *parties({"Despatch Supplier Party": "SU", "Delivery Customer Party": "DP", "Buyer Customer Party": "BY",
              "Seller Supplier Party": "SE", "Originator Customer Party": "OB"},
             "SG2", "SG3", "SG4", MESSAGE, sender="Despatch Supplier Party", recipient="Buyer Customer Party"),
    C("Carrier Party", f"{M}SG2~CA/NAD", attributes={"3035": "CA"}),

    # the shipment: CPS 1, packaging level 5, ranked first among the CPS groups
    C("Shipment", f"{M}SG11~ship/CPS", attributes={"7164": "#seq", "7075": "5"}, order=0),
    ref("Shipment ID", "SRN", "SG1", at=M),
    text("Handling Instructions", "HAN", at="../"),
    measure("Gross Weight", "AAE", "AAD", at=M),
    measure("Net Weight", "AAE", "AAC", at=M),
    measure("Gross Volume", "AAE", "AAW", at=M),
    measure("Net Volume", "AAE", "AAX", at=M),
    count("Total Goods Item Quantity", "51", at=M),
    count("Total Transport Handling Unit Quantity", "11", at=M),
    C("Consignment", "."),
    ref("Consignment ID", "CU", "SG1", at=M),
    ref("Carrier Assigned ID", "BN", "SG1", at=M),
    C("Delivery", "."),
    ref("Delivery ID", "AAJ", "SG1", at=M),
    date("Latest Delivery Date", "17", at=M),
    C("Requested Delivery Period", "."),
    C("Date Range", "."),
    date("Date Range Start", "64", at=M, within=["Requested Delivery Period"]),
    date("Date Range End", "63", at=M, within=["Requested Delivery Period"]),
    OMIT("Delivery Quantity", "DESADV's header has no quantity; what is delivered is each line's despatch quantity"),
    *location_party("Delivery Location", "ST", "SG2", MESSAGE),
    OMIT_C("Delivery Party", "the party delivered to is the delivery customer (NAD DP)"),

    # each transport handling unit: a CPS under the shipment's (level 3), a PAC for the unit, a PAC for its packages
    C("Transport Handling Units", "."),
    *[C(f"Transport Handling Unit {n}", ".", order=n) for n in range(1, 7)],
    C(THU, f"{M}SG11/CPS", attributes={"7164": "#seq", "7166": "1", "7075": "3"}),
    V("Transport Handling Unit Type", "../SG12/PAC/@C202.7065", "code", table=REC21,
      also=[const("../SG12/PAC/@7224", "1"), const("../SG12/PAC/@C531.7075", "3")]),
    V("Minimum Temperature", "../SG12/MEA~AAU/@C174.6162",
      units={"to": "@C174.6411", "transform": "code", "table": REC20},
      also=[const("../SG12/MEA~AAU/@6311", "AAE"), const("../SG12/MEA~AAU/@C502.6313", "AAU")]),
    V("Maximum Temperature", "../SG12/MEA~AAU/@C174.6152",
      units={"to": "@C174.6411", "transform": "code", "table": REC20},
      also=[const("../SG12/MEA~AAU/@6311", "AAE"), const("../SG12/MEA~AAU/@C502.6313", "AAU")]),
    qty("Total Package Quantity", "189", at="../SG12/", units=False),
    V("Handling Instructions", "../SG12/SG13/HAN/@C524.4078", within=["Shipment", THU]),
    V("Shipping Marks", "../SG12/SG14/PCI/@C210.7102"),
    V("Transport Handling Unit ID", "../SG12/SG14/SG16~AW/GIN/@C208.7402",
      also=[const("../SG12/SG14/SG16~AW/GIN/@7405", "AW")]),
    C("Pallet Identification", "."),
    V("Pallet ID", "../=SG12/=SG14/SG16~P/GIN/@C208.7402"),
    V("Pallet ID Scheme", "../=SG12/=SG14/SG16~P/GIN/@7405", "code", table=PALLET_GIN,
      also=[{"to": "../=SG12/=SG14/SG16~P/GIN/@C208#2.7402", "transform": "code", "table": PALLET_SCHEME_NAME}]),
    date("Date Range Start", "157", at="../=SG12/=SG14/", within=["Pallet Identification"]),
    date("Date Range End", "799", at="../=SG12/=SG14/", within=["Pallet Identification"]),
    C("Package", "../SG12~pkg/PAC", attributes={"C531.7075": "1"}, order=1),   # after the unit's own PAC
    V("Package Quantity", "@7224"),
    V("Packaging Type", "@C202.7065", "code", table=REC21),
    OMIT("Package ID", "PAC has no element for a package's identifier"),
    C("Pack Specification", "."),
    measure("Pallet Height", "PD", "HT", at="../../=SG12/"),
    measure("Weight", "PD", "AAB", at="../../=SG12/", within=["Pack Specification"]),
    V("Pack Specification Version", "../../=SG12/=SG14/RFF~ZZZ/@C506.1154",
      also=[const("../../=SG12/=SG14/RFF~ZZZ/@C506.1153", "ZZZ")]),
    OMIT("Cases per Layer", "a pallet's build pattern; DESADV's packaging levels describe what is shipped"),
    OMIT("Layers per Pallet", "a pallet's build pattern; DESADV's packaging levels describe what is shipped"),

    # the lines, in the shipment's CPS
    C("Despatch Lines", "."),
    *[C(f"Despatch Line {n}", ".", order=n) for n in range(1, 11)],
    C("Despatch Line", f"{M}=SG11~ship/SG19"),
    V("Line ID", "LIN/@1082"),
    V("Line Status", "LIN/@1229", "code", table=LINE_STATUS),
    *item(),
    OMIT_C("Tax Category", "DESADV's line has no tax segment", within=["Item"]),
    qty("Delivered Quantity", "12"),
    qty("Backorder Quantity", "83"),
    qty("Outstanding Quantity", "73"),
    text("Note", "AAI", within=["Despatch Line"]),
    V("Backorder Reason", "FTX~BACKORDER/@C108.4440", also=[
        const("FTX~BACKORDER/@4451", "ACD"), const("FTX~BACKORDER/@C107.4441", "BACKORDER"),
        const("FTX~BACKORDER/@C107.3055", "ZZZ")]),
    V("Outstanding Reason", "FTX~OUTSTANDING/@C108.4440", also=[
        const("FTX~OUTSTANDING/@4451", "ACD"), const("FTX~OUTSTANDING/@C107.4441", "OUTSTANDING"),
        const("FTX~OUTSTANDING/@C107.3055", "ZZZ")]),
    C("Order Line Reference", "."),
    V("Line ID", "SG20~ON/RFF/@C506.1156", within=["Order Line Reference"],
      also=[const("SG20~ON/RFF/@C506.1153", "ON")]),
    ref("Sales Order Line ID", "VN", "SG20"),
    OMIT("Line Status", "the order line's status is the order's; DESADV refers to the line by its number",
         within=["Order Line Reference"]),
    C("Line Document Reference", "."),
    ref("Document Reference ID", "ACD", "SG20", within=["Line Document Reference"]),
    ref_date("Document Reference Issue Date", "ACD", "SG20", within=["Line Document Reference"]),
]
