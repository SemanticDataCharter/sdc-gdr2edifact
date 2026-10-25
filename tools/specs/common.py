"""Rules every business documents library model shares with UN/EDIFACT D.24A: the record's own clusters, parties and
addresses, references, dates, quantities, amounts, items.

The qualifiers are the UN-EDIFACT library's (its mapping/*.json, reviewed by hand on 4 October 2026, from which the
library's qualifier tokens were published). The segment groups that hold a party, its references and its contacts are
numbered differently in each message, so the party rules take them as arguments.

Paths: a message is a tree whose root is the message type; `SG<n>` a segment group, a tag a segment, `~x` after either
tells apart segments or groups of the same tag (`DTM~137`, `SG1~ON`); a segment's data are attributes named by the
directory (`@3035`, `@C082.3039`, `@C080.3036#2` for a component's second occurrence, `@C212#2.7140` for a composite's
second occurrence in its segment). `..` goes up, `+name` is a segment of the value's own, `=name` joins the element of
that name the parent already has.
"""
REC21_PREFIX = "https://unece.org/trade/uncefact/cl-recommendations"
UBL_CL = "http://docs.oasis-open.org/ubl/os-UBL-2.3/cl/gc/default/"
#: UN/ECE Recommendation 20 codes for the SI unit symbols the Default library's measure components carry.
REC20 = {"mm": "MMT", "cm": "CMT", "m": "MTR", "km": "KMT", "mg": "MGM", "g": "GRM", "kg": "KGM", "mL": "MLT",
         "L": "LTR", "°C": "CEL", "K": "KEL"}
#: A party identification scheme as the code list agency (3055) and, where 3055 has none, the list named in 1131.
PARTY_AGENCY = {"Global Location Number (GS1)": "9", "DUNS number": "16", "Assigned by the buyer": "92",
                "Assigned by the seller": "91", "Tax identifier": "ZZZ", "Company registration number": "ZZZ",
                "Mutually agreed": "ZZZ"}
PARTY_LIST = {"Tax identifier": "TAX", "Company registration number": "CRN"}
#: An item identification scheme as the item type identification code (7143) and the list named in 1131.
ITEM_TYPE = {"Global Trade Item Number (GS1)": "SRV", "Seller's item number": "SA", "Buyer's item number": "IN",
             "Manufacturer's item number": "MF", "Catalogue item number": "ZZZ", "Mutually agreed": "ZZZ"}
ITEM_LIST = {"Catalogue item number": "CAT"}
#: UN/ECE Recommendation 21 package type codes for the business documents' handling unit and packaging tokens (the
#: model binds these tokens to the Recommendations' page, without a code, so the code is declared here).
REC21 = {"Pallet": "PX", "Case": "CS", "Carton": "CT", "Bag": "BG", "Tray": "PU", "Drum": "DR", "Bale": "BL",
         "Crate": "CR", "Roll cage": "CW", "Container": "CN"}
LINE_STATUS = {"Added": "1", "Revised": "3", "Cancelled": "37", "Disputed": "50", "No status": ""}
DOCUMENT_STATUS = {"Original": "9", "Revised": "5", "Cancelled": "1"}


def C(label, to, **kw):
    return {"cluster": label, "to": to, **kw}


def V(label, to, transform="copy", **kw):
    return {"component": label, "to": to, "transform": transform, **kw}


def OMIT_C(label, reason, **kw):
    return {"cluster": label, "to": "-", "transform": "omit", "reason": reason, **kw}


def OMIT(label, reason, **kw):
    return {"component": label, "to": "-", "transform": "omit", "reason": reason, **kw}


def const(to, value):
    return {"to": to, "transform": "constant", "value": value}


def date(label, qualifier, at="", group=None, **kw):
    """A date as a DTM of its qualifier (format 102 inferred from the value), in its own group when given."""
    seg = f"{at}{group + '/' if group else ''}DTM~{qualifier}"
    return V(label, f"{seg}/@C507.2380", "format", format="%Y%m%d",
             also=[const(f"{seg}/@C507.2005", qualifier)] + kw.pop("also", []), **kw)


def ref(label, qualifier, group, at="", attr="C506.1154", **kw):
    """A reference as an RFF of its qualifier, opening its group (`group~qualifier`)."""
    seg = f"{at}{group}~{qualifier}/RFF"
    return V(label, f"{seg}/@{attr}", also=[const(f"{seg}/@C506.1153", qualifier)] + kw.pop("also", []), **kw)


