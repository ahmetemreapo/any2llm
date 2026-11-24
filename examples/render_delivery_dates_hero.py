"""Regenerate the README hero with Pillow, Liberation fonts, and Poppler.

Run python examples/render_delivery_dates_hero.py from the repository root.
"""

import subprocess
from io import BytesIO
from math import ceil
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

EXAMPLES = Path(__file__).resolve().parent
DISPLAY_SIZE = (800, 450)
SCALE = 2
DURATIONS = (2800, 2800, 3200, 4900)
BATCHES = ("batch_01_of_2.md", "batch_02_of_2.md")

BACKGROUND, PANEL, BORDER = "#0c131e", "#151f2d", "#29374a"
INK, ACCENT, WARNING = "#eff4fb", "#95e3d3", "#fcd788"


def pixels(*coordinates):
    return tuple(coordinate * SCALE for coordinate in coordinates)


def new_frame(label, title, label_font, title_font):
    image = Image.new("RGB", pixels(*DISPLAY_SIZE), BACKGROUND)
    draw = ImageDraw.Draw(image)
    draw.text(pixels(34, 24), label, font=label_font, fill=ACCENT)
    draw.text(pixels(34, 56), title, font=title_font, fill=INK)
    return image, draw


def panel(draw, x1, y1, x2, y2):
    draw.rounded_rectangle(pixels(x1, y1, x2, y2), 11 * SCALE, fill=PANEL, outline=BORDER, width=SCALE)


def file_labels(draw, y, names, mono):
    x = 34
    for name in names:
        width = ceil(mono.getlength(name) / SCALE) + 22
        panel(draw, x, y, x + width, y + 40)
        draw.text(pixels(x + 11, y + 10), name, font=mono, fill=INK)
        x += width + 10


def pdf_excerpt():
    pdf = EXAMPLES / "delivery-dates" / "supplier-offer.pdf"
    # Crop the shipment sentence at the target pixel density during PDF rasterization.
    result = subprocess.run(
        [
            "pdftoppm", "-f", "3", "-l", "3", "-r", str(200 * SCALE),
            "-x", str(45 * SCALE), "-y", str(64 * SCALE),
            "-W", str(575 * SCALE), "-H", str(53 * SCALE),
            "-png", "-singlefile", str(pdf),
        ],
        check=True,
        stdout=subprocess.PIPE,
        timeout=15,
    )
    with Image.open(BytesIO(result.stdout)) as crop:
        return crop.convert("RGB")


def main():
    # Render the font outlines directly at 2× on both axes. Missing fonts raise an error.
    label = ImageFont.truetype("LiberationSans-Bold.ttf", 20 * SCALE)
    heading = ImageFont.truetype("LiberationSans-Bold.ttf", 35 * SCALE)
    body = ImageFont.truetype("LiberationSans-Regular.ttf", 20 * SCALE)
    mono = ImageFont.truetype("LiberationMono-Regular.ttf", 16 * SCALE)
    terminal = "any2llm  /  Terminal"
    chat = "Delivery dates  /  Local chat transcript"

    one, draw = new_frame(terminal, "Pack a folder of delivery documents", label, heading)
    file_labels(draw, 127, ("delivery-schedule.xlsx", "meeting-notes.txt", "supplier-offer.pdf"), mono)
    panel(draw, 34, 190, 766, 365)
    draw.text(
        pixels(52, 211), "$ any2llm examples/delivery-dates -y --no-open --lang en \\",
        font=mono, fill=ACCENT,
    )
    draw.text(
        pixels(52, 241), '>   --max-tokens 150 --task "List shipment dates and cite PDF pages."',
        font=mono, fill=INK,
    )

    two, draw = new_frame(terminal, "Three documents, two attachments", label, heading)
    panel(draw, 34, 127, 766, 273)
    draw.multiline_text(
        pixels(52, 151), "Check the original PDF (supplier-offer.pdf, page(s) 2).\nNo text could be read.",
        font=mono, fill=WARNING, spacing=7 * SCALE,
    )
    draw.text(pixels(52, 222), "examples/delivery-dates/_llm_pack/", font=mono, fill=INK)
    file_labels(draw, 303, (*BATCHES, "PROMPT.txt"), mono)

    three, draw = new_frame(chat, "Ask for dates and PDF page numbers", label, heading)
    panel(draw, 34, 127, 766, 290)
    draw.text(pixels(52, 144), "You  •  Question", font=label, fill=ACCENT)
    draw.multiline_text(
        pixels(52, 179),
        "Copy the two shipment dates from supplier-offer.pdf, with the page\n"
        "number from each <page> tag. Format: Shipment — date\n"
        "(supplier-offer.pdf, page N).",
        font=body, fill=INK, spacing=6 * SCALE,
    )
    file_labels(draw, 320, BATCHES, mono)

    four, draw = new_frame(chat, "Check the cited page", label, heading)
    panel(draw, 34, 120, 766, 281)
    draw.text(pixels(52, 135), "Qwen2.5 0.5B Instruct", font=label, fill=ACCENT)
    draw.multiline_text(
        pixels(52, 169),
        "Shipment — 2027-03-12 (supplier-offer.pdf, page 1)\n"
        "Shipment — 2027-03-26 (supplier-offer.pdf, page 3)",
        font=body, fill=INK, spacing=6 * SCALE,
    )
    panel(draw, 34, 300, 766, 422)
    draw.text(
        pixels(52, 313), "supplier-offer.pdf  •  Page 3 of 3  •  Source excerpt", font=label, fill=INK,
    )
    four.paste(pdf_excerpt(), pixels(52, 351))

    first, *rest = (frame.quantize(colors=128) for frame in (one, two, three, four))
    first.save(
        EXAMPLES / "delivery-dates-chat-demo.gif",
        save_all=True, append_images=rest, duration=DURATIONS, loop=0, optimize=True,
    )


if __name__ == "__main__":
    main()
