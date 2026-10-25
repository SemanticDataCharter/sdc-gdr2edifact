"""The business documents library's Order Response model as a UN/EDIFACT D.24A ORDRSP.

The qualifiers are the UN-EDIFACT library's paper mapping (mapping/ordrsp.json): the response to the order as a whole
is BGM's response type (4343), the response to each line LIN's action code (1229), a substitute the seller made or
proposes a PIA "substituted for" (4347 4) with its quantity QTY 94. Groups in ORDRSP: SG1 references, SG3 parties (SG4
their references, SG6 their contacts), SG7 tax, SG8 currencies, SG9 payment terms, SG12 delivery terms, SG13 packages,
SG19 allowances and charges (SG22 their amounts), SG27 lines (SG31 price, SG32 references, SG38 tax, SG39 parties);
after UNS the totals and the line count.
"""
from common import (UBL_IDENTIFIERS, C, OMIT, OMIT_C, V, allowances, count, date, delivery_terms,
                    issue_date_time, item, line_delivery, location_party, measure, moa, parties, payment_means,
                    payment_terms, price, qty, record, ref, ref_date, tax, text, totals)

TITLE = "Order Response (business documents library) to UN/EDIFACT D.24A ORDRSP"
ID = "order-response-edifact-d24a"
VERSION = 1
AUTHOR = "Axius SDC, Inc."
DATE = "2026-10-25"
DESCRIPTION = ("The Order Response model's values in a D.24A ORDRSP. Declared: the library links its components to UBL, "
               "not to UN/EDIFACT. The payment means code is the model's own binding to UBL's PaymentMeansCode, which "
               "is UNCL 4461.")
MESSAGE = "ORDRSP"
M = f"/{MESSAGE}/"
RESPONSE = {"Accepted": "AP", "Accepted with changes": "AC", "Rejected": "RE", "Acknowledged": "AB"}
LINE_RESPONSE = {"Accepted": "5", "Accepted with changes": "6", "Rejected": "7", "Substituted": "3"}
SUBSTITUTES = ("Seller Proposed Substitute Line Item", "Seller Substituted Line Item")
NOT_IN_A_SUBSTITUTE = ("a substitute is identified (PIA, substituted for) and counted (QTY 94); the rest of its line "
                       "item has no place in ORDRSP's line")


def substitute(cluster: str):
    rules = [
        C(cluster, "."),
        C("Line Item", ".", within=[cluster]),
        C("Item", ".", within=[cluster]),
        *[C(f"{kind} Item Identification", "+PIA", attributes={"4347": "4"}, within=[cluster])
          for kind in ("Standard", "Seller's", "Buyer's", "Manufacturer's")],
        V("Item Identification Value", "@C212.7140", within=[cluster, "Standard Item Identification"]),
        V("Item Identification Scheme", "@C212.7143", "code", within=[cluster, "Standard Item Identification"],
          table={"Global Trade Item Number (GS1)": "SRV", "Seller's item number": "SA", "Buyer's item number": "IN",
                 "Manufacturer's item number": "MF", "Catalogue item number": "ZZZ", "Mutually agreed": "ZZZ"},
          on_miss="omit"),
        qty("Ordered Quantity", "94", within=[cluster]),
        *[OMIT_C(c, NOT_IN_A_SUBSTITUTE, within=[cluster]) for c in
          ("Price", "Delivery", "Item Dimensions", "Commodity Classification", "Tax Category")],
        *[OMIT(v, NOT_IN_A_SUBSTITUTE, within=[cluster]) for v in
          ("Line ID", "Note", "Line Status", "Line Extension Amount", "Total Tax Amount", "Partial Delivery Allowed",
           "Back Order Allowed", "Item Name", "Item Description", "Brand Name", "Model Name", "Pack Quantity",
           "Pack Size", "Item Extended ID")],
    ]
    return rules