def ref_date(label, qualifier, group, at="", **kw):
    """The date of a reference: DTM 171 in the reference's group."""
    seg = f"{at}{group}~{qualifier}/DTM"
    return V(label, f"{seg}/@C507.2380", "format", format="%Y%m%d", also=[const(f"{seg}/@C507.2005", "171")], **kw)


def text(label, qualifier, at="", **kw):
    """Free text as an FTX of its subject qualifier; past 512 characters it continues in the next 4440."""
    seg = f"{at}FTX~{qualifier}"
    return V(label, f"{seg}/@C108.4440", also=[const(f"{seg}/@4451", qualifier)] + kw.pop("also", []), **kw)


def qty(label, qualifier, at="", units=True, **kw):
    seg = f"{at}QTY~{qualifier}"
    if units:
        kw["units"] = {"to": "@C186.6411", "transform": "copy"}
    return V(label, f"{seg}/@C186.6060", also=[const(f"{seg}/@C186.6063", qualifier)] + kw.pop("also", []), **kw)


def moa(label, qualifier, at="", group=None, **kw):
    seg = f"{at}{group + '/' if group else ''}MOA~{qualifier}"
    return V(label, f"{seg}/@C516.5004", units={"to": "@C516.6345", "transform": "copy"},
             also=[const(f"{seg}/@C516.5025", qualifier)] + kw.pop("also", []), **kw)


def measure(label, purpose, dimension, at="", **kw):
    """A measurement: MEA with its purpose (6311) and dimension (6313), the value in C174 with its Recommendation 20
    unit."""
    seg = f"{at}MEA~{dimension}"
    return V(label, f"{seg}/@C174.6314", units={"to": "@C174.6411", "transform": "code", "table": REC20},
             also=[const(f"{seg}/@6311", purpose), const(f"{seg}/@C502.6313", dimension)] + kw.pop("also", []), **kw)


def count(label, qualifier, at="", **kw):
    seg = f"{at}CNT~{qualifier}"
    return V(label, f"{seg}/@C270.6066", also=[const(f"{seg}/@C270.6069", qualifier)], **kw)


def record(governed: str, data: str, message: str):
    return [
        C(governed, message),
        C(data, "."),
        OMIT_C("Audit Event", "the record's audit event: UN/EDIFACT has no place for it"),
        OMIT_C("PROV Activity", "the record's provenance: UN/EDIFACT has no place for it"),
        OMIT_C("PROV Agent", "the record's provenance: UN/EDIFACT has no place for it"),
        OMIT_C("PROV Entity", "the record's provenance: UN/EDIFACT has no place for it"),
    ]


#: The UBL-facing identifiers of a business document, which UN/EDIFACT's envelope and BGM already settle.
UBL_IDENTIFIERS = [
    OMIT("Customization ID", "a UBL customization identifier; UN/EDIFACT names the message and directory in UNH"),
    OMIT("Profile ID", "a UBL profile identifier; UN/EDIFACT names the message and directory in UNH"),
    OMIT("Profile Execution ID", "a UBL profile execution identifier; UN/EDIFACT has no element for it"),
    OMIT("Document UUID", "a UBL document UUID; the message is identified by BGM's document number"),
    OMIT("Copy Indicator", "UN/EDIFACT's message function (BGM 1225) does not distinguish a copy from an original "
                           "here"),
]


def issue_date_time(message: str):
    """The issue date and time: one DTM 137 (102 for a date, 204 with the time), and the interchange's date and
    time of preparation."""
    return [
        V("Issue Date", "DTM~137/@C507.2380", "format", format="%Y%m%d",
          also=[const("DTM~137/@C507.2005", "137"),
                {"to": f"/{message}/=UNB/@S004.0017", "transform": "format", "format": "%y%m%d"}]),
        V("Issue Time", "DTM~137/@C507.2380+", "format", format="%H%M%S",
          also=[{"to": f"/{message}/=UNB/@S004.0019", "transform": "format", "format": "%H%M"}]),
    ]


