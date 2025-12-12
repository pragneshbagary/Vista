import React from "react"
import { Menu, PlusCircle } from "lucide-react"
import GhostIconButton from "./GhostIconButton"

export default function Header({ createNewChat, sidebarCollapsed, setSidebarOpen, vistaStatus }) {
  return (
    <header className="sticky top-0 z-30 hidden border-b border-zinc-200/60 bg-white/80 px-4 py-3 backdrop-blur md:flex md:items-center md:justify-between dark:border-zinc-800 dark:bg-zinc-900/70">
      <div className="flex items-center gap-3">
        {sidebarCollapsed && (
          <GhostIconButton label="Toggle Sidebar" onClick={() => setSidebarOpen(true)}>
            <Menu className="h-4 w-4" />
          </GhostIconButton>
        )}
        <div className="flex items-center gap-2 text-sm font-semibold tracking-tight">
          <span className="inline-flex h-4 w-4 items-center justify-center">✱</span>
          VISTA Assistant
          
          {/* VISTA Status Indicator */}
          {vistaStatus && (
            <span className={`ml-2 inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium ${
              vistaStatus === "online" 
                ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400" 
                : vistaStatus === "offline"
                ? "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400"
                : "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400"
            }`}>
              <span className={`h-1.5 w-1.5 rounded-full ${
                vistaStatus === "online" ? "bg-green-500 animate-pulse" : 
                vistaStatus === "offline" ? "bg-red-500" : 
                "bg-yellow-500 animate-pulse"
              }`}></span>
              {vistaStatus === "online" ? "Online" : vistaStatus === "offline" ? "Offline" : "Connecting..."}
            </span>
          )}
        </div>
      </div>

      <GhostIconButton label="New Chat" onClick={createNewChat}>
        <PlusCircle className="h-4 w-4" />
      </GhostIconButton>
    </header>
  )
}
