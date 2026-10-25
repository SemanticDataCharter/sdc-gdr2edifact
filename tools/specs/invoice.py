"""The business documents library's Invoice model as a UN/EDIFACT D.24A INVOIC; the Credit Note is the same message
(credit_note.py) with its own document name codes.

The qualifiers are the UN-EDIFACT library's paper mapping (mapping/invoic.json). Groups in INVOIC: SG1 references,
SG2 parties (SG3 their references, SG5 their contacts), SG6 tax, SG8 payment terms, SG12 delivery terms, SG16
allowances and charges (SG20 their amounts), SG24 adjustments, SG27 lines (SG28 amounts, SG30 price, SG31 references,
SG35 tax, SG36 parties, SG40 allowances and charges with SG43 their amounts); after UNS the line count and the totals,
each a MOA in a group of its own (SG52).
"""
from common import (UBL_IDENTIFIERS, C, OMIT, OMIT_C, V, allowances, const, count, date, delivery_terms,
                    issue_date_time, item, location_party, moa, parties, payment_means, payment_terms,
                    price, qty, record, ref, ref_date, tax, text, totals)

TITLE = "Invoice (business documents library) to UN/EDIFACT D.24A INVOIC"
ID = "invoice-edifact-d24a"
VERSION = 1
AUTHOR = "Axius SDC, Inc."
DATE = "2026-10-25"
DESCRIPTION = ("The Invoice model's values in a D.24A INVOIC. Declared: the library links its components to UBL, not to "
               "UN/EDIFACT. The payment means code is the model's own binding to UBL's PaymentMeansCode, which is UNCL "
               "4461.")
MESSAGE = "INVOIC"
INVOICE_TYPE = {"Commercial invoice": "380", "Corrected invoice": "384", "Prepayment invoice": "386",
                "Self-billed invoice": "389", "Final invoice": "380"}
NO_WITHHOLDING = "TAX's function qualifier (5283) has no code for a tax withheld from the payment"


def period(at: str, within: list[str]):
    """An invoicing period: one DTM 263 holding start and end (format 718, CCYYMMDD-CCYYMMDD)."""
    seg = f"{at}DTM~263"
    return [
        V("Date Range Start", f"{seg}/@C507.2380", "format", format="%Y%m%d", within=within,
          also=[const(f"{seg}/@C507.2005", "263"), const(f"{seg}/@C507.2379", "718")]),
        V("Date Range End", f"{seg}/@C507.2380+", "format", format="-%Y%m%d", within=within),
    ]


