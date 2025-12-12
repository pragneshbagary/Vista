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
        {/* Animated gradient background */}
        <div className="absolute inset-0 animated-gradient-bg opacity-40"></div>
        
        {/* Floating orbs */}
        <div className="floating-orb floating-orb-1"></div>
        <div className="floating-orb floating-orb-2"></div>
        <div className="floating-orb floating-orb-3"></div>

        {/* Empty state with glass card */}
        <div className="relative z-10 flex h-full items-center justify-center p-8">
          <div className="glass-card glass-shadow max-w-md space-y-6 p-8 text-center">
            <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-gradient-to-br from-purple-500 to-pink-500 shadow-lg">
              <Sparkles className="h-8 w-8 text-white" />
            </div>
            <div className="space-y-3">
              <h2 className="text-2xl font-bold tracking-tight text-white">
                Welcome to VISTA
              </h2>
              <p className="text-sm text-white/70 leading-relaxed">
                Your personal AI assistant powered by your knowledge base. Start a new chat to begin asking questions.
              </p>
            </div>
            <div className="pt-4 space-y-2 text-xs text-white/50">
              <p>💡 Try asking about your projects, skills, or experiences</p>
              <p>⌨️ Press <kbd className="px-2 py-1 glass-light rounded text-white/70 font-mono text-xs">Cmd/Ctrl + N</kbd> for a new chat</p>
            </div>
          </div>
        </div>
      </div>
    )
  }

  const messages = conversation.messages || []

  return (
    <div className="relative flex h-full w-full flex-col overflow-hidden">
      {/* Subtle gradient background */}
      <div className="absolute inset-0 bg-gradient-to-br from-purple-50/50 via-blue-50/30 to-pink-50/50 dark:from-purple-950/20 dark:via-blue-950/10 dark:to-pink-950/20"></div>
      
      {/* Floating orbs (subtle) */}
      <div className="absolute top-20 left-20 h-64 w-64 rounded-full bg-purple-500/10 blur-3xl"></div>
      <div className="absolute bottom-20 right-20 h-64 w-64 rounded-full bg-blue-500/10 blur-3xl"></div>

      {/* Messages area */}
      <div className="relative z-10 flex-1 overflow-y-auto px-4 py-6 scrollbar-glass">
        <div className="mx-auto max-w-3xl space-y-6">
          {messages.length === 0 ? (
            <div className="flex h-full min-h-[400px] items-center justify-center">
              <div className="glass-card glass-shadow max-w-md space-y-4 p-6 text-center">
                <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-gradient-to-br from-purple-500 to-blue-500 shadow-lg">
                  <Bot className="h-6 w-6 text-white" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-white mb-2">Start the conversation</h3>
                  <p className="text-sm text-white/60">
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
                  <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-purple-500 to-pink-500 shadow-lg">
                    <Bot className="h-5 w-5 text-white" />
                  </div>
                  <div className="glass-card glass-shadow flex items-center gap-3 px-5 py-4">
                    <div className="flex gap-1.5">
                      <div className="h-2 w-2 animate-bounce rounded-full bg-white/60 [animation-delay:-0.3s]"></div>
                      <div className="h-2 w-2 animate-bounce rounded-full bg-white/60 [animation-delay:-0.15s]"></div>
                      <div className="h-2 w-2 animate-bounce rounded-full bg-white/60"></div>
                    </div>
                    <span className="text-sm text-white/70">Thinking...</span>
                    {onPauseThinking && (
                      <button
                        onClick={onPauseThinking}
                        className="ml-2 text-xs text-white/50 hover:text-white/70 transition-colors"
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
      <div className="relative z-10 border-t border-white/10 backdrop-blur-xl bg-white/5 dark:bg-black/5">
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