import React from "react"
import { Menu, PlusCircle, Sparkles } from "lucide-react"
import GhostIconButton from "./GhostIconButton"

export default function Header({ createNewChat, sidebarCollapsed, setSidebarOpen, vistaStatus }) {
  return (
    <header className="sticky top-0 z-30 hidden border-b border-white/10 glass-medium backdrop-blur-xl px-4 py-3 md:flex md:items-center md:justify-between shadow-lg">
      <div className="flex items-center gap-3">
        {sidebarCollapsed && (
          <button
            onClick={() => setSidebarOpen(true)}
            className="glass-button p-2 text-white/70 hover:text-white transition-colors"
            aria-label="Toggle Sidebar"
          >
            <Menu className="h-4 w-4" />
          </button>
        )}
        
        <div className="flex items-center gap-3">
          {/* Logo with glass effect */}
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-purple-500 to-pink-500 shadow-lg">
            <Sparkles className="h-4 w-4 text-white" />
          </div>
          
          <div className="flex items-center gap-2 text-sm font-semibold tracking-tight text-white">
            VISTA Assistant
            
            {/* VISTA Status Indicator with glass effect */}
            {vistaStatus && (
              <span className={`ml-2 inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium glass-light ${
                vistaStatus === "online" 
                  ? "text-green-300" 
                  : vistaStatus === "offline"
                  ? "text-red-300"
                  : "text-yellow-300"
              }`}>
                <span className={`h-1.5 w-1.5 rounded-full ${
                  vistaStatus === "online" ? "bg-green-400 animate-pulse shadow-lg shadow-green-400/50" : 
                  vistaStatus === "offline" ? "bg-red-400 shadow-lg shadow-red-400/50" : 
                  "bg-yellow-400 animate-pulse shadow-lg shadow-yellow-400/50"
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
        className="glass-shine glass-button flex items-center gap-2 px-4 py-2 text-sm font-medium text-white hover:text-white transition-all hover:scale-105"
        aria-label="New Chat"
      >
        <PlusCircle className="h-4 w-4" />
        <span className="hidden sm:inline">New Chat</span>
      </button>
    </header>
  )
}