import React from "react";

export default function GhostIconButton({ label, children }) {
  return (
    <button
      className="hidden md:inline-flex rounded-full glass-button p-2 text-muted-foreground hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      aria-label={label}
      title={label}
    >
      {children}
    </button>
  );
}