def parties(roles: dict[str, str], PG: str, RG: str, CG: str, message: str, sender: str, recipient: str):
    """Each party as an NAD of its function (3035) opening a party group, with its references (RFF) and contacts
    (CTA, COM) in the groups under it. The sender's and the recipient's identifications are also the interchange's."""
    rules = [C(wrapper, f"/{message}/{PG}/NAD", attributes={"3035": code}) for wrapper, code in roles.items()]
    unb = f"/{message}/=UNB/@"
    rules += [
        V("Party Identification Value", "@C082.3039"),
        V("Party Identification Value", "@C082.3039", within=[sender],
          also=[{"to": unb + "S002.0004", "transform": "copy"}, const(unb + "S002.0007", "14")]),
        V("Party Identification Value", "@C082.3039", within=[recipient],
          also=[{"to": unb + "S003.0010", "transform": "copy"}, const(unb + "S003.0007", "14")]),
        C("Supplier Party", "."),
        C("Customer Party", "."),
        C("Party", "."),
        C("Party Identification", "."),
        C("Party Legal Entity", "."),
        C("US Address", "."),
        C("International Address", "."),
        V("Party Identification Scheme", "@C082.3055", "code", table=PARTY_AGENCY, on_miss="omit",
          also=[{"to": "@C082.1131", "transform": "code", "table": PARTY_LIST, "on_miss": "omit"}]),
        V("Organization Name", "@C080.3036"),
        V("Registration Name", "@C080.3036#2"),
        ref("Company ID", "XA", RG, at="../"),
        ref("Customer Assigned Account ID", "IA", RG, at="../"),
        ref("Supplier Assigned Account ID", "IT", RG, at="../"),
        V("Address (Line 1)", "@C059.3042"),
        V("Address (Line 2)", "@C059.3042#2"),
        V("City Name", "@3164"),
        V("US State Code", "@C819.3229"),
        V("Region Name", "@C819.3228"),
        V("US ZIP Code", "@3251"),
        V("Postal Code", "@3251"),
        V("Country Code ISO 3166", "@3207"),
        C("Party Contact", f"../{CG}/CTA", attributes={"3139": "IC"}),
        C("Contact Point", "."),
        V("Contact Name", "@C056.3412"),
        V("Phone Number", "../+COM/@C076.3148", also=[const("../+COM/@C076.3155", "TE")]),
        V("Fax Number", "../+COM/@C076.3148", also=[const("../+COM/@C076.3155", "FX")]),
        V("Email Address", "../+COM/@C076.3148", also=[const("../+COM/@C076.3155", "EM")]),
        V("Website URL", "../+COM/@C076.3148", also=[const("../+COM/@C076.3155", "AH")]),
        OMIT("Endpoint ID", "the party's identification in NAD is its address for interchange; NAD has no separate "
                            "endpoint"),
        OMIT("Contact Department", "CTA's contact identifier (3413) is a code of at most 17 characters, not a "
                                   "department's name"),
        OMIT("Contact Job Title", "CTA has no element for a job title"),
        OMIT("Contact Method", "COM's channel (3155) is set by the number written; there is no preferred method"),
        OMIT("Contact Use", "COM has no element for the use of a contact point"),
        OMIT("Address Use", "NAD has no element for the use of an address"),
    ]
    return rules


def location_party(cluster: str, code: str, PG: str, message: str, within=None):
    """A location as a party of its own (NAD ST): its identifier, its name, its address."""
    kw = {"within": within} if within else {}
    return [
        C(cluster, f"/{message}/{PG}~{code}/NAD", attributes={"3035": code}, **kw),
        V("Delivery Location ID", "@C082.3039", also=[const("@C082.3055", "9")]),
        V("Delivery Location Name", "@C080.3036"),
    ]


