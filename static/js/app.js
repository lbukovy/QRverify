// static/js/app.js
// QR Verifier main logic

const readerDivId = "reader";
let html5QrCode = null;
let currentCameraId = null;

const $ = (sel) => document.querySelector(sel);

function setStatus(success, text) {
  const pill = $("#statusPill");
  pill.classList.remove("success", "fail");
  pill.classList.add(success ? "success" : "fail");
  pill.textContent = text;
}

function showResultSection() {
  $("#resultSection").classList.remove("hidden");
}

function renderMatchedRules(decoded) {
  const ul = $("#matchedRules");
  ul.innerHTML = "";
  let count = 0;
  for (const rule of (window.QRV_CONFIG?.rules || [])) {
    if (rule.pattern.test(decoded)) {
      const li = document.createElement("li");
      li.textContent = rule.name;
      ul.appendChild(li);
      count++;
    }
  }
  if (count === 0) {
    const li = document.createElement("li");
    li.textContent = "No rule matched.";
    ul.appendChild(li);
  }
}

function parseHmacPayload(decoded) {
  const idx = decoded.lastIndexOf("|hmac=");
  if (idx === -1) return null;
  const payload = decoded.slice(0, idx);
  const hmacHex = decoded.slice(idx + 6).trim();
  return { payload, hmacHex };
}

async function verifyHmac(decoded) {
  const out = $("#cryptoResult");
  out.innerHTML = "";
  const secret = (window.QRV_CONFIG?.hmacSecret || "").trim();
  const parsed = parseHmacPayload(decoded);
  if (!parsed) {
    out.textContent = "No HMAC string found. Skipped.";
    return null;
  }
  if (!secret) {
    out.textContent = "HMAC secret not configured in config.js.";
    return null;
  }
  try {
    const enc = new TextEncoder();
    const keyData = enc.encode(secret);
    const key = await crypto.subtle.importKey(
      "raw", keyData, { name: "HMAC", hash: "SHA-256" }, false, ["sign", "verify"]
    );
    const sig = await crypto.subtle.sign("HMAC", key, enc.encode(parsed.payload));
    const computedHex = Array.from(new Uint8Array(sig)).map(b => b.toString(16).padStart(2, "0")).join("");
    const ok = computedHex.toLowerCase() === parsed.hmacHex.toLowerCase();
    out.innerHTML = ok
      ? `<span class="px-2 py-1 rounded bg-green-100 text-green-700">HMAC OK</span>`
      : `<span class="px-2 py-1 rounded bg-red-100 text-red-700">HMAC FAIL</span><div class="mt-1 text-xs break-all">Expected: ${parsed.hmacHex}<br>Got: ${computedHex}</div>`;
    return ok;
  } catch (e) {
    out.textContent = "Error verifying HMAC: " + e.message;
    return false;
  }
}

function handleDecoded(decodedText) {
  $("#decodedText").value = decodedText;
  renderMatchedRules(decodedText);
  verifyHmac(decodedText).then(() => {});
  const anyMatch = (window.QRV_CONFIG?.rules || []).some(r => r.pattern.test(decodedText));
  setStatus(anyMatch, anyMatch ? "Payload matches rules" : "No rules matched");
  showResultSection();
}

async function startScanner() {
  if (!html5QrCode) {
    html5QrCode = new Html5Qrcode(readerDivId);
  }
  const cameraId = currentCameraId;
  const config = { fps: 10, qrbox: 250 };
  await html5QrCode.start(
    cameraId || { facingMode: "environment" },
    config,
    (decodedText) => {
      stopScanner();
      handleDecoded(decodedText);
    },
    (errorMessage) => {}
  );
}

async function stopScanner() {
  if (html5QrCode && html5QrCode._isScanning) {
    await html5QrCode.stop();
  }
}

async function listCameras() {
  const cameras = await Html5Qrcode.getCameras();
  const sel = $("#cameraSelect");
  sel.innerHTML = "";
  cameras.forEach(cam => {
    const opt = document.createElement("option");
    opt.value = cam.id;
    opt.textContent = cam.label || cam.id;
    sel.appendChild(opt);
  });
  if (cameras[0]) currentCameraId = cameras[0].id;
}

function bindUI() {
  $("#btnStart").addEventListener("click", startScanner);
  $("#btnStop").addEventListener("click", stopScanner);
  $("#cameraSelect").addEventListener("change", (e) => {
    currentCameraId = e.target.value;
  });
  $("#fileInput").addEventListener("change", async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const tmp = new Html5Qrcode("reader");
    try {
      const result = await tmp.scanFile(file, true);
      handleDecoded(result);
    } catch (err) {
      setStatus(false, "Failed to decode image.");
      showResultSection();
    } finally {
      tmp.clear();
    }
  });
}

document.addEventListener("DOMContentLoaded", async () => {
  bindUI();
  try { await listCameras(); } catch (_) {}
});
