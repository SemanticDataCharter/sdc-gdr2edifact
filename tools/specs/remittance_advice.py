"""The business documents library's Remittance Advice model as a UN/EDIFACT D.24A REMADV.

The qualifiers are the UN-EDIFACT library's paper mapping (mapping/remadv.json): the remittance advice (BGM 481), the
payer's references in the header, each document paid a line group (SG5) opened by DOC (380 the invoice), with the
amounts debited, credited and outstanding, the credit note taken into account as the line's reference (RFF CD); after
UNS the totals paid, debited and credited.
"""
from common import (DOCUMENT_STATUS, UBL_IDENTIFIERS, C, OMIT, OMIT_C, V, const, date, issue_date_time, moa,
                    parties, payment_means, record, text)

TITLE = "Remittance Advice (business documents library) to UN/EDIFACT D.24A REMADV"
ID = "remittance-advice-edifact-d24a"
VERSION = 1
AUTHOR = "Axius SDC, Inc."
DATE = "2026-10-25"
DESCRIPTION = ("The Remittance Advice model's values in a D.24A REMADV. Declared: the library links its components to "
               "UBL, not to UN/EDIFACT. The payment means code is the model's own binding to UBL's PaymentMeansCode, "
               "which is UNCL 4461.")
MESSAGE = "REMADV"
M = f"/{MESSAGE}/"
LINE = "Remittance Advice Line"


def header_ref(label, q):
    return V(label, f"RFF~{q}/@C506.1154", also=[const(f"RFF~{q}/@C506.1153", q)])


RULES = [
    *record("Remittance Advice Governed Record", "Remittance Advice", MESSAGE),
    C("Remittance Advice Document", "."),
    *UBL_IDENTIFIERS,
    *issue_date_time(MESSAGE),
    V("Remittance Advice ID", "BGM/@C106.1004", also=[const("BGM/@C002.1001", "481")]),
    V("Document Status", "BGM/@1225", "code", table=DOCUMENT_STATUS),
    text("Note", "AAI", within=["Remittance Advice Document"]),
    header_ref("Payment Order Reference", "AEK"),
    header_ref("Payer Reference", "CR"),
    header_ref("Invoicing Party Reference", "IV"),
    V("Document Currency", "SG4~2/CUX/@C504.6345", also=[const("SG4~2/CUX/@C504.6347", "2")]),
    moa("Total Payment Amount", "139", at=M),
    moa("Total Debit Amount", "128", at=M),
    moa("Total Credit Amount", "210", at=M),
    OMIT("Line Count", "REMADV counts nothing in its summary; its lines are the documents paid"),
    C("Invoice Period", "."),
    C("Date Range", "."),
    *[r for at, within in (("", ["Remittance Advice Document", "Invoice Period"]), ("", [LINE, "Invoice Period"]))
      for r in (V("Date Range Start", f"{at}DTM~263/@C507.2380", "format", format="%Y%m%d", within=within,
                  also=[const(f"{at}DTM~263/@C507.2005", "263"), const(f"{at}DTM~263/@C507.2379", "718")]),
                V("Date Range End", f"{at}DTM~263/@C507.2380+", "format", format="-%Y%m%d", within=within))],

    *parties({"Accounting Customer Party": "PR", "Accounting Supplier Party": "II", "Payee Party": "PE"},
             "SG1", "SG2", "SG3", MESSAGE, sender="Accounting Customer Party", recipient="Accounting Supplier Party"),
    *payment_means("Payment Means Instruction"),
    OMIT_C("Tax Total", "REMADV carries tax only within an adjustment; the remittance's tax total has no place"),
    OMIT_C("Additional Document Reference", "REMADV's references in its header are the payment's; a further document "
                                            "has no qualifier there"),
    OMIT_C("Billing Reference", "REMADV names each document paid in a line of its own (DOC)",
           within=["Remittance Advice"]),

    # each document paid: a line group opened by DOC, the invoice's number and date
    C("Remittance Advice Lines", "."),
    *[C(f"Remittance Advice Line {n}", ".", order=n) for n in range(1, 11)],
    C(LINE, f"{M}SG5"),
    C("Billing Reference", ".", within=["Remittance Advice", LINE]),
    C("Invoice Document Reference", ".", within=["Remittance Advice", LINE]),
    C("Credit Note Document Reference", ".", within=["Remittance Advice", LINE]),
    C("Document Reference", ".", within=["Remittance Advice", LINE]),
    V("Document Reference ID", "DOC/@C503.1004", within=[LINE, "Invoice Document Reference"],
      also=[const("DOC/@C002.1001", "380")]),
    date("Document Reference Issue Date", "171", within=[LINE, "Invoice Document Reference"]),
    V("Document Reference ID", "RFF~CD/@C506.1154", within=[LINE, "Credit Note Document Reference"],
      also=[const("RFF~CD/@C506.1153", "CD")]),
    OMIT("Document Reference Issue Date", "a line has one reference date, the invoice's",
         within=[LINE, "Credit Note Document Reference"]),
    OMIT("Document Type", "DOC's document name code says the document's kind (380 an invoice)", within=[LINE]),
    OMIT("Document Description", "DOC has no element for a description", within=[LINE]),
    OMIT("Line ID", "REMADV's lines are identified by the document each pays (DOC)", within=[LINE]),
    moa("Debit Line Amount", "39"),
    moa("Credit Line Amount", "210"),
    moa("Balance Amount", "9"),
    V("Invoicing Party Reference", "RFF~IV/@C506.1154", within=[LINE], also=[const("RFF~IV/@C506.1153", "IV")]),
    OMIT("Payment Purpose", "REMADV's line has no free text; a payment's purpose is a code a partner agrees"),
    OMIT("Note", "REMADV's line has no free text", within=[LINE]),
    *[OMIT_C(p, "a line names one party (NAD, at most two); the parties of the remittance are its header's",
             within=[LINE]) for p in ("Accounting Customer Party", "Accounting Supplier Party", "Buyer Customer Party",
                                      "Seller Supplier Party", "Payee Party")],
    C("Line Document Reference", ".", within=[LINE]),
    OMIT("Document Reference ID", "a line's reference is the credit note taken into account (RFF CD)",
         within=[LINE, "Line Document Reference"]),
    OMIT("Document Reference Issue Date", "a line has one reference date, the invoice's",
         within=[LINE, "Line Document Reference"]),
]
