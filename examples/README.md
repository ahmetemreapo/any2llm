# Examples

Real output files are checked into this folder. Attach one to your AI chat and check the page citations yourself. [Türkçe](README.tr.md)

> [!TIP]
> If GitHub opens the attachment as text, use the download arrow (↓) at the top of the file view to save the original `.md` file.

## Work example: delivery dates

A supplier offer (PDF), a delivery schedule (Excel), and a meeting note (text). [Browse the source files](delivery-dates/).

1. Download the [delivery dates attachment](delivery-dates-pack/batch_01_of_1.md?plain=1) and attach it in your AI chat.
2. Send this question with it:

   > List the pilot and main shipment dates. Cite the Excel sheet and the original PDF page for each date, and flag any page whose text could not be read.

3. Check pages 1 and 3 of the [original supplier offer](https://raw.githubusercontent.com/ahmetemreapo/any2llm/main/examples/delivery-dates/supplier-offer.pdf#page=1).

<details>
<summary>Expected answer</summary>

| Shipment | Delivery date | Sources |
| --- | --- | --- |
| Pilot | March 12, 2027 | `delivery-schedule.xlsx`, Schedule sheet, and `supplier-offer.pdf`, page 1 |
| Main | March 26, 2027 | `delivery-schedule.xlsx`, Schedule sheet, and `supplier-offer.pdf`, page 3 |

The batch flags page 2 because its text is in an image. Open the original page to read the freight note.

</details>

## Student example: midterm practice

Four research methods files (PDF, PowerPoint, Word, and Excel) in one attachment, plus [the generated chat prompt](midterm/en/PROMPT.txt).

1. Download the [midterm attachment](midterm/en/batch_01_of_1.md?plain=1) and attach it in your AI chat.
2. Send this question with it:

   > Which research design fits the measurement plan? Cite the Excel sheet for what was measured in each class and the original PDF page for the design definition.

3. Check the definition on [page 2 of the original PDF](https://raw.githubusercontent.com/ahmetemreapo/any2llm/main/src/any2llm/demo_assets/en/research-designs.pdf#page=2).

<details>
<summary>Expected answer</summary>

The plan uses a quasi-experimental pretest–posttest design with a nonequivalent comparison group. Two existing classes take the same 10-item terms test before and after the activity, with no random assignment. Class A recalls the terms from memory and Class B rereads them, each for eight minutes. See the Plan sheet in `measurement-plan.xlsx` and page 2 of `research-designs.pdf`.

</details>

Run the same demo locally with `any2llm demo --lang en --no-open`.
