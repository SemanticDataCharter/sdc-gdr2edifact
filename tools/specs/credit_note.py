"""The business documents library's Credit Note model as a UN/EDIFACT D.24A INVOIC: the Invoice's mapping with the
credit note's document name codes (BGM 1001 381 and the credit note types), its credited quantity (QTY 501), and the
discrepancy the credit resolves as an adjustment (AJT, with its reference, description and date)."""
import invoice
from common import C, OMIT, V, date, ref, ref_date, text

TITLE = "Credit Note (business documents library) to UN/EDIFACT D.24A INVOIC"
ID = "credit-note-edifact-d24a"
VERSION = 1
AUTHOR = "Axius SDC, Inc."
DATE = "2026-10-25"
DESCRIPTION = ("The Credit Note model's values in a D.24A INVOIC with the credit note's document name codes. Declared: "
               "the library links its components to UBL, not to UN/EDIFACT. The payment means code is the model's own "
               "binding to UBL's PaymentMeansCode, which is UNCL 4461.")
MESSAGE = "INVOIC"
CREDIT_NOTE_TYPE = {"Credit note": "381", "Self billed credit note": "261", "Factored credit note": "396",
                    "Forwarder's credit note": "532", "Credit note related to goods or services": "81",
                    "Credit note related to financial adjustments": "83"}
LINE = "Credit Note Line"

RULES = [
    *invoice.body("Credit Note", "Credit Note Document", "Credit Note ID", "Credit Note Type", CREDIT_NOTE_TYPE, LINE,
                  ("Credited Quantity", "501")),
    C("Discrepancy Response", "SG24/AJT"),
    V("Discrepancy Response Code", "@4465", "code", table={"Deduction agreed": "1"}, on_miss="omit"),
    ref("Discrepancy Reference ID", "AGG", "SG1", at="../../"),
    text("Discrepancy Description", "ABO", at="../"),
    date("Discrepancy Effective Date", "226", at="../../"),
    # on a line: INVOIC's line has no adjustment segment; the discrepancy's reference, description and date are the line's
    C("Discrepancy Response", ".", within=[LINE]),
    OMIT("Discrepancy Response Code", "INVOIC's line has no adjustment segment for a response code", within=[LINE]),
    ref("Discrepancy Reference ID", "AGG", "SG31", within=[LINE]),
    text("Discrepancy Description", "ABO", within=[LINE]),
    date("Discrepancy Effective Date", "226", within=[LINE]),
    C("Billing Reference", ".", within=[LINE]),
    # on a line, the invoice credited is the line's reference (SG31 RFF IV)
    ref("Document Reference ID", "IV", "SG31", within=[LINE, "Invoice Document Reference"]),
    ref_date("Document Reference Issue Date", "IV", "SG31", within=[LINE, "Invoice Document Reference"]),
]
