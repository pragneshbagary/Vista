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
      <div className="relative flex h-full w-full flex-col overflow-hidden">
        <div className="relative z-10 flex h-full items-center justify-center p-8">
          <div className="glass-card glass-shadow max-w-md space-y-6 p-8 text-center text-foreground">
            <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-gradient-to-br from-primary to-accent shadow-lg">
              <Sparkles className="h-8 w-8 text-primary-foreground" />
            </div>
            <div className="space-y-3">
              <h2 className="text-2xl font-bold tracking-tight">
                Welcome to VISTA
              </h2>
              <p className="text-sm text-muted-foreground leading-relaxed">
                Your personal AI assistant powered by your knowledge base. Start a new chat to begin asking questions.
              </p>
            </div>
            <div className="pt-4 space-y-2 text-xs text-muted-foreground">
              <p>💡 Try asking about your projects, skills, or experiences</p>
              <p>⌨️ Press <kbd className="px-2 py-1 glass-light rounded text-xs">Cmd/Ctrl + N</kbd> for a new chat</p>
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
      <div className="relative z-10 flex-1 overflow-y-auto px-4 py-6 scrollbar-glass">
        <div className="mx-auto max-w-3xl space-y-6">
          {messages.length === 0 ? (
            <div className="flex h-full min-h-[400px] items-center justify-center">
              <div className="glass-card glass-shadow max-w-md space-y-4 p-6 text-center text-foreground">
                <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-gradient-to-br from-primary to-accent shadow-lg">
                  <Bot className="h-6 w-6 text-primary-foreground" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold mb-2">Start the conversation</h3>
                  <p className="text-sm text-muted-foreground">
                    Ask me anything from your knowledge base
                  </p>
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
                  <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-primary to-accent shadow-lg">
                    <Bot className="h-5 w-5 text-primary-foreground" />
                  </div>
                  <div className="glass-card glass-shadow flex items-center gap-3 px-5 py-4">
                    <div className="flex gap-1.5">
                      <div className="h-2 w-2 animate-bounce rounded-full bg-muted-foreground [animation-delay:-0.3s]"></div>
                      <div className="h-2 w-2 animate-bounce rounded-full bg-muted-foreground [animation-delay:-0.15s]"></div>
                      <div className="h-2 w-2 animate-bounce rounded-full bg-muted-foreground"></div>
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
      <div className="relative z-10 border-t border-border bg-background/50 backdrop-blur-lg">
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

