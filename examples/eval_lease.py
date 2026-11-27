"""Measure `any2llm ask` on the example lease with a local model.

Run python examples/eval_lease.py [MODEL] from the repository root with Ollama (or another local server) running.
For each context size, it asks five questions, counts the expected facts found in the answers, and checks every
citation. The small context forces the model to read the lease in parts.
"""

import sys
import time
from pathlib import Path

from any2llm.ask import Asker
from any2llm.citations import FAILED, NO_QUOTE
from any2llm.llm import connect
from any2llm.sources import load

QUESTIONS = {
    "How much notice do I need to give to move out, and when do I get my deposit back?": ["three months", "30 days"],
    "Can I keep a dog, and who pays if it damages something?": ["written consent", "responsible"],
    "Can I sublet my apartment while I study abroad?": ["six months"],
    "What does the monthly service charge cover, and what is the late payment fee?": ["garden", "25 euros"],
    "When can the landlord enter my apartment, and how often are inspections?": ["48 hours", "twice a year"],
}


def main() -> None:
    model = sys.argv[1] if len(sys.argv) > 1 else None
    library = load(Path(__file__).resolve().parent / "lease", recursive=False)
    for context in (2048, 8192):
        backend = connect(model=model, context=context)
        facts = expected = failed = unquoted = citations = 0
        start = time.monotonic()
        for question, keys in QUESTIONS.items():
            asker = Asker(backend, library.documents, "en")
            answer = asker.answer(question, lambda _: None)
            report = asker.check(answer)
            found = [key for key in keys if key.casefold() in answer.casefold()]
            facts += len(found)
            expected += len(keys)
            failed += report.count(*FAILED)
            unquoted += report.count(NO_QUOTE)
            citations += len(report.checks)
            if len(found) < len(keys) or report.count(*FAILED):
                print(f"  missed: {question} found={found} statuses={[c.status for c in report.checks]}")
        elapsed = time.monotonic() - start
        print(f"{backend.model}, context {context}: facts {facts}/{expected}, citations {citations}, "
              f"failed {failed}, without quote {unquoted}, {elapsed:.0f} s for {len(QUESTIONS)} questions")


if __name__ == "__main__":
    main()
