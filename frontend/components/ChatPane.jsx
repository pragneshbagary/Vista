import React, { useEffect, useRef, forwardRef, useImperativeHandle } from "react"
import { Bot, Sparkles } from "lucide-react"
import Message from "./Message"
import Composer from "./Composer"

// Add CSS for animations
const animationStyles = `
  @keyframes float {
    0%, 100% { transform: translateY(0px); }
    50% { transform: translateY(-15px); }
  }
  
  @keyframes subtle-glow {
    0%, 100% { filter: drop-shadow(0 0 15px rgba(59, 130, 246, 0.3)); }
    50% { filter: drop-shadow(0 0 25px rgba(59, 130, 246, 0.5)); }
  }
  
  .logo-float {
    animation: float 4s ease-in-out infinite;
  }
  
  .logo-glow {
    animation: subtle-glow 3s ease-in-out infinite;
  }
`

const ChatPane = forwardRef(({ 
  conversation, 
  onSend, 
  onEditMessage, 
  onResendMessage, 
  isThinking, 
  onPauseThinking,
  theme = "light",
  userAvatar,
  selectedLLM
}, ref) => {
  const messagesEndRef = useRef(null)
  const composerRef = useRef(null)

  // Inject animation styles
  useEffect(() => {
    const style = document.createElement('style')
    style.textContent = animationStyles
    document.head.appendChild(style)
    return () => document.head.removeChild(style)
  }, [])

  // Expose methods to parent component
  useImperativeHandle(ref, () => ({
    insertTemplate: (content) => {
      if (composerRef.current) {
        composerRef.current.insertTemplate(content)
      }
    }
  }))

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }

  useEffect(() => {
    scrollToBottom()
  }, [conversation?.messages, isThinking])

  if (!conversation) {
    return (
      <div className="relative flex h-full w-full flex-col overflow-hidden bg-gradient-to-br from-background via-background to-background">
        <div className="relative z-10 flex h-full items-center justify-center p-8">
          <div className="glass-card glass-shadow max-w-md space-y-8 p-12 text-center text-foreground">
            <div className="mx-auto flex h-20 w-20 items-center justify-center rounded-2xl bg-gradient-to-br from-primary/40 to-accent/40 backdrop-blur-md border border-white/20">
              <Sparkles className="h-10 w-10 text-primary" />
            </div>
            <div className="space-y-4">
              <h2 className="text-3xl font-bold tracking-tight bg-gradient-to-r from-foreground to-foreground/70 bg-clip-text text-transparent">
                VISTA
              </h2>
              <p className="text-sm text-muted-foreground leading-relaxed">
                Vector-Integrated Semantic Text Assistant. Ask me about my projects and experience.
              </p>
            </div>
            <div className="pt-4 space-y-3 text-xs text-muted-foreground">
              <p className="flex items-center justify-center gap-2">
                <span>💡</span>
                <span>Try asking about specific projects or technologies</span>
              </p>
              <p className="flex items-center justify-center gap-2">
                <span>⌨️</span>
                <span>Press <kbd className="px-2 py-1 glass-light rounded text-xs font-mono ml-1">Cmd/Ctrl + N</kbd> for a new chat</span>
              </p>
            </div>
          </div>
        </div>
      </div>
    )
  }

  const messages = conversation.messages || []

  return (
    <div className="relative flex h-full w-full flex-col overflow-hidden">
      {/* Background Logo - Blurred when conversation is active */}
      <div className={`absolute inset-0 flex items-center justify-center pointer-events-none transition-all duration-300 ${
        messages.length > 0 ? (theme === 'dark' ? 'opacity-30 blur-sm' : 'opacity-15 blur-sm') : 'opacity-0'
      }`}>
        <img 
          src="/vista_logo.png" 
          alt="VISTA Logo Background" 
          className="h-96 w-96 object-contain"
        />
      </div>
      
      {/* Messages area */}
      <div className="relative z-10 flex-1 overflow-y-auto px-6 py-8 pb-24 scrollbar-glass flex items-center justify-center">
        <div className="mx-auto max-w-3xl w-full">
          {messages.length === 0 ? (
            <div className="flex items-center justify-center">
              <img 
                src="/vista_logo.png" 
                alt="VISTA Logo" 
                className="h-80 w-80 object-contain drop-shadow-lg opacity-100 transition-all duration-300 logo-float logo-glow"
              />
            </div>
          ) : (
            <div className="space-y-6 pb-4">
              {messages.map((message) => (
                <Message
                  key={message.id}
                  message={message}
                  onEdit={onEditMessage}
                  onResend={onResendMessage}
                  userAvatar={userAvatar}
                />
              ))}
              
              {/* Thinking indicator */}
              {isThinking && (
                <div className="flex items-start gap-4">
                  <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-primary/40 to-accent/40 backdrop-blur-md border border-white/20">
                    <Bot className="h-5 w-5 text-primary" />
                  </div>
                  <div className="glass-card glass-shadow flex items-center gap-3 px-5 py-4">
                    <div className="flex gap-1.5">
                      <div className="h-2 w-2 animate-bounce rounded-full bg-primary [animation-delay:-0.3s]"></div>
                      <div className="h-2 w-2 animate-bounce rounded-full bg-primary [animation-delay:-0.15s]"></div>
                      <div className="h-2 w-2 animate-bounce rounded-full bg-primary"></div>
                    </div>
                    <span className="text-sm text-muted-foreground">Thinking...</span>
                    {onPauseThinking && (
                      <button
                        onClick={onPauseThinking}
                        className="ml-2 text-xs text-muted-foreground hover:text-foreground transition-colors"
                      >
                        Stop
                      </button>
                    )}
                  </div>
                </div>
              )}
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Composer area with glass effect */}
      <div className="relative z-10 flex-shrink-0 border-t border-gray-300/20 dark:border-white/10">
        {/* Glass rim */}
        
        <div className="mx-auto max-w-3xl px-6 py-4">
          {/* <div className="glass-card rounded-lg p-3 relative"> */}
            {/* Glow rim effect - bright white edge at top */}
            <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-gray-400/60 to-transparent dark:via-white/30 rounded-t-lg" />

            {/* Soft glow effect - subtle white glow below rim */}
            {/* <div className="absolute inset-x-0 top-px h-1 bg-gradient-to-b from-gray-300/30 to-transparent dark:from-white/10 pointer-events-none rounded-t-lg" /> */}
            <Composer
              ref={composerRef}
              onSend={onSend}
              disabled={isThinking}
            />
          {/* </div> */}
        </div>
      </div>
    </div>
  )
})

ChatPane.displayName = "ChatPane"

export default ChatPane

