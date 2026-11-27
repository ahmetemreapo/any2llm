"""Render the README terminal demo for ask and check with Pillow and DejaVu Sans Mono.

Run python examples/render_ask_demo.py from the repository root. The text on screen is copied from real runs:
`any2llm ask` with qwen3:4b-instruct on Ollama (RTX 4050 laptop GPU, about 5 seconds), and `any2llm check`
on examples/lease-chat-answer.md, an example answer with two planted mistakes.
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

EXAMPLES = Path(__file__).resolve().parent
WIDTH, HEIGHT = 900, 520
SCALE = 2
FONT_SIZE = 16
LINE = 24
MARGIN_X, TOP = 24, 54
WRAP = 84

BACKGROUND, BAR, BORDER = "#0d1117", "#161b22", "#30363d"
INK, DIM, PROMPT, GREEN, RED, YELLOW, CYAN = (
    "#e6edf3", "#8b949e", "#7ee787", "#3fb950", "#f85149", "#d29922", "#79c0ff",
)

ASK_COMMAND = (
    'any2llm ask examples/lease "How much notice do I need to give to move out, and when do I get my deposit back?"'
)
ASK_STATUS = [
    (DIM, "any2llm · qwen3:4b-instruct · Ollama · 8,192 token context"),
    (DIM, "… Read 2 documents"),
    (DIM, "… Asking the model…"),
]
ASK_ANSWER = (
    "I need to give three months' written notice to move out: \"The Tenant may end the lease with three months' "
    "written notice, ending on the last day of a calendar month\" [lease-agreement.pdf, p. 14].\n\n"
    "I get my deposit back within 30 days after returning the keys: \"The deposit is refunded within 30 days after "
    "the Tenant returns the keys\" [lease-agreement.pdf, p. 6]."
)
ASK_REPORT = [
    (GREEN, "✓  2 of 2 citations match the original sources"),
    (GREEN, "  ✓ [lease-agreement.pdf, p. 14] quote found where cited"),
    (GREEN, "  ✓ [lease-agreement.pdf, p. 6] quote found where cited"),
]
CHECK_CAPTION = "# An answer from any chat app, copied to a file (or just to the clipboard)"
CHECK_COMMAND = "any2llm check examples/lease examples/lease-chat-answer.md"
CHECK_REPORT = [
    (RED, "✗  2 of 4 citations match the original sources"),
    (RED, "  ✗ [lease-agreement.pdf, p. 12] quote is on page 14, not the cited page"),
    (DIM, "      \"the Tenant may end the lease with three months' written notice\""),
    (RED, "  ✗ [lease-agreement.pdf, p. 6] quote not found in this source"),
    (DIM, "      \"The deposit is refunded within 14 days after the Tenant returns the keys\""),
    (GREEN, "  ✓ [lease-agreement.pdf, p. 8] quote found where cited"),
    (GREEN, "  ✓ [house-rules.txt] quote found where cited"),
    (RED, "Open the original pages before you rely on the parts marked ✗."),
]


def wrap(text: str, width: int = WRAP) -> list[str]:
    lines = []
    for paragraph in text.split("\n"):
        indent = paragraph[: len(paragraph) - len(paragraph.lstrip(" "))]
        line = indent
        for word in paragraph.strip(" ").split(" "):
            if line.strip() and len(line) + 1 + len(word) > width:
                lines.append(line)
                line = indent + "  " + word if indent else word
            else:
                line = f"{line} {word}" if line.strip() else line + word
        lines.append(line)
    return lines


class Screen:
    def __init__(self, title: str):
        self.title = title
        self.rows: list[tuple[str, str]] = []
        self.font = ImageFont.truetype("DejaVuSansMono.ttf", FONT_SIZE * SCALE)
        self.bold = ImageFont.truetype("DejaVuSansMono-Bold.ttf", FONT_SIZE * SCALE)

    def add(self, color: str, text: str) -> None:
        for line in wrap(text):
            self.rows.append((color, line))

    def command(self, text: str, typed: int | None = None) -> None:
        shown = text if typed is None else text[:typed]
        lines = wrap("$ " + shown)
        for line in lines:
            self.rows.append((PROMPT, line))

    def frame(self, *, cursor: bool = False) -> Image.Image:
        image = Image.new("RGB", (WIDTH * SCALE, HEIGHT * SCALE), BACKGROUND)
        draw = ImageDraw.Draw(image)
        draw.rectangle((0, 0, WIDTH * SCALE, 36 * SCALE), fill=BAR)
        draw.line((0, 36 * SCALE, WIDTH * SCALE, 36 * SCALE), fill=BORDER, width=SCALE)
        for index, color in enumerate(("#ff5f56", "#ffbd2e", "#27c93f")):
            x = (20 + index * 20) * SCALE
            draw.ellipse((x - 6 * SCALE, 12 * SCALE, x + 6 * SCALE, 24 * SCALE), fill=color)
        title_width = draw.textlength(self.title, font=self.font)
        draw.text(((WIDTH * SCALE - title_width) / 2, 9 * SCALE), self.title, font=self.font, fill=DIM)
        visible = self.rows[-((HEIGHT - TOP - 10) // LINE):]
        for row, (color, text) in enumerate(visible):
            font = self.bold if color in (GREEN, RED) and not text.startswith("  ") else self.font
            draw.text((MARGIN_X * SCALE, (TOP + row * LINE) * SCALE), text, font=font, fill=color)
        if cursor and visible:
            last = visible[-1][1]
            x = MARGIN_X * SCALE + draw.textlength(last, font=self.font) + 3 * SCALE
            y = (TOP + (len(visible) - 1) * LINE) * SCALE
            draw.rectangle((x, y + 2 * SCALE, x + 9 * SCALE, y + 19 * SCALE), fill=INK)
        return image.resize((WIDTH, HEIGHT), Image.LANCZOS)


def typing(screen: Screen, command: str, frames: list, durations: list, steps: int = 12) -> None:
    base = list(screen.rows)
    for step in range(1, steps + 1):
        screen.rows = list(base)
        screen.command(command, typed=round(len(command) * step / steps))
        frames.append(screen.frame(cursor=True))
        durations.append(55)
    durations[-1] = 500


def main() -> None:
    frames: list[Image.Image] = []
    durations: list[int] = []

    ask = Screen("any2llm ask  ·  local model, nothing leaves the laptop")
    typing(ask, ASK_COMMAND, frames, durations)
    for color, text in ASK_STATUS:
        ask.add(color, text)
        frames.append(ask.frame())
        durations.append(450)
    ask.add(INK, "")
    base = list(ask.rows)
    words = ASK_ANSWER.split(" ")
    for step in range(1, 9):
        ask.rows = list(base)
        ask.add(INK, " ".join(words[: round(len(words) * step / 8)]))
        frames.append(ask.frame())
        durations.append(160)
    ask.add(INK, "")
    for color, text in ASK_REPORT:
        ask.add(color, text)
        frames.append(ask.frame())
        durations.append(350)
    durations[-1] = 3800

    check = Screen("any2llm check  ·  verify any chatbot's citations")
    check.add(DIM, CHECK_CAPTION)
    typing(check, CHECK_COMMAND, frames, durations, steps=8)
    check.add(INK, "")
    for color, text in CHECK_REPORT:
        check.add(color, text)
        frames.append(check.frame())
        durations.append(300)
    durations[-1] = 5200

    palette = [frame.quantize(colors=64, method=Image.Quantize.MEDIANCUT) for frame in frames]
    palette[0].save(
        EXAMPLES / "ask-and-check-demo.gif", save_all=True, append_images=palette[1:],
        duration=durations, loop=0, optimize=True,
    )


if __name__ == "__main__":
    main()
