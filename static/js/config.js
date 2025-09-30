// Konfigurácia verifikácie QR Verifier

window.QRV_CONFIG = {
  rules: [
    { name: "URL (http/https)", pattern: /^(https?:\/\/)[\w\-\.:@]+(\/.*)?$/i },
    { name: "UUID v4", pattern: /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i },
    { name: "E-mail", pattern: /^[^\s@]+@[^\s@]+\.[^\s@]+$/ },
    { name: "IBAN (základná kontrola)", pattern: /^[A-Z]{2}\d{2}[A-Z0-9]{1,30}$/ },
    { name: "Interné dokladové ID (INV-YYYY-XXXX)", pattern: /^INV-\d{4}-\d{4}$/ },
    { name: "Klientské ID (alfanumerické, 6–12 znakov)", pattern: /^[A-Z0-9]{6,12}$/ }
  ],

  // Tajný kľúč pre HMAC-SHA256
  hmacSecret: "saxo-verify-9f4c2b7a1e84"
};
