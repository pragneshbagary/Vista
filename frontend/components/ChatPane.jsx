import React, { useEffect, useRef, forwardRef, useImperativeHandle } from "react"
import { Bot, Sparkles } from "lucide-react"
import Message from "./Message"
import Composer from "./Composer"

const ChatPane = forwardRef(({ 
  conversation, 
  onSend, 
  onEditMessage, 
  onResendMessage, 
  isThinking, 
  onPauseThinking 
}, ref) => {
  const messagesEndRef = useRef(null)
  const composerRef = useRef(null)

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
                Welcome to VISTA
              </h2>
              <p className="text-sm text-muted-foreground leading-relaxed">
                Your personal AI assistant powered by your knowledge base. Start a new chat to begin asking questions.
              </p>
            </div>
            <div className="pt-4 space-y-3 text-xs text-muted-foreground">
              <p className="flex items-center justify-center gap-2">
                <span>💡</span>
                <span>Ask about your projects, skills, or experiences</span>
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
      {/* Messages area */}
      <div className="relative z-10 flex-1 overflow-y-auto px-4 py-8 pb-24 scrollbar-glass">
        <div className="mx-auto max-w-3xl space-y-6 pb-4">
          {messages.length === 0 ? (
            <div className="flex h-full min-h-[400px] items-center justify-center">
              <div className="glass-card glass-shadow max-w-md space-y-6 p-10 text-center text-foreground">
                <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-primary/40 to-accent/40 backdrop-blur-md border border-white/20">
                  <Bot className="h-8 w-8 text-primary" />
                </div>
                <div>
                  <h3 className="text-xl font-semibold mb-2">Start the conversation</h3>
                  <p className="text-xs text-muted-foreground">Ask me anything about your background</p>
                </div>
              </div>
            </div>
          ) : (
            <>
              {messages.map((message) => (
                <Message
                  key={message.id}
                  message={message}
                  onEdit={onEditMessage}
                  onResend={onResendMessage}
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
            </>
          )}
          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Composer area with glass effect */}
<div className="
  relative z-10 flex-shrink-0
  backdrop-blur-xl

  border-t border-blue-300/40
  bg-gradient-to-t from-cyan/70 to-white/40
  shadow-[0_-6px_20px_rgba(59,130,246,0.12)]

  dark:border-blue-500/20
  dark:bg-gradient-to-t dark:from-slate-900/80 dark:to-slate-900/50
  dark:shadow-[0_-6px_20px_rgba(0,0,0,0.5)]
">
  {/* Glass rim */}
  <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-blue-300/60 to-transparent dark:via-blue-400/80 pointer-events-none" />
        <div className="mx-auto max-w-3xl px-4 py-4">
          <Composer
            ref={composerRef}
            onSend={onSend}
            disabled={isThinking}
          />
        </div>
      </div>
    </div>
  )
})

ChatPane.displayName = "ChatPane"

export default ChatPane

