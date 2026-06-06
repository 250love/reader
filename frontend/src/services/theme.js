export const THEMES = {
  LIGHT: "light",
  DARK: "dark"
};

const THEME_STORAGE_KEY = "theme";
export const THEME_CHANGE_EVENT = "paper-reader-theme-change";

export function normalizeTheme(theme) {
  return theme === THEMES.DARK ? THEMES.DARK : THEMES.LIGHT;
}

export function getStoredTheme() {
  if (typeof window === "undefined") {
    return THEMES.LIGHT;
  }
  return normalizeTheme(window.localStorage.getItem(THEME_STORAGE_KEY));
}

export function applyTheme(theme) {
  if (typeof document === "undefined") {
    return;
  }
  document.documentElement.dataset.theme = normalizeTheme(theme);
}

export function setStoredTheme(theme) {
  const safeTheme = normalizeTheme(theme);
  if (typeof window !== "undefined") {
    window.localStorage.setItem(THEME_STORAGE_KEY, safeTheme);
    window.dispatchEvent(new CustomEvent(THEME_CHANGE_EVENT, { detail: { theme: safeTheme } }));
  }
  applyTheme(safeTheme);
  return safeTheme;
}

export function initTheme() {
  const theme = getStoredTheme();
  applyTheme(theme);
  return theme;
}
