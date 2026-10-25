"""The business documents library's Receipt Advice model as a UN/EDIFACT D.24A RECADV.

The qualifiers are the UN-EDIFACT library's paper mapping (mapping/recadv.json): the goods receipt (BGM 632), the
actual delivery as DTM 35, the parties in SG4 (mandatory in RECADV), the lines in a shipment-level CPS with the
received, short and rejected quantities and their variances (QVR), each received handling unit a CPS of its own with
its SSCC and pallet identifier.
"""
from common import (DOCUMENT_STATUS, UBL_IDENTIFIERS, C, OMIT, OMIT_C, V, const, count, date,
                    issue_date_time, item, location_party, parties, qty, record, ref, ref_date, text)

TITLE = "Receipt Advice (business documents library) to UN/EDIFACT D.24A RECADV"
ID = "receipt-advice-edifact-d24a"
VERSION = 1
AUTHOR = "Axius SDC, Inc."
DATE = "2026-10-25"
DESCRIPTION = ("The Receipt Advice model's values in a D.24A RECADV. Declared: the library links its components to UBL, "
               "not to UN/EDIFACT.")
MESSAGE = "RECADV"
M = f"/{MESSAGE}/"
RHU = "Received Handling Unit"
PALLET_GIN = {"Global Returnable Asset Identifier (GS1)": "DB", "Pool operator number": "ZZZ",
              "Shipper's number": "ZZZ", "Mutually agreed": "ZZZ"}
PALLET_SCHEME_NAME = {"Global Returnable Asset Identifier (GS1)": "", "Pool operator number": "Pool operator number",
                      "Shipper's number": "Shipper's number", "Mutually agreed": "Mutually agreed"}
NO_UNIT_DATE = "RECADV's package and handling unit groups have no date or free text"
NO_CHECK_CODE = "CDI states a condition by a code a partner agrees; the library names none for this check"


def variance(label, at, codes4221=None, codes4295=None):
    """A variance as a QVR of its own: the reason's name as text, and the directory's code where it has one."""
    seg = f"{at}QVR~{label.replace(' ', '')}"
    also = []
    if codes4221:
        also.append({"to": f"{seg}/@4221", "transform": "code", "table": codes4221, "on_miss": "omit"})
    if codes4295:
        also.append({"to": f"{seg}/@C960.4295", "transform": "code", "table": codes4295, "on_miss": "omit"})
    return V(label, f"{seg}/@C960.4294", also=also)


def action(label, subject, at=""):
    seg = f"{at}FTX~{subject}"
    return V(label, f"{seg}/@C108.4440", also=[const(f"{seg}/@4451", "ACD"), const(f"{seg}/@C107.4441", subject),
                                               const(f"{seg}/@C107.3055", "ZZZ")])


