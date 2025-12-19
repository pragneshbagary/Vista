import React, { useState, useRef, forwardRef, useImperativeHandle } from "react"
import { Send, Paperclip, Mic, StopCircle } from "lucide-react"

const Composer = forwardRef(({ onSend, disabled }, ref) => {
  const [input, setInput] = useState("")
  const [isRecording, setIsRecording] = useState(false)
  const textareaRef = useRef(null)

  // Expose methods to parent
  useImperativeHandle(ref, () => ({
    insertTemplate: (content) => {
      setInput(content)
      textareaRef.current?.focus()
    }
  }))

  const handleSend = () => {
    if (input.trim() && !disabled) {
      onSend(input.trim())
      setInput("")
      // Reset textarea height
      if (textareaRef.current) {
        textareaRef.current.style.height = "auto"
      }
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleInput = (e) => {
    setInput(e.target.value)
    
    // Auto-resize textarea
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto"
      textareaRef.current.style.height = Math.min(textareaRef.current.scrollHeight, 200) + "px"
    }
  }

  const toggleRecording = () => {
    setIsRecording(!isRecording)
    // TODO: Implement actual voice recording
  }

  return (
    <div className="glass-card glass-shadow relative w-full">
      {/* Main input area */}
      <div className="flex items-center gap-3 p-3">
        {/* Textarea */}
        <div className="flex-1 relative min-w-0">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={handleInput}
            onKeyDown={handleKeyDown}
            placeholder={disabled ? "VISTA is thinking..." : "Ask anything..."}
            disabled={disabled}
            className="w-full resize-none glass-input text-foreground placeholder:text-muted-foreground focus:outline-none text-sm leading-relaxed max-h-[150px]"
            rows={1}
            style={{ minHeight: "44px" }}
          />
        </div>

        {/* Send button */}
        <button
          onClick={handleSend}
          disabled={disabled}
          className="glass-shine group relative overflow-hidden flex-shrink-0 rounded-lg bg-gradient-to-br from-blue-500 to-blue-600 p-2.5 text-white shadow-lg hover:shadow-xl disabled:opacity-50 disabled:cursor-not-allowed transition-all hover:scale-105 active:scale-95 border border-blue-400/30"
          title="Send message"
        >
          <Send className="h-4 w-4" />
        </button>
      </div>

      {/* Character count */}
      {input.length > 500 && (
        <div className="border-t border-white/10 px-4 py-2">
          <span className={`text-xs ${
            input.length > 2000 ? "text-destructive" : "text-muted-foreground"
          }`}>
            {input.length} / 2000 characters
          </span>
        </div>
      )}
    </div>
  )
})

Composer.displayName = "Composer"

export default Composer
