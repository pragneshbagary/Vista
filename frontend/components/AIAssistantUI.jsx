"use client"

import React, { useEffect, useRef, useState } from "react"
import Header from "./Header"
import ChatPane from "./ChatPane"
import ThemeToggle from "./ThemeToggle"

// VISTA API Configuration
const VISTA_API_URL = process.env.NEXT_PUBLIC_VISTA_API_URL || "http://localhost:8000"

export default function AIAssistantUI() {
  const [theme, setTheme] = useState(() => {
    const saved = typeof window !== "undefined" && localStorage.getItem("theme")
    if (saved) return saved
    if (typeof window !== "undefined" && window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches)
      return "dark"
    return "light"
  })

  const [isAnimating, setIsAnimating] = useState(false)

  // Random avatar selection for user
  const [userAvatar] = useState(() => {
    if (typeof window === "undefined") return null
    
    const avatars = [
      "001-bear.png", "002-tiger.png", "003-lion.png", "004-penguin.png",
      "005-koala.png", "006-dog.png", "007-giraffe.png", "008-panda.png",
      "009-rabbit.png", "010-pig.png", "011-dog.png", "012-zebra.png",
      "013-horse.png", "014-pig.png", "015-monkey.png", "016-monkey.png"
    ]
    return avatars[Math.floor(Math.random() * avatars.length)]
  })

  // LLM Selection
  const [showLLMSelector] = useState(true)
  const [selectedLLM, setSelectedLLM] = useState("gemini")

  // VISTA Backend Status
  const [vistaStatus, setVistaStatus] = useState("checking")

  // Check VISTA backend health
  useEffect(() => {
    const checkVistaHealth = async () => {
      try {
        const response = await fetch(`${VISTA_API_URL}/health`)
        if (response.ok) {
          setVistaStatus("online")
        } else {
          setVistaStatus("offline")
        }
      } catch (error) {
        console.error("VISTA health check failed:", error)
        setVistaStatus("offline")
      }
    }

    checkVistaHealth()
    const interval = setInterval(checkVistaHealth, 30000)
    return () => clearInterval(interval)
  }, [])

  useEffect(() => {
    try {
      setIsAnimating(true)
      
      setTimeout(() => {
        if (theme === "dark") document.documentElement.classList.add("dark")
        else document.documentElement.classList.remove("dark")
        document.documentElement.setAttribute("data-theme", theme)
        document.documentElement.style.colorScheme = theme
        localStorage.setItem("theme", theme)
      }, 300)
      
      setTimeout(() => {
        setIsAnimating(false)
      }, 600)
    } catch {}
  }, [theme])

  useEffect(() => {
    try {
      const media = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)")
      if (!media) return
      const listener = (e) => {
        const saved = localStorage.getItem("theme")
        if (!saved) setTheme(e.matches ? "dark" : "light")
      }
      media.addEventListener("change", listener)
      return () => media.removeEventListener("change", listener)
    } catch {}
  }, [])

  const [conversations, setConversations] = useState([])
  const [selectedId, setSelectedId] = useState(null)

  const [isThinking, setIsThinking] = useState(false)
  const [thinkingConvId, setThinkingConvId] = useState(null)

  const composerRef = useRef(null)

  // Create new chat function
  function createNewChat() {
    const id = Math.random().toString(36).slice(2)
    const item = {
      id,
      title: "New Chat",
      updatedAt: new Date().toISOString(),
      messageCount: 0,
      preview: "Ask me anything",
      messages: [],
    }
    setConversations((prev) => [item, ...prev])
    setSelectedId(id)
  }

  // Initialize with a default chat
  useEffect(() => {
    if (conversations.length === 0 && !selectedId) {
      createNewChat()
    }
  }, [])

  // Send message to VISTA API
  async function sendMessage(convId, content) {
    if (!content.trim()) return

    if (vistaStatus === "offline") {
      alert("VISTA backend is offline. Please start the API server.")
      return
    }

    const now = new Date().toISOString()
    const userMsg = { id: Math.random().toString(36).slice(2), role: "user", content, createdAt: now }

    setConversations((prev) =>
      prev.map((c) => {
        if (c.id !== convId) return c
        const msgs = [...(c.messages || []), userMsg]
        return {
          ...c,
          messages: msgs,
          updatedAt: now,
          messageCount: msgs.length,
          preview: content.slice(0, 80),
          title: msgs.length === 1 ? content.slice(0, 40) : c.title,
        }
      }),
    )

    setIsThinking(true)
    setThinkingConvId(convId)

    try {
      const response = await fetch(`${VISTA_API_URL}/api/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          message: content,
          llm_provider: selectedLLM,
        }),
      })

      if (!response.ok) {
        throw new Error(`VISTA API error: ${response.status}`)
      }

      const data = await response.json()
      const assistantContent = data.response || "No response received"

      setConversations((prev) =>
        prev.map((c) => {
          if (c.id !== convId) return c
          const asstMsg = {
            id: Math.random().toString(36).slice(2),
            role: "assistant",
            content: assistantContent,
            createdAt: new Date().toISOString(),
          }
          const msgs = [...(c.messages || []), asstMsg]
          return {
            ...c,
            messages: msgs,
            updatedAt: new Date().toISOString(),
            messageCount: msgs.length,
            preview: asstMsg.content.slice(0, 80),
          }
        }),
      )
    } catch (error) {
      console.error("Error calling VISTA API:", error)

      setConversations((prev) =>
        prev.map((c) => {
          if (c.id !== convId) return c
          const errorMsg = {
            id: Math.random().toString(36).slice(2),
            role: "assistant",
            content: `❌ Error: ${error.message}\n\nMake sure:\n1. VISTA backend is running (python api_server.py)\n2. Port 8000 is accessible\n3. Your .env file is configured correctly`,
            createdAt: new Date().toISOString(),
          }
          const msgs = [...(c.messages || []), errorMsg]
          return {
            ...c,
            messages: msgs,
            updatedAt: new Date().toISOString(),
            messageCount: msgs.length,
            preview: errorMsg.content.slice(0, 80),
          }
        }),
      )
    } finally {
      setIsThinking(false)
      setThinkingConvId(null)
    }
  }

  function editMessage(convId, messageId, newContent) {
    const now = new Date().toISOString()
    setConversations((prev) =>
      prev.map((c) => {
        if (c.id !== convId) return c
        const msgs = (c.messages || []).map((m) =>
          m.id === messageId ? { ...m, content: newContent, editedAt: now } : m,
        )
        return {
          ...c,
          messages: msgs,
          preview: msgs[msgs.length - 1]?.content?.slice(0, 80) || c.preview,
        }
      }),
    )
  }

  function resendMessage(convId, messageId) {
    const conv = conversations.find((c) => c.id === convId)
    const msg = conv?.messages?.find((m) => m.id === messageId)
    if (!msg) return
    sendMessage(convId, msg.content)
  }

  function pauseThinking() {
    setIsThinking(false)
    setThinkingConvId(null)
  }

  const selected = conversations.find((c) => c.id === selectedId) || null

  return (
    <div className={`h-screen w-full 
  bg-gradient-to-br 
  from-white via-gray-50 to-gray-100
  dark:from-black dark:via-gray-950 dark:to-gray-900
  text-foreground overflow-hidden ${isAnimating ? "theme-transition" : ""}`}>
      <div className="fixed inset-0 -z-10 
  bg-gradient-to-br 
  from-gray-200/20 via-white/10 to-gray-300/15
  dark:from-gray-800/20 dark:via-transparent dark:to-gray-800/15
  pointer-events-none" />
      
      {vistaStatus === "offline" && (
        <div className="fixed top-20 left-1/2 -translate-x-1/2 z-50 rounded-xl 
  border border-red-500/60
  bg-gradient-to-r from-red-100/80 via-red-50/70 to-rose-100/80
  dark:from-red-900/30 dark:via-red-800/20 dark:to-rose-900/30
  backdrop-blur-xl shadow-lg 
  px-6 py-3 text-center text-sm font-medium whitespace-nowrap 
  text-red-700 dark:text-red-300">
          ⚠️ VISTA Backend is offline. Please start the API server.
        </div>
      )}

      <div className="mx-auto flex h-[calc(100vh-0px)] max-w-[1400px]">
        <main className="relative flex min-w-0 flex-1 flex-col">
          <Header 
            createNewChat={createNewChat} 
            sidebarCollapsed={false}
            setSidebarOpen={() => {}}
            vistaStatus={vistaStatus}
            theme={theme}
            setTheme={setTheme}
            showLLMSelector={showLLMSelector}
            selectedLLM={selectedLLM}
            onLLMChange={setSelectedLLM}
          />
          <ChatPane
            ref={composerRef}
            conversation={selected}
            onSend={(content) => selected && sendMessage(selected.id, content)}
            onEditMessage={(messageId, newContent) => selected && editMessage(selected.id, messageId, newContent)}
            onResendMessage={(messageId) => selected && resendMessage(selected.id, messageId)}
            isThinking={isThinking && thinkingConvId === selected?.id}
            onPauseThinking={pauseThinking}
            theme={theme}
            userAvatar={userAvatar}
            selectedLLM={selectedLLM}
          />
        </main>
      </div>
    </div>
  )
}