RULES = [
    *record("Receipt Advice Governed Record", "Receipt Advice", MESSAGE),
    C("Receipt Advice Document", "."),
    *UBL_IDENTIFIERS,
    *issue_date_time(MESSAGE),
    V("Receipt Advice ID", "BGM/@C106.1004"),
    V("Receipt Advice Type", "BGM/@C002.1001", "code", table={"Delivery": "632", "Return": "632"}),
    V("Document Status", "BGM/@1225", "code", table=DOCUMENT_STATUS),
    text("Note", "AAI"),
    count("Line Count", "2", at=M),

    C("Order Reference", "."),
    ref("Order ID", "ON", "SG1"),
    ref_date("Issue Date", "ON", "SG1", within=["Order Reference"]),
    ref("Sales Order ID", "VN", "SG1"),
    OMIT("Order Type", "RECADV refers to the order by its number (RFF ON); the order's type is the order's"),
    C("Despatch Document Reference", "."),
    C("Document Reference", "."),
    ref("Document Reference ID", "AAK", "SG1", within=["Despatch Document Reference"]),
    ref_date("Document Reference Issue Date", "AAK", "SG1", within=["Despatch Document Reference"]),
    OMIT("Document Type", "a reference group carries a reference number and its date, not the document's type"),
    OMIT("Document Description", "a reference group carries a reference number and its date, not a description"),

    *parties({"Delivery Customer Party": "DP", "Despatch Supplier Party": "SU", "Buyer Customer Party": "BY",
              "Seller Supplier Party": "SE"},
             "SG4", "SG5", "SG6", MESSAGE, sender="Delivery Customer Party", recipient="Despatch Supplier Party"),
    C("Carrier Party", f"{M}SG4~CA/NAD", attributes={"3035": "CA"}),

    # the shipment received: its references and dates in the header, its lines in the shipment-level CPS
    C("Receipt Shipment", f"{M}SG16~ship/CPS", attributes={"7164": "#seq", "7075": "5"}, order=0),
    ref("Shipment ID", "SRN", "SG1", at=M),
    V("Actual Delivery Date", f"{M}DTM~35/@C507.2380", "format", format="%Y%m%d",
      also=[const(f"{M}DTM~35/@C507.2005", "35")]),
    V("Actual Delivery Time", f"{M}DTM~35/@C507.2380+", "format", format="%H%M%S"),
    C("Consignment", "."),
    ref("Consignment ID", "CU", "SG1", at=M),
    ref("Carrier Assigned ID", "BN", "SG1", at=M),
    C("Delivery", "."),
    ref("Delivery ID", "AAJ", "SG1", at=M),
    date("Latest Delivery Date", "17", at=M),
    C("Requested Delivery Period", "."),
    date("Date Range Start", "64", at=M, within=["Requested Delivery Period"]),
    date("Date Range End", "63", at=M, within=["Requested Delivery Period"]),
    OMIT("Delivery Quantity", "RECADV's header has no quantity; what is received is each line's received quantity"),
    *location_party("Delivery Location", "ST", "SG4", MESSAGE),
    OMIT_C("Delivery Party", "the party delivered to is the delivery customer (NAD DP)"),

    # each received handling unit: a CPS under the shipment's, its package group with the SSCC and the pallet
    C("Received Handling Units", "."),
    *[C(f"Received Handling Unit {n}", ".", order=n) for n in range(1, 7)],
    C(RHU, f"{M}SG16/CPS", attributes={"7164": "#seq", "7166": "1"}),
    V("Transport Handling Unit ID", "../SG20/SG21/SG23~AW/GIN/@C208.7402",
      also=[const("../SG20/SG21/SG23~AW/GIN/@7405", "AW")]),
    C("Pallet Identification", "."),
    V("Pallet ID", "../=SG20/=SG21/SG23~P/GIN/@C208.7402"),
    V("Pallet ID Scheme", "../=SG20/=SG21/SG23~P/GIN/@7405", "code", table=PALLET_GIN,
      also=[{"to": "../=SG20/=SG21/SG23~P/GIN/@C208#2.7402", "transform": "code", "table": PALLET_SCHEME_NAME}]),
    C("Date Range", ".", within=["Pallet Identification"]),
    OMIT("Date Range Start", NO_UNIT_DATE, within=["Pallet Identification"]),
    OMIT("Date Range End", NO_UNIT_DATE, within=["Pallet Identification"]),
    V("Pack Specification Version", "../SG20/SG21/RFF~ZZZ/@C506.1154",
      also=[const("../SG20/SG21/RFF~ZZZ/@C506.1153", "ZZZ")]),
    OMIT("Pack Specification in Force", "a package identification group has one reference, the version the unit was "
                                        "packed to"),
    V("Receiving Condition", "../SG20/SG21/SG22~cond/CDI/@C564.7006", also=[const("../SG20/SG21/SG22~cond/CDI/@7001", "1")]),
    OMIT("Received Date", NO_UNIT_DATE, within=[RHU]),
    OMIT("Received Time", NO_UNIT_DATE),
    OMIT("Exception Description", NO_UNIT_DATE),
    OMIT("Pallet ID Valid on Receipt", NO_CHECK_CODE),
    OMIT("Pack Specification Compliant", NO_CHECK_CODE),

    # the lines, in the shipment's CPS
    C("Receipt Lines", "."),
    *[C(f"Receipt Line {n}", ".", order=n) for n in range(1, 11)],
    C("Receipt Line", f"{M}=SG16~ship/SG25"),
    V("Line ID", "LIN/@1082"),
    *item(),
    OMIT_C("Tax Category", "RECADV's line has no tax segment", within=["Item"]),
    qty("Received Quantity", "48"),
    qty("Short Quantity", "119"),
    qty("Rejected Quantity", "185"),
    qty("Oversupply Quantity", "121"),
    date("Received Date", "50"),
    text("Note", "AAI", within=["Receipt Line"]),
    variance("Quantity Discrepancy", "", codes4221={"Over": "AC", "Mixed": "CS"},
             codes4295={"Short": "BP", "Damaged": "BA"}),
    variance("Timing Complaint", "", codes4221={"Early": "AI", "Late": "AG", "Outside the appointment": "AZ"}),
    text("Timing Complaint Description", "AFH"),
    variance("Reject Reason", "", codes4221={"Over-supplied": "AC"}, codes4295={"Damaged": "BA"}),
    text("Reject Reason Description", "ACD"),
    action("Reject Action", "REJECT"),
    action("Shortage Action", "SHORTAGE"),
    C("Order Line Reference", "."),
    V("Line ID", "SG33~ON/RFF/@C506.1156", within=["Order Line Reference"],
      also=[const("SG33~ON/RFF/@C506.1153", "ON")]),
    ref("Sales Order Line ID", "VN", "SG33"),
    C("Despatch Line Reference", "."),
    V("Line ID", "SG33~AAK/RFF/@C506.1156", within=["Despatch Line Reference"],
      also=[const("SG33~AAK/RFF/@C506.1153", "AAK")]),
    V("Document Reference ID", "=SG33~AAK/=RFF/@C506.1154", within=["Despatch Line Reference"]),
    ref_date("Document Reference Issue Date", "AAK", "=SG33", within=["Despatch Line Reference"]),
    OMIT("Line Status", "the referenced line's status is that document's; RECADV refers to the line by its number",
         within=["Order Line Reference"]),
    OMIT("Line Status", "the referenced line's status is that document's; RECADV refers to the line by its number",
         within=["Despatch Line Reference"]),
]
