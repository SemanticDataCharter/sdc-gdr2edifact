"""The business documents library's Torvale Order profile as a UN/EDIFACT D.24A ORDERS: the Order's mapping with the
profile's delivery terms and requirements. The pack specification version Torvale requires is a reference (RFF ZZZ,
mutually defined) of the order; the delivery window in days has no element of its own in ORDERS."""
import order
from common import OMIT, C, ref

TITLE = "Torvale Order (business documents library profile) to UN/EDIFACT D.24A ORDERS"
ID = "torvale-order-edifact-d24a"
VERSION = 1
AUTHOR = "Axius SDC, Inc."
DATE = "2026-10-25"
DESCRIPTION = ("The Torvale Order profile's values in a D.24A ORDERS: the Order's mapping with the profile's delivery "
               "terms and requirements. Declared: the library links its components to UBL, not to UN/EDIFACT.")
MESSAGE = "ORDERS"

RULES = [
    *order.body(MESSAGE, "Torvale Order", "Payment Means Instruction", ("Torvale Delivery Terms", "Torvale Delivery Terms Code")),
    C("Torvale Order Requirements", "."),
    ref("Torvale Pack Specification Version", "ZZZ", "SG1"),
    OMIT("Torvale Delivery Window Days", "ORDERS states a delivery window by its dates (DTM 64 and 63), not by a "
                                         "count of days"),
]