def item(lin: str = "=LIN"):
    """An item on a line: the standard identification in LIN, the seller's and others in PIA, the name in IMD."""
    return [
        C("Item", "."),
        C("Item Identification", "."),
        C("Standard Item Identification", "."),
        V("Item Identification Value", f"{lin}/@C212.7140", within=["Standard Item Identification"]),
        V("Item Identification Scheme", f"{lin}/@C212.7143", "code", table=ITEM_TYPE, on_miss="omit",
          within=["Standard Item Identification"],
          also=[{"to": f"{lin}/@C212.1131", "transform": "code", "table": ITEM_LIST, "on_miss": "omit"}]),
        # one PIA (additional identification) per further identification
        C("Seller's Item Identification", "+PIA", attributes={"4347": "1"}),
        C("Buyer's Item Identification", "+PIA", attributes={"4347": "1"}),
        C("Manufacturer's Item Identification", "+PIA", attributes={"4347": "1"}),
        V("Item Identification Value", "@C212.7140", within=["Seller's Item Identification"]),
        V("Item Identification Scheme", "@C212.7143", "code", table=ITEM_TYPE, on_miss="omit",
          within=["Seller's Item Identification"]),
        V("Item Identification Value", "@C212.7140", within=["Buyer's Item Identification"]),
        V("Item Identification Scheme", "@C212.7143", "code", table=ITEM_TYPE, on_miss="omit",
          within=["Buyer's Item Identification"]),
        V("Item Identification Value", "@C212.7140", within=["Manufacturer's Item Identification"]),
        V("Item Identification Scheme", "@C212.7143", "code", table=ITEM_TYPE, on_miss="omit",
          within=["Manufacturer's Item Identification"]),
        OMIT("Item Extended ID", "PIA and LIN carry one identifier per scheme; an extended identifier has no place"),
        V("Item Name", "IMD~F/@C273.7008", also=[const("IMD~F/@7077", "F")]),
        V("Item Description", "IMD~F/@C273.7008#2", also=[const("IMD~F/@7077", "F")]),
        OMIT("Brand Name", "the directory's item characteristic codes (7081) name no brand; a partner's guide sets one"),
        OMIT("Model Name", "the directory's item characteristic codes (7081) name no model; a partner's guide sets one"),
        qty("Pack Quantity", "59", units=False),
        OMIT("Pack Size", "the pack's contents travel as QTY 59 (Pack Quantity); a second pack figure has no qualifier"),
        OMIT_C("Commodity Classification", "a commodity code goes in PIA with a code list a partner agrees; the "
                                           "library names none"),
        C("Item Dimensions", "."),
        measure("Length/Distance", "AAE", "LN"),
        measure("Weight", "AAE", "AAB"),
        measure("Volume", "AAE", "ABJ"),
    ]


INCOTERMS = "Incoterms 2020"
CHARGE_INDICATOR = {"true": "C", "false": "A"}
PRICE_TYPE = {"Contract price": "CT", "Catalogue price": "CA", "List price": "PC"}


def payment_means(cluster: str):
    """The payment means: PAI with UBL's PaymentMeansCode, which is UNCL 4461 code for code (a lookup)."""
    return [
        C(cluster, "."),
        V("Payment Means", "PAI/@C534.4461", "binding", prefix=UBL_CL + "PaymentMeansCode-2.3.gc", on_miss="omit"),
        date("Payment Due Date", "140", within=[cluster]),
        text("Note", "PMD", within=[cluster]),
    ]


def payment_terms(PG: str):
    """The payment terms: PYT (basic terms) opening its group, with the due date, the settlement period and the
    discount and penalty percentages in it."""
    return [
        C("Payment Terms", f"{PG}/PYT", attributes={"4279": "1"}),
        V("Payment Terms ID", "@C019.4277"),
        V("Note", "@C019.4276", within=["Payment Terms"]),
        V("Settlement Discount Percent", "../PCD~12/@C501.5482", also=[const("../PCD~12/@C501.5245", "12")]),
        V("Penalty Surcharge Percent", "../PCD~15/@C501.5482", also=[const("../PCD~15/@C501.5245", "15")]),
        date("Payment Due Date", "140", at="../", within=["Payment Terms"]),
        C("Settlement Period", "."),
        date("Date Range Start", "7", at="../", within=["Settlement Period"]),
        date("Date Range End", "12", at="../", within=["Settlement Period"]),
    ]


def delivery_terms(TG: str, cluster: str = "Delivery Terms", code: str = "Delivery Terms Code"):
    """The delivery terms: TOD (delivery condition) with the Incoterm, its place as the group's LOC."""
    return [
        C(cluster, f"{TG}/TOD", attributes={"4055": "6", "C100.1131": INCOTERMS, "C100.3055": "ZZZ"}),
        V(code, "@C100.4052"),
        text("Delivery Special Terms", "AAR", at="../../"),
        C("Delivery Location", "../LOC~1", attributes={"3227": "1"}, within=[cluster]),
        V("Delivery Location ID", "@C517.3225", within=[cluster]),
        V("Delivery Location Name", "@C517.3224", within=[cluster]),
        OMIT_C("US Address", "LOC names a place by its identifier and name; the terms' place has no address",
               within=[cluster, "Delivery Location"]),
        OMIT_C("International Address", "LOC names a place by its identifier and name; the terms' place has no "
                                         "address", within=[cluster, "Delivery Location"]),
    ]


