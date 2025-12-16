import React from "react"
import { Menu, PlusCircle, Sparkles } from "lucide-react"
import GhostIconButton from "./GhostIconButton"

export default function Header({ createNewChat, sidebarCollapsed, setSidebarOpen, vistaStatus }) {
  return (
    <header className="sticky top-0 z-30 hidden glass-medium px-4 py-3 md:flex md:items-center md:justify-between">
      <div className="flex items-center gap-3">
        {sidebarCollapsed && (
          <button
            onClick={() => setSidebarOpen(true)}
            className="glass-button p-2 text-muted-foreground hover:text-foreground transition-colors"
            aria-label="Toggle Sidebar"
          >
            <Menu className="h-4 w-4" />
          </button>
        )}
        
        <div className="flex items-center gap-3">
          {/* Logo with glass effect */}
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-primary to-accent">
            <Sparkles className="h-4 w-4 text-primary-foreground" />
          </div>
          
          <div className="flex items-center gap-2 text-sm font-semibold tracking-tight text-foreground">
            VISTA Assistant
            
            {/* VISTA Status Indicator with glass effect */}
            {vistaStatus && (
              <span className={`ml-2 inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ${
                vistaStatus === "online" 
                  ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300" 
                  : vistaStatus === "offline"
                  ? "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300"
                  : "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-300"
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
      </div>

      {/* New Chat Button with glass effect */}
      <button
        onClick={createNewChat}
        className="glass-shine glass-button flex items-center gap-2 px-4 py-2 text-sm font-medium bg-primary text-primary-foreground hover:bg-primary/90 transition-all hover:scale-105"
        aria-label="New Chat"
      >
        <PlusCircle className="h-4 w-4" />
        <span className="hidden sm:inline">New Chat</span>
      </button>
    </header>
  )
}