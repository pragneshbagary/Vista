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
    <div className="glass-card glass-shadow relative">
      {/* Main input area */}
      <div className="flex items-end gap-3 p-3">
        {/* Attachment button */}
        <button
          className="glass-button flex-shrink-0 p-2 text-white/60 hover:text-white disabled:opacity-50"
          disabled={disabled}
          title="Attach file"
        >
          <Paperclip className="h-5 w-5" />
        </button>

        {/* Textarea */}
        <div className="flex-1 relative">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={handleInput}
            onKeyDown={handleKeyDown}
            placeholder={disabled ? "VISTA is thinking..." : "Ask anything about your knowledge base..."}
            disabled={disabled}
            className="w-full resize-none bg-transparent text-white placeholder-white/40 focus:outline-none text-sm leading-relaxed py-2 max-h-[200px] scrollbar-glass"
            rows={1}
            style={{ minHeight: "40px" }}
          />
        </div>

        {/* Voice/Send button */}
        <div className="flex flex-shrink-0 gap-2">
         
            <button
              onClick={handleSend}
              disabled={disabled}
              className="glass-shine group relative overflow-hidden rounded-xl bg-gradient-to-r from-purple-500 to-pink-500 p-2.5 text-white shadow-lg hover:shadow-xl disabled:opacity-50 disabled:cursor-not-allowed transition-all hover:scale-105 active:scale-95"
              title="Send message"
            >
              <Send className="h-5 w-5" />
            </button>
        </div>
      </div>



      {/* Character count or tips */}
      {input.length > 500 && (
        <div className="border-t border-white/10 px-4 py-2">
          <span className={`text-xs ${
            input.length > 2000 ? "text-red-400" : "text-white/50"
          }`}>
            {input.length} / 2000 characters
          </span>
        </div>
      )}

      {/* Keyboard shortcut hint */}
      {!input && (
        <div className="absolute bottom-4 right-4 pointer-events-none">
          <span className="text-xs text-white/30">
            <kbd className="px-1.5 py-0.5 glass-light rounded text-white/40 font-mono text-[10px]">Enter</kbd> to send
            {" • "}
            <kbd className="px-1.5 py-0.5 glass-light rounded text-white/40 font-mono text-[10px]">Shift+Enter</kbd> for new line
          </span>
        </div>
      )}
    </div>
  )
})

Composer.displayName = "Composer"

export default Composer