def allowances(AG: str, MG: str):
    """An allowance or charge: ALC (5463 from the charge indicator) opening its group, the reason's name as text, the
    amount and its base each a MOA in a group of its own."""
    return [
        C("Allowance Charge", f"{AG}/ALC"),
        V("Charge Indicator", "@5463", "code", table=CHARGE_INDICATOR),
        V("Allowance Charge Reason", "@C214.7160"),
        V("Allowance Charge Reason Text", "@C214.7160#2"),
        moa("Allowance Charge Amount", "8", at="../", group=f"{MG}~8"),
        moa("Base Amount", "25", at="../", group=f"{MG}~25"),
        OMIT("Multiplier Factor", "ALC's groups carry a quantity, a percentage, an amount or a rate; a multiplier "
                                  "factor is none of them"),
    ]


def tax(TG: str, LTG: str | None = None, summary_at: str = "", summary_group: str | None = None):
    """Tax: the total tax as the summary's MOA 176; each subtotal a TAX (5283 tax) opening its group with the tax
    amount (MOA 124); an item's tax category the line's TAX group."""
    rules = [
        C("Tax Total", "."),
        moa("Tax Amount", "176", at=summary_at, group=summary_group),
        C("Tax Subtotal", f"{TG}/TAX", attributes={"5283": "7"}),
        moa("Tax Amount", "124", at="../", within=["Tax Subtotal"]),
        OMIT("Taxable Amount", "a tax group holds one amount, the tax; the document's taxable base is its tax "
                               "exclusive amount (MOA 125)", within=["Tax Subtotal"]),
        C("Tax Category", "."),
        V("Tax Category ID", "@5305"),
        V("Tax Percent", "@C243.5278"),
        OMIT("Tax Category Name", "TAX identifies a category by its code (5305); it has no element for a name"),
        C("Tax Scheme", "."),
        V("Tax Scheme Name", "@C241.5152"),
        OMIT("Tax Scheme ID", "TAX types a tax by the directory's code (5153) and names it (5152); a jurisdiction's "
                              "own scheme identifier has no element"),
    ]
    if LTG:
        rules.append(C("Tax Category", f"{LTG}/TAX", attributes={"5283": "7"}, within=["Item"]))
    else:
        rules.append(OMIT_C("Tax Category", "this message's line has no tax segment", within=["Item"]))
    return rules


def totals(cluster: str, at: str, group: str | None = None):
    """The document's monetary totals: each a MOA of its qualifier, in the summary (in a group of its own where the
    message puts summary amounts in groups)."""
    g = (lambda q: f"{group}~{q}") if group else (lambda q: None)
    return [
        C(cluster, "."),
        moa("Line Extension Total Amount", "79", at=at, group=g("79")),
        moa("Tax Exclusive Amount", "125", at=at, group=g("125")),
        moa("Tax Inclusive Amount", "128", at=at, group=g("128")),
        moa("Allowance Total Amount", "260", at=at, group=g("260")),
        moa("Charge Total Amount", "131", at=at, group=g("131")),
        moa("Prepaid Amount", "113", at=at, group=g("113")),
        moa("Payable Rounding Amount", "165", at=at, group=g("165")),
        moa("Payable Amount", "9", at=at, group=g("9")),
    ]


def price(PG: str):
    """The price: PRI (calculation net) opening its group, with its base quantity and validity."""
    return [
        C("Price", f"{PG}/PRI", attributes={"C509.5125": "AAA"}),
        V("Price Amount", "@C509.5118"),
        V("Base Quantity", "@C509.5284", units={"to": "@C509.6411", "transform": "copy"}),
        V("Price Type", "@C509.5375", "code", table=PRICE_TYPE, on_miss="omit"),
        C("Price Validity Period", "."),
        date("Date Range Start", "157", at="../", within=["Price Validity Period"]),
        date("Date Range End", "799", at="../", within=["Price Validity Period"]),
    ]


def line_delivery(LDG: str):
    """A line's own delivery: its dates in the line's DTM, its location a party (NAD ST) of the line."""
    return [
        C("Delivery", ".", within=["Line Item"]),
        date("Latest Delivery Date", "17", within=["Line Item"]),
        date("Date Range Start", "64", within=["Line Item", "Requested Delivery Period"]),
        date("Date Range End", "63", within=["Line Item", "Requested Delivery Period"]),
        OMIT("Delivery ID", "a line's delivery is the document's; the line has no delivery reference",
             within=["Line Item"]),
        OMIT("Delivery Quantity", "the quantity is the line's own (QTY)", within=["Line Item"]),
        C("Delivery Location", f"{LDG}~ST/NAD", attributes={"3035": "ST"}, within=["Line Item"]),
        OMIT_C("Delivery Party", "the party delivered to is the document's", within=["Line Item"]),
    ]
