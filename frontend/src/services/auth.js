const TOKEN_KEY = "paper_reader_token";
const USER_KEY = "paper_reader_user";

export function getToken() {
  return localStorage.getItem(TOKEN_KEY) || "";
}

export function setAuth(token, user) {
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(USER_KEY, JSON.stringify(user || {}));
}

export function clearAuth() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

export function getUser() {
  const raw = localStorage.getItem(USER_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

export function isAuthed() {
  const token = getToken();
  if (!token) return false;

  const exp = _readJwtExp(token);
  if (typeof exp === "number") {
    const nowSec = Math.floor(Date.now() / 1000);
    if (exp <= nowSec) {
      clearAuth();
      return false;
    }
  }
  return true;
}

function _readJwtExp(token) {
  try {
    const parts = token.split(".");
    if (parts.length < 2) return null;
    const payloadBase64 = parts[1].replace(/-/g, "+").replace(/_/g, "/");
    const payloadText = decodeURIComponent(
      atob(payloadBase64)
        .split("")
        .map((char) => `%${char.charCodeAt(0).toString(16).padStart(2, "0")}`)
        .join("")
    );
    const payload = JSON.parse(payloadText);
    return Number.isFinite(payload?.exp) ? payload.exp : null;
  } catch {
    return null;
  }
}
