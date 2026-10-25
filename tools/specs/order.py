"""The business documents library's Order model as a UN/EDIFACT D.24A ORDERS.

The qualifiers are the UN-EDIFACT library's paper mapping (mapping/orders.json, reviewed 4 October 2026). Groups in
ORDERS: SG1 references, SG2 parties (SG3 their references, SG5 their contacts), SG6 tax, SG8 payment terms, SG12
delivery terms, SG19 allowances and charges (SG22 their amounts), SG29 lines (SG33 price, SG34 references, SG40 tax,
SG41 parties); after UNS, the totals (MOA) and the line count (CNT).
"""
from common import (UBL_IDENTIFIERS, C, OMIT, V, allowances, count, date, delivery_terms, issue_date_time,
                    item, line_delivery, location_party, moa, parties, payment_means, payment_terms, price, qty,
                    record, ref, ref_date, tax, text, totals, LINE_STATUS)

TITLE = "Order (business documents library) to UN/EDIFACT D.24A ORDERS"
ID = "order-edifact-d24a"
VERSION = 1
AUTHOR = "Axius SDC, Inc."
DATE = "2026-10-25"
DESCRIPTION = ("The Order model's values in a D.24A ORDERS. Declared: the library links its components to UBL, not to "
               "UN/EDIFACT. The payment means code is the model's own binding to UBL's PaymentMeansCode, which is UNCL "
               "4461.")
MESSAGE = "ORDERS"
M = f"/{MESSAGE}/"
ORDER_TYPE = {"Standard order": "220", "Blanket order": "221", "Call-off order": "226", "Consignment order": "227",
              "Drop-shipment order": "220", "Repeat order": "220"}


def body(message: str, data: str, payment_means_cluster: str, terms: tuple[str, str]):
    m = f"/{message}/"
    return [
        *record(f"{data} Governed Record", data, message),
        C("Order Document", "."),
        *UBL_IDENTIFIERS,
        *issue_date_time(message),
        V("Order ID", "BGM/@C106.1004"),
        V("Order Type", "BGM/@C002.1001", "code", table=ORDER_TYPE),
        ref("Sales Order ID", "VN", "SG1"),
        ref("Customer Reference", "CR", "SG1"),
        ref("Accounting Cost", "ADE", "SG1"),
        text("Note", "AAI"),
        V("Document Currency", "SG7~2/CUX/@C504.6345", also=[{"to": "SG7~2/CUX/@C504.6347", "transform": "constant",
                                                             "value": "2"}]),
        OMIT("Pricing Currency", "CUX's further currency is a target for conversion at a rate; a pricing currency "
                                 "has no qualifier of its own"),
        count("Line Count", "2", at=m),
        C("Validity Period", "."),
        C("Date Range", "."),
        date("Date Range Start", "157", within=["Validity Period"]),
        date("Date Range End", "799", within=["Validity Period"]),

        C("Quotation Document Reference", "."),
        C("Catalogue Reference", "."),
        C("Originator Document Reference", "."),
        C("Additional Document Reference", "."),
        C("Document Reference", "."),
        *[r for cluster, q in (("Quotation Document Reference", "AAG"), ("Catalogue Reference", "ABN"),
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

        *parties({"Buyer Customer Party": "BY", "Seller Supplier Party": "SE", "Originator Customer Party": "OB",
                  "Accounting Customer Party": "IV"},
                 "SG2", "SG3", "SG5", message, sender="Buyer Customer Party", recipient="Seller Supplier Party"),

        C("Delivery", "."),
        ref("Delivery ID", "AAJ", "SG1"),
        date("Latest Delivery Date", "17"),
        C("Requested Delivery Period", "."),
        date("Date Range Start", "64", within=["Requested Delivery Period"]),
        date("Date Range End", "63", within=["Requested Delivery Period"]),
        OMIT("Delivery Quantity", "ORDERS' header has no quantity; what is ordered is each line's ordered quantity"),
        *location_party("Delivery Location", "ST", "SG2", message),
        C("Delivery Party", f"{m}SG2~DP/NAD", attributes={"3035": "DP"}),
        *delivery_terms("SG12", *terms),
        *payment_means(payment_means_cluster),
        *payment_terms("SG8"),
        *allowances("SG19", "SG22"),
        *tax("SG6", "SG40", summary_at=m),
        *totals("Anticipated Monetary Total", m),

        C("Order Lines", "."),
        *[C(f"Order Line {n}", ".", order=n) for n in range(1, 11)],
        C("Order Line", f"{m}SG29"),
        C("Line Item", "."),
        V("Line ID", "LIN/@1082"),
        V("Line Status", "LIN/@1229", "code", table=LINE_STATUS),
        *item(),
        qty("Ordered Quantity", "21"),
        moa("Line Extension Amount", "203"),
        moa("Total Tax Amount", "124", within=["Line Item"]),
        text("Note", "AAI", within=["Line Item"]),
        OMIT("Partial Delivery Allowed", "ORDERS has no element for allowing a partial delivery"),
        OMIT("Back Order Allowed", "ORDERS has no element for allowing a back order"),
        *price("SG33"),
        *line_delivery("SG41"),
        C("Line Document Reference", "."),
        ref("Document Reference ID", "ACD", "SG34", within=["Line Document Reference"]),
        ref_date("Document Reference Issue Date", "ACD", "SG34", within=["Line Document Reference"]),
    ]


RULES = body(MESSAGE, "Order", "Payment Means", ("Delivery Terms", "Delivery Terms Code"))