def body(data: str, document: str, number: str, type_label: str, types: dict, line: str, quantity: tuple[str, str]):
    m = f"/{MESSAGE}/"
    lines = f"{line}s"
    return [
        *record(f"{data} Governed Record", data, MESSAGE),
        C(document, "."),
        *UBL_IDENTIFIERS,
        *issue_date_time(MESSAGE),
        V(number, "BGM/@C106.1004"),
        V(type_label, "BGM/@C002.1001", "code", table=types),
        OMIT("Document Status", "BGM's message function (1225) says whether the message is an original, a change or "
                                "a cancellation; the record's document status is the business document's own"),
        date("Due Date", "13"),
        date("Tax Point Date", "131"),
        ref("Buyer Reference", "CR", "SG1"),
        ref("Accounting Cost", "ADE", "SG1"),
        text("Note", "AAI"),
        V("Document Currency", "SG7~2/CUX/@C504.6345", also=[const("SG7~2/CUX/@C504.6347", "2")]),
        *[OMIT(c, "CUX's further currency is a target for conversion at a rate; this currency has no qualifier of its "
                  "own") for c in ("Pricing Currency", "Tax Currency", "Payment Currency")],
        count("Line Count", "2", at=m),
        C("Invoice Period", "."),
        C("Date Range", "."),
        *period("", [document, "Invoice Period"]),

        C("Order Reference", "."),
        ref("Order ID", "ON", "SG1"),
        ref_date("Issue Date", "ON", "SG1", within=["Order Reference"]),
        ref("Sales Order ID", "VN", "SG1"),
        OMIT("Order Type", "INVOIC refers to the order by its number (RFF ON); the order's type is the order's"),
        C("Billing Reference", "."),
        C("Invoice Document Reference", "."),
        C("Despatch Document Reference", "."),
        C("Receipt Document Reference", "."),
        C("Originator Document Reference", "."),
        C("Additional Document Reference", "."),
        C("Document Reference", "."),
        *[r for cluster, q in (("Invoice Document Reference", "IV"), ("Despatch Document Reference", "AAK"),
                               ("Receipt Document Reference", "ALO"), ("Originator Document Reference", "ABO"),
                               ("Additional Document Reference", "ACD"))
          for r in (ref("Document Reference ID", q, "SG1", within=[cluster]),
                    ref_date("Document Reference Issue Date", q, "SG1", within=[cluster]))],
        OMIT("Document Type", "a reference group carries a reference number and its date, not the document's type"),
        OMIT("Document Description", "a reference group carries a reference number and its date, not a description"),
        C("Contract", "."),
        ref("Contract ID", "CT", "SG1"),
        V("Contract Issue Date", "SG1~CT/DTM/@C507.2380", "format", format="%Y%m%d",
          also=[const("SG1~CT/DTM/@C507.2005", "126")]),
        OMIT("Contract Type", "a reference group carries a contract's number and its date, not its type"),

        *parties({"Accounting Supplier Party": "II", "Accounting Customer Party": "IV", "Buyer Customer Party": "BY",
                  "Seller Supplier Party": "SE", "Payee Party": "PE"},
                 "SG2", "SG3", "SG5", MESSAGE, sender="Accounting Supplier Party", recipient="Accounting Customer Party"),
        OMIT_C("Tax Representative Party", "the directory's party function codes (3035) have no tax representative"),

        C("Delivery", "."),
        ref("Delivery ID", "AAJ", "SG1"),
        date("Latest Delivery Date", "17"),
        C("Requested Delivery Period", "."),
        date("Date Range Start", "64", within=[data, "Delivery", "Requested Delivery Period"]),
        date("Date Range End", "63", within=[data, "Delivery", "Requested Delivery Period"]),
        OMIT("Delivery Quantity", "INVOIC's header has no quantity; what is invoiced is each line's quantity"),
        *location_party("Delivery Location", "ST", "SG2", MESSAGE),
        OMIT_C("Delivery Party", "the party delivered to is named by the delivery location (NAD ST)"),
        *delivery_terms("SG12"),
        *payment_means("Payment Means Instruction"),
        *payment_terms("SG8"),
        C("Prepaid Payment", "."),
        ref("Payment ID", "PQ", "SG1"),
        ref("Payment Instruction ID", "AEK", "SG1"),
        moa("Paid Amount", "11", at=m, group="SG52~11"),
        date("Payment Received Date", "193"),
        date("Paid Date", "209"),
        *allowances("SG16", "SG20"),
        *tax("SG6", "SG35", summary_at=m, summary_group="SG52~176"),
        OMIT_C("Withholding Tax Total", NO_WITHHOLDING),
        *totals("Legal Monetary Total", m, group="SG52"),

        C(lines, "."),
        *[C(f"{line} {n}", ".", order=n) for n in range(1, 11)],
        C(line, f"{m}SG27"),
        V("Line ID", "LIN/@1082"),
        *item(),
        qty(*quantity),
        moa("Line Extension Amount", "203", group="SG28~203"),
        OMIT("Tax Inclusive Line Extension Amount", "a line's amounts are qualified by 5025, which has no line amount "
                                                    "including tax"),
        date("Tax Point Date", "131", within=[line]),
        ref("Accounting Cost", "ADE", "SG31", within=[line]),
        OMIT("Free of Charge", "INVOIC states free goods as a quantity (QTY 192), not as a flag on the line"),
        text("Note", "AAI", within=[line]),
        *period("", [line, "Invoice Period"]),
        *price("SG30"),
        # the line's tax: its subtotal a TAX of the line (SG35), its total the line's MOA 124 (SG28)
        C("Tax Subtotal", "SG35/TAX", attributes={"5283": "7"}, within=[line]),
        moa("Tax Amount", "124", group="SG28~124", within=[line, "Tax Total"]),
        moa("Tax Amount", "124", at="../", within=[line, "Tax Total", "Tax Subtotal"]),
        moa("Taxable Amount", "125", at="../", within=[line, "Tax Total", "Tax Subtotal"]),
        C("Allowance Charge", "SG40/ALC", within=[line]),
        moa("Allowance Charge Amount", "8", at="../", group="SG43~8", within=[line, "Allowance Charge"]),
        moa("Base Amount", "25", at="../", group="SG43~25", within=[line, "Allowance Charge"]),
        C("Order Line Reference", "."),
        V("Line ID", "SG31~ON/RFF/@C506.1156", within=["Order Line Reference"],
          also=[const("SG31~ON/RFF/@C506.1153", "ON")]),
        ref("Sales Order Line ID", "VN", "SG31"),
        *[r for cluster, q in (("Despatch Line Reference", "AAK"), ("Receipt Line Reference", "ALO"))
          for r in (V("Line ID", f"SG31~{q}/RFF/@C506.1156", within=[cluster],
                      also=[const(f"SG31~{q}/RFF/@C506.1153", q)]),
                    V("Document Reference ID", f"=SG31~{q}/=RFF/@C506.1154", within=[cluster]),
                    ref_date("Document Reference Issue Date", q, "=SG31", within=[cluster]))],
        *[OMIT("Line Status", "the referenced line's status is that document's; INVOIC refers to the line by its "
                              "number", within=[c]) for c in
          ("Order Line Reference", "Despatch Line Reference", "Receipt Line Reference")],
        C("Line Document Reference", "."),
        ref("Document Reference ID", "ACD", "SG31", within=["Line Document Reference"]),
        ref_date("Document Reference Issue Date", "ACD", "SG31", within=["Line Document Reference"]),
    ]


RULES = body("Invoice", "Invoice Document", "Invoice ID", "Invoice Type", INVOICE_TYPE, "Invoice Line",
             ("Invoiced Quantity", "47"))
