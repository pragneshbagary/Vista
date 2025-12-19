import React from "react";
import { Sun, Moon } from "lucide-react";

export default function ThemeToggle({ theme, setTheme }) {
  return (
    <button
      className="inline-flex items-center gap-2 rounded-lg border border-blue-200/40 bg-white/40 backdrop-blur-md px-3 py-2.5 text-sm text-foreground hover:bg-white/60 hover:border-blue-300/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-400/40 transition-all dark:border-white/10 dark:bg-white/5 dark:hover:bg-white/10 dark:focus-visible:ring-blue-500/40"
      onClick={() => setTheme((t) => (t === "dark" ? "light" : "dark"))}
      aria-label="Toggle theme"
      title="Toggle theme"
    >
      {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
      <span className="hidden sm:inline text-sm font-medium">{theme === "dark" ? "Light" : "Dark"}</span>
    </button>
  );
}
