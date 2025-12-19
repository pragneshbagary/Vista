import React from "react"
import { Menu, PlusCircle, Sparkles } from "lucide-react"
import ThemeToggle from "./ThemeToggle"



export default function Header({ createNewChat, sidebarCollapsed, setSidebarOpen, vistaStatus, theme, setTheme }) {
  return (
    <header className="
  sticky top-0 z-30 hidden md:flex md:items-center md:justify-between
  px-6 py-4
  backdrop-blur-xl
  bg-white/60
  border-b border-blue-300/40
  shadow-sm
  dark:bg-slate-900/75
  dark:border-blue-500/40
  dark:shadow-black/40
">
 

      <div className="flex items-center gap-4">
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
          <div className="flex h-9 w-9 items-center justify-center rounded-xl
  bg-gradient-to-br from-blue-500/40 to-indigo-500/40
  backdrop-blur-md
  border border-blue-400/30
  shadow-sm">
            <Sparkles className="h-4 w-4 text-blue-600 dark:text-blue-400" />
          </div>
          
          <div className="flex items-center gap-3 text-sm font-semibold tracking-tight text-foreground">
            VISTA Assistant
            
            {/* VISTA Status Indicator with glass effect */}
            {vistaStatus && (
              <span className={`ml-1 inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium backdrop-blur-md shadow-sm ${
                vistaStatus === "online" 
                  ? "border-green-500/30 bg-green-500/10" 
                  : vistaStatus === "offline"
                  ? "border-red-500/30 bg-red-500/10"
                  : "border-yellow-500/30 bg-yellow-500/10"
              }`}>
                <span className={`h-1.5 w-1.5 rounded-full ${
                  vistaStatus === "online" ? "bg-green-500 animate-pulse" : 
                  vistaStatus === "offline" ? "bg-red-500" : 
                  "bg-yellow-500 animate-pulse"
                }`}></span>
                <span className={
                  vistaStatus === "online" 
                    ? "text-green-600 dark:text-green-400" 
                    : vistaStatus === "offline"
                    ? "text-red-600 dark:text-red-400"
                    : "text-yellow-600 dark:text-yellow-400"
                }>
                  {vistaStatus === "online" ? "Online" : vistaStatus === "offline" ? "Offline" : "Connecting..."}
                </span>
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Right side buttons */}
      <div className="flex items-center gap-3">
        {/* Theme Toggle */}
        <ThemeToggle theme={theme} setTheme={setTheme} />

        {/* New Chat Button with glass effect */}
        <button
          onClick={createNewChat}
          className="glass-shine group relative overflow-hidden rounded-lg flex items-center gap-2 px-4 py-2.5 text-sm font-medium bg-gradient-to-br from-blue-500 to-blue-600 text-white shadow-lg hover:shadow-xl transition-all hover:scale-105 active:scale-95 border border-blue-400/30"
          aria-label="New Chat"
        >
          <PlusCircle className="h-4 w-4" />
          <span className="hidden sm:inline">New Chat</span>
        </button>
      </div>
      {/* Bright rim */}
<div className="
  absolute inset-x-0 top-18.5 h-px
  bg-gradient-to-r
  from-transparent via-blue-600/80 to-transparent
  dark:via-blue-400/100
" />

{/* Soft glow */}
<div className="
  absolute inset-x-0 top-19 h-2
  bg-gradient-to-b
  from-blue-300/20 to-transparent
  dark:from-blue-500/20
  pointer-events-none
" />
    </header>
  )
}