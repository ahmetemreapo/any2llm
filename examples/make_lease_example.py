"""Build the fictional lease used by the ask and check examples.

Run python examples/make_lease_example.py from the repository root. It needs LibreOffice (soffice) on PATH.
All names, addresses, and amounts are invented.
"""

import subprocess
import tempfile
from html import escape
from pathlib import Path

OUTPUT = Path(__file__).resolve().parent / "lease"

SECTIONS = [
    ("1. Parties and premises", [
        "This residential lease is made between Northfield Housing Cooperative (the Landlord) and the person named "
        "on the signature page (the Tenant).",
        "The premises are apartment 4B at 18 Linden Row, including one storage cage in the basement and shared use "
        "of the courtyard.",
        "The apartment is let unfurnished except for the kitchen appliances listed in Schedule A.",
    ]),
    ("2. Term", [
        "The lease starts on 1 September 2027 and runs for twelve months.",
        "After the first twelve months the lease continues from month to month until either party ends it as set "
        "out in section 14.",
        "Keys are handed over on the start date between 10:00 and 16:00 at the cooperative office.",
    ]),
    ("3. Rent", [
        "The monthly rent is 1,240 euros, payable in advance on or before the third working day of each month.",
        "Rent is paid by bank transfer to the account shown in Schedule B. Cash payments are not accepted.",
        "A late payment fee of 25 euros applies when rent arrives more than ten days after the due date.",
    ]),
    ("4. Rent review", [
        "The Landlord may review the rent once in any twelve-month period.",
        "Any increase may not exceed the change in the national consumer price index over the previous twelve "
        "months plus one percentage point.",
        "The Landlord must give written notice of a rent increase at least two months before it takes effect.",
    ]),
    ("5. Service charges", [
        "A monthly service charge of 95 euros covers cleaning of shared areas, the lift, and garden upkeep.",
        "Heating and hot water are billed separately each quarter based on the apartment's meter.",
        "The Landlord sends a statement of actual service costs by 30 April of each year.",
    ]),
    ("6. Security deposit", [
        "The Tenant pays a security deposit equal to two months' rent before the start date.",
        "The deposit is held in a separate account and earns no interest for either party.",
        "The deposit is refunded within 30 days after the Tenant returns the keys, minus any documented cost of "
        "repairing damage beyond normal wear and tear.",
    ]),
    ("7. Use of the premises", [
        "The Tenant uses the apartment as a private home for no more than four people.",
        "Running a business that receives customers at the apartment requires the Landlord's written consent.",
        "Short-term holiday letting of the apartment, in whole or in part, is not allowed.",
    ]),
    ("8. Pets", [
        "Cats and small caged animals are allowed without consent.",
        "Dogs are allowed only with the Landlord's written consent, which may not be refused without good reason.",
        "The Tenant is responsible for any damage caused by animals kept in the apartment.",
    ]),
    ("9. Repairs and maintenance", [
        "The Landlord keeps the structure, roof, plumbing, wiring, and heating system in good repair.",
        "The Tenant reports defects promptly through the cooperative's maintenance portal.",
        "Urgent defects that affect water, heating, or safety are attended to within 24 hours of the report.",
    ]),
    ("10. Alterations", [
        "The Tenant may hang pictures and shelves and may paint walls in neutral colours.",
        "Structural changes, new fixed installations, and changes to the kitchen require written consent.",
        "At the end of the lease the Tenant restores any alteration made without consent.",
    ]),
    ("11. Access", [
        "The Landlord may enter the apartment for inspections or repairs after giving at least 48 hours' notice.",
        "In an emergency the Landlord may enter without notice and informs the Tenant as soon as possible.",
        "Inspections take place no more than twice a year unless a repair requires more visits.",
    ]),
    ("12. Insurance", [
        "The Landlord insures the building against fire, storm, and water damage.",
        "The Tenant is advised to insure their own belongings and liability.",
        "The Landlord's insurance does not cover the Tenant's furniture or personal items.",
    ]),
    ("13. Subletting", [
        "The Tenant may sublet a room only with the Landlord's written consent.",
        "Subletting the whole apartment is allowed for up to six months when the Tenant works or studies abroad.",
        "The Tenant remains responsible for rent and for the conduct of any subtenant.",
    ]),
    ("14. Ending the lease", [
        "During the first twelve months neither party may end the lease, except under section 15.",
        "After the first twelve months the Tenant may end the lease with three months' written notice, ending on the "
        "last day of a calendar month.",
        "The Landlord may end the lease only on the grounds allowed by law and with six months' written notice.",
    ]),
    ("15. Early termination", [
        "The Tenant may end the lease early if they find a replacement tenant whom the Landlord accepts.",
        "The Landlord may not refuse a suitable replacement tenant without good reason.",
        "An early termination fee of one month's rent applies if no replacement tenant is found.",
    ]),
    ("16. Moving out", [
        "On the last day of the lease the Tenant returns all keys and leaves the apartment clean and empty.",
        "The Landlord and Tenant inspect the apartment together and sign a handover report.",
        "Items left behind after the handover may be removed at the Tenant's cost.",
    ]),
    ("17. Notices and signatures", [
        "Notices under this lease are valid when sent by letter or by e-mail to the addresses on this page.",
        "This lease is governed by the law of the place where the apartment is located.",
        "Signed in two copies, one for each party.",
    ]),
]


def html() -> str:
    pages = []
    for number, (title, clauses) in enumerate(SECTIONS):
        body = "".join(f"<p>{escape(clause)}</p>" for clause in clauses)
        # LibreOffice's HTML import honours inline page breaks, one section per page.
        brk = ' style="page-break-before: always"' if number else ""
        pages.append(f"<h2{brk}>{escape(title)}</h2>{body}")
    style = (
        "body{font-family:'Liberation Serif',serif;font-size:13pt;line-height:1.5}"
        "h1{font-size:20pt}h2{font-size:15pt}"
    )
    return (f"<!doctype html><html><head><meta charset='utf-8'><style>{style}</style></head><body>"
            "<h1>Residential lease — 18 Linden Row, apartment 4B</h1>" + "".join(pages) + "</body></html>")


def main() -> None:
    OUTPUT.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory() as work:
        source = Path(work) / "lease-agreement.html"
        source.write_text(html(), encoding="utf-8")
        subprocess.run(
            ["soffice", "--headless", "--infilter=HTML (StarWriter)", "--convert-to", "pdf:writer_pdf_Export",
             "--outdir", str(OUTPUT),
             str(source)], check=True, capture_output=True,
        )
    (OUTPUT / "house-rules.txt").write_text(
        "Northfield Housing Cooperative — house rules\n\n"
        "Quiet hours are from 22:00 to 07:00 every day.\n"
        "Bicycles are kept in the bicycle room, not in the stairwell.\n"
        "Recycling is collected on Tuesdays; bins go out after 18:00 on Monday.\n"
        "Barbecues with open flames are not allowed on balconies.\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
