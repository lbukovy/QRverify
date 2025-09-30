# QR Verifier – Server flow (URL → Upload → Match)

This version implements the *scan → open page → upload document → verify* flow.

## How it works
- The QR code encodes a **proper URL**, for example:
  ```
  https://qrverify.onrender.com/verify?id=INV-2025-0001&sig=<HMAC_HEX>
  ```
- On open, the server validates the HMAC (to ensure the link is authentic).
- The page asks the user to **upload the whole document** (PDF or image).
- The server computes **SHA-256** of the uploaded file and compares it with the canonical hash stored in `docs_db.json`.
- The result page shows PASS/FAIL and details.

> For robust matches, use the original PDF as the canonical source. Photo uploads will only match if the hash was computed from the exact same file (photos of a printout will *not* match). If you need photo-to-original matching, you will need OCR + structure checks. This basic version does *file hash* matching, which is reliable for PDF-to-PDF.

## Setup
1. Set environment variable on Render:
   - `QRV_HMAC_SECRET` = your secret for HMAC (must match the one you use to build the QR links).
2. Add canonical hashes to `docs_db.json` (see below).
3. Deploy.

## docs_db.json
Example:
```json
{
  "INV-2025-TEST": {
    "sha256": "PUT_SHA256_OF_ORIGINAL_PDF_HERE",
    "title": "Invoice 2025 TEST",
    "amount": "1234.56",
    "currency": "EUR"
  }
}
```

## Generate QR link
Use HMAC-SHA256 over the **doc_id** alone:
```
sig = hex( HMAC_SHA256(secret, doc_id) )
URL = https://qrverify.onrender.com/verify?id=<doc_id>&sig=<sig>
```
This produces a valid URL that mobile scanners open directly.

## Helper: compute hash of a PDF
```
python tools/compute_hash.py path/to/document.pdf
```
Copy the printed SHA-256 into `docs_db.json` under the desired `doc_id`.
