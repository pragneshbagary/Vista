import React from "react"
import { Menu, PlusCircle, Sparkles } from "lucide-react"
import ThemeToggle from "./ThemeToggle"
import LLMSelector from "./LLMSelector"



export default function Header({ createNewChat, sidebarCollapsed, setSidebarOpen, vistaStatus, theme, setTheme, showLLMSelector, selectedLLM, onLLMChange }) {
  return (
    <header className="sticky top-0 z-30 hidden md:flex md:items-center md:justify-between
  mx-4 mt-4 mb-4 px-6 py-4
  rounded-2xl
  shadow-lg
  relative
  bg-gray-200/60 dark:bg-white/8
  border border-gray-300/40 dark:border-white/20
  backdrop-blur-xl
">
      {/* Glow rim effect - bright white edge at top */}
      <div className="absolute inset-x-0 top-0 h-px
  bg-gradient-to-r from-transparent via-gray-400/60 to-transparent
  dark:via-white/30
  rounded-t-2xl" />

      {/* Soft glow effect - subtle white glow below rim */}
      <div className="absolute inset-x-0 top-px h-2
  bg-gradient-to-b from-gray-300/30 to-transparent
  dark:from-white/10
  pointer-events-none
  rounded-t-2xl" />

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
          {/* Logo */}
          <img src="/vista_logo.svg" alt="VISTA Logo" className="h-8 w-8 object-contain" />
          
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
        {/* LLM Selector */}
        <LLMSelector 
          selectedLLM={selectedLLM} 
          onLLMChange={onLLMChange}
          visible={showLLMSelector}
        />

        {/* Theme Toggle */}
        <ThemeToggle theme={theme} setTheme={setTheme} />

        {/* New Chat Button with glass effect */}
        <button
          onClick={createNewChat}
          className="glass-shine group relative overflow-hidden rounded-lg flex items-center gap-2 px-4 py-2.5 text-sm font-medium bg-gradient-to-br from-gray-600 to-gray-700 text-white shadow-lg hover:shadow-xl transition-all hover:scale-105 active:scale-95 border border-gray-500/30"
          aria-label="New Chat"
        >
          <PlusCircle className="h-4 w-4" />
          <span className="hidden sm:inline">New Chat</span>
        </button>
      </div>
    </header>
  )
}