from fastapi import FastAPI, File, UploadFile, Form, HTTPException
"""Extract text from PDF bytes using PyMuPDF."""
try:
with fitz.open(stream=file_bytes, filetype='pdf') as doc:
pages = [p.get_text() for p in doc]
return "\n".join(pages)
except Exception as e:
raise




def chunk_text_by_chars(text: str, max_chars: int = 3000):
paragraphs = [p.strip() for p in text.split('\n') if p.strip()]
chunks = []
curr = ''
for p in paragraphs:
if len(curr) + len(p) + 1 > max_chars:
if curr:
chunks.append(curr.strip())
curr = p + '\n'
else:
curr += p + '\n'
if curr.strip():
chunks.append(curr.strip())
return chunks




async def get_offline_summarizer():
global _offline_summarizer
if _offline_summarizer is None:
device = 0 if torch.cuda.is_available() else -1
_offline_summarizer = pipeline('summarization', model=OFFLINE_MODEL_NAME, device=device)
return _offline_summarizer




@app.post('/api/summarize/offline')
async def summarize_offline(file: UploadFile = File(...), length: str = Form('medium')):
content = await file.read()
text = extract_text_from_pdf_bytes(content)
if not text.strip():
raise HTTPException(status_code=400, detail='No text extracted from PDF')


summarizer = await get_offline_summarizer()
chunks = chunk_text_by_chars(text, max_chars=3000)


# heuristic: set model max_length according to requested length
if length == 'short':
max_len = 100
elif length == 'medium':
max_len = 250
else:
max_len = 500


partials = []
for c in chunks:
out = summarizer(c, max_length=max_len, min_length=30, do_sample=False)
partials.append(out[0]['summary_text'])


if len(partials) > 1:
combined = "\n".join(partials)
# final pass
final = summarizer(combined, max_length=max_len*2, min_length=30, do_sample=False)[0]['summary_text']
else:
final = partials[0]


return JSONResponse({'summary': final})




@app.post('/api/summarize/online')
async def summarize_online(file: UploadFile = F