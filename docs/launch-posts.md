# Launch post drafts

Every number below comes from a real run on the example files. Post the GIF (`examples/ask-and-check-demo.gif`) or a short screen recording with each post, and answer comments for the first few hours. Be the first to point out the limits: the check confirms that quotes exist on the cited page. It doesn't judge reasoning.

## r/LocalLLaMA

**Title:** I made my local model's citations checkable: every quote is matched against the actual PDF page

**Body:**

Small local models are fine at answering questions about my documents. What I couldn't trust was "see page 12". So I added two commands to any2llm, my open-source document packer:

- `any2llm ask ./docs "question"` finds Ollama, LM Studio, or llama.cpp on localhost. It sends the model the full text with physical page tags instead of RAG chunks, and it sets `num_ctx` for each request, because Ollama defaults to 4k context on GPUs under 24 GB. Folders bigger than the context are read in parts, and the quotes from each part are combined.
- After the answer, every `"quote" [file.pdf, p. N]` is checked against the extracted page. You get "found", "on page 14, not page 12", or "not found". A changed number never counts as a near match.

On a laptop RTX 4050 with `qwen3:4b-instruct`, questions about a 17-page lease take about 5 to 7 seconds. The repo includes the eval (`examples/eval_lease.py`): five questions with 9 expected facts, run at 8k context and at 2k, where the model has to read the lease in three parts. In three runs of each, all 9 facts were in the answers and all 9 citations passed. One trick that mattered: quotes the model collects from each part are matched back to the full source sentence before the final answer, so a 4B model can't drift away from the text between steps.

`any2llm check ./docs` also works on answers from any other chat: copy the answer and run it.

It reads PDF (with optional OCR), docx, xlsx (including formulas), pptx, EPUB, HTML, and code, and the terminal speaks 11 languages. MIT licensed, and nothing leaves your machine.

Repo: https://github.com/ahmetemreapo/any2llm

I'd especially like to hear which models stick to the quote format and which ones drift. If you have a nasty PDF where extraction breaks, I'd like to see that too.

## r/ClaudeAI (or r/ClaudeCode)

**Title:** A Claude Code plugin that makes Claude check its own PDF citations before it answers

**Body:**

`/plugin install any2llm --marketplace ahmetemreapo/any2llm`

Ask something like "what does the lease in ./lease say about pets and moving out?" The skill extracts the folder with any2llm (PDF pages keep their physical numbers, and Word, Excel, and EPUB work too). Claude drafts the answer with quotes like `"exact words" [file.pdf, p. 8]`, then runs `any2llm check` on the draft. Anything on the wrong page or not in the file gets fixed before you see the answer.

In my test run on a 17-page lease, Claude wrote 10 citations and all 10 passed. The point is that you don't have to take that on faith: the check runs on every answer, and a failed quote is shown instead of hidden.

It's also an MCP server (`list_documents`, `read_documents`, `check_citations`) for Claude Desktop and Cursor.

Repo: https://github.com/ahmetemreapo/any2llm. Feedback on the skill wording is very welcome.

## X / Twitter thread

1/ AI chats love to say "see page 12". Is it actually on page 12? I built a check for that. 🧵

any2llm reads your PDFs, Word, and Excel files locally, answers with a local model, and checks every quote against the original page. [GIF]

2/ `any2llm ask ./docs "question"`
→ finds Ollama, LM Studio, or llama.cpp by itself
→ sends the full text with real page numbers (no RAG chunking)
→ sets the context size, because Ollama defaults to 4k on most GPUs
→ about 5 to 7 s on a laptop RTX 4050 with qwen3:4b

3/ `any2llm check ./docs`
Copy an answer from ChatGPT, Claude, or Gemini and run it. Each quote comes back as:
✓ found where cited
✗ on page 14, not page 12
✗ not in your files
A changed number never passes.

4/ For Claude Code: `/plugin install any2llm --marketplace ahmetemreapo/any2llm`
Claude checks its own citations before it answers. In my test, 10 of 10 passed.

5/ Open source (MIT), runs locally, 11 languages, and handles PDF with OCR, docx, xlsx formulas, pptx, and EPUB.
https://github.com/ahmetemreapo/any2llm

## Show HN

**Title:** Show HN: any2llm – check that an AI's quotes are really on the PDF page it cites

**Body:**

any2llm started as a tool that packs a folder of PDFs and Office files into Markdown for a chat, keeping physical page numbers. People still had to check every "see page N" by hand, so I added a checker. It parses citations in the form "quote" [file, p. N], normalizes the text (hyphenation, quote marks, table pipes), and reports each one as found, on another page (with the right page), in another file, or not found. Near matches are allowed for small wording changes but never for changed numbers.

`any2llm ask` runs the whole loop against a local model (Ollama, LM Studio, or llama.cpp). It reads large folders in parts that fit the model's real context instead of retrieving chunks. `any2llm check` works on answers from any chat. There's also an MCP server and a Claude Code plugin that checks its own drafts.

I'd value feedback on the matching rules and on PDFs where extraction falls apart.

https://github.com/ahmetemreapo/any2llm

## Türkçe: r/CodingTR, Türk geliştirici Discord'ları ve X

**Başlık:** Yapay zekânın "12. sayfada" dediği alıntı gerçekten 12. sayfada mı? Kontrol eden açık kaynak bir araç yaptım

**Metin:**

Bir öğrenci olarak ders PDF'lerimi ve sözleşme gibi belgeleri yapay zekâya soruyorum. Cevaplar çoğu zaman iyi, ama "bkz. s. 12" dediği yer bazen 14. sayfada çıkıyor, bazen de alıntıdaki sayı belgede hiç yok. any2llm'e bunun için iki komut ekledim:

- `any2llm ask ./belgeler "soru"`: Ollama, LM Studio veya llama.cpp'yi kendisi bulur. Metnin tamamını gerçek sayfa numaralarıyla modele verir. Belge bağlama sığmıyorsa bölüm bölüm okuyup birleştirir. Laptop RTX 4050 ve qwen3:4b-instruct ile 17 sayfalık bir sözleşmeye soru başına 5 ila 7 saniye.
- `any2llm check ./belgeler`: ChatGPT, Claude veya Gemini'nin cevabını kopyalayıp çalıştırıyorsun. Her alıntı için "doğru yerde", "12. değil 14. sayfada" ya da "dosyalarında yok" diyor. Sayısı değişmiş bir alıntı asla geçmiyor.

PDF (OCR dahil), Word, Excel (formüller dahil), PowerPoint ve EPUB okuyor. Terminal Türkçe dahil 11 dilde, her şey bilgisayarında çalışıyor, lisansı MIT.

https://github.com/ahmetemreapo/any2llm

İlk açık kaynak projem. Bozuk çıkan bir PDF'in ya da formata uymayan bir modelin olursa issue açarsan çok sevinirim.