RULES = [
    *record("Order Response Governed Record", "Order Response", MESSAGE),
    C("Order Response Document", "."),
    *UBL_IDENTIFIERS,
    *issue_date_time(MESSAGE),
    V("Order Response ID", "BGM/@C106.1004", also=[{"to": "BGM/@C002.1001", "transform": "constant", "value": "231"}]),
    V("Order Response Type", "BGM/@4343", "code", table=RESPONSE),
    ref("Sales Order ID", "VN", "SG1"),
    ref("Customer Reference", "CR", "SG1"),
    ref("Accounting Cost", "ADE", "SG1"),
    text("Note", "AAI"),
    V("Document Currency", "SG8~2/CUX/@C504.6345", also=[{"to": "SG8~2/CUX/@C504.6347", "transform": "constant",
                                                         "value": "2"}]),
    OMIT("Pricing Currency", "CUX's further currency is a target for conversion at a rate; a pricing currency has no "
                             "qualifier of its own"),
    count("Line Count", "2", at=M),
    C("Validity Period", "."),
    C("Date Range", "."),
    date("Date Range Start", "157", within=["Validity Period"]),
    date("Date Range End", "799", within=["Validity Period"]),
    # the shipment totals: a package group (SG13) of all packages, with its gross weight and volume
    C("Response Shipment Totals", "SG13/PAC"),
    V("Total Packages Quantity", "@7224"),
    measure("Gross Weight", "AAE", "AAD", at="../"),
    measure("Net Weight", "AAE", "AAC", at="../"),
    measure("Gross Volume", "AAE", "AAW", at="../"),
    measure("Net Volume", "AAE", "AAX", at="../"),

    C("Order Reference", "."),
    ref("Order ID", "ON", "SG1"),
    ref_date("Issue Date", "ON", "SG1", within=["Order Reference"]),
    OMIT("Order Type", "ORDRSP refers to the order by its number (RFF ON); the order's type is the order's"),
    C("Order Document Reference", "."),
    C("Order Change Document Reference", "."),
    C("Originator Document Reference", "."),
    C("Additional Document Reference", "."),
    C("Document Reference", "."),
    *[r for cluster, q in (("Order Document Reference", "OP"), ("Order Change Document Reference", "ACE"),
                           ("Originator Document Reference", "ABO"), ("Additional Document Reference", "ACD"))
      for r in (ref("Document Reference ID", q, "SG1", within=[cluster]),
                ref_date("Document Reference Issue Date", q, "SG1", within=[cluster]))],
    OMIT("Document Type", "a reference group carries a reference number and its date, not the document's type"),
    OMIT("Document Description", "a reference group carries a reference number and its date, not a description"),
    C("Contract", "."),
    ref("Contract ID", "CT", "SG1"),
    V("Contract Issue Date", "SG1~CT/DTM/@C507.2380", "format", format="%Y%m%d",
      also=[{"to": "SG1~CT/DTM/@C507.2005", "transform": "constant", "value": "126"}]),
    OMIT("Contract Type", "a reference group carries a contract's number and its date, not its type"),
    C("Transaction Conditions", "."),
    ref("Transaction Conditions ID", "AJS", "SG1"),
    text("Transaction Conditions Description", "AAR"),
    OMIT_C("Document Reference", "the agreement is referred to by its number (RFF AJS)",
           within=["Transaction Conditions"]),

    *parties({"Seller Supplier Party": "SE", "Buyer Customer Party": "BY", "Originator Customer Party": "OB",
              "Accounting Supplier Party": "II", "Accounting Customer Party": "IV"},
             "SG3", "SG4", "SG6", MESSAGE, sender="Seller Supplier Party", recipient="Buyer Customer Party"),

    C("Delivery", "."),
    ref("Delivery ID", "AAJ", "SG1"),
    date("Latest Delivery Date", "17"),
    C("Requested Delivery Period", "."),
    date("Date Range Start", "64", within=["Requested Delivery Period"]),
    date("Date Range End", "63", within=["Requested Delivery Period"]),
    OMIT("Delivery Quantity", "ORDRSP's header has no quantity; what is confirmed is each line's quantity"),
    *location_party("Delivery Location", "ST", "SG3", MESSAGE),
    C("Delivery Party", f"{M}SG3~DP/NAD", attributes={"3035": "DP"}),
    *delivery_terms("SG12"),
    *payment_means("Payment Means Instruction"),
    *payment_terms("SG9"),
    *allowances("SG19", "SG22"),
    *tax("SG7", "SG38", summary_at=M),
    *totals("Legal Monetary Total", M),

    C("Order Response Lines", "."),
    *[C(f"Order Response Line {n}", ".", order=n) for n in range(1, 11)],
    C("Order Response Line", f"{M}SG27"),
    C("Line Item", "."),
    V("Line ID", "LIN/@1082"),
    V("Line Response", "=LIN/@1229", "code", table=LINE_RESPONSE),
    OMIT("Line Status", "a response line's action code (1229) carries its response; the line item's own status has "
                        "no second place", within=["Order Response Line", "Line Item"]),
    *item(),
    qty("Ordered Quantity", "21"),
    moa("Line Extension Amount", "203"),
    moa("Total Tax Amount", "124", within=["Line Item"]),
    text("Note", "AAI", within=["Line Item"]),
    OMIT("Partial Delivery Allowed", "ORDRSP has no element for allowing a partial delivery"),
    OMIT("Back Order Allowed", "ORDRSP has no element for allowing a back order"),
    *price("SG31"),
    *line_delivery("SG39"),
    C("Order Line Reference", "."),
    V("Line ID", "SG32~ON/RFF/@C506.1156", within=["Order Line Reference"],
      also=[{"to": "SG32~ON/RFF/@C506.1153", "transform": "constant", "value": "ON"}]),
    ref("Sales Order Line ID", "VN", "SG32"),
    OMIT("Line Status", "the order line's status is the order's; ORDRSP answers the line with its own action code",
         within=["Order Line Reference"]),
    C("Line Document Reference", "."),
    ref("Document Reference ID", "ACD", "SG32", within=["Line Document Reference"]),
    ref_date("Document Reference Issue Date", "ACD", "SG32", within=["Line Document Reference"]),
    *[r for s in SUBSTITUTES for r in substitute(s)],
]
