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
    <div className="flex items-center gap-3">
      {/* Textarea */}
      <div className="flex-1 relative min-w-0">
        <textarea
          ref={textareaRef}
          value={input}
          onChange={handleInput}
          onKeyDown={handleKeyDown}
          rows={1}
          disabled={disabled}
          placeholder={disabled ? "VISTA is thinking..." : "Ask anything..."}
          className="
  glass-input
  w-full
  min-h-[44px]
  max-h-[150px]
  resize-none
  text-sm
  leading-relaxed
  placeholder:text-muted-foreground
"
        />
      </div>

      {/* Send button */}
      <button
        onClick={handleSend}
        disabled={disabled}
        className="glass-shine group relative overflow-hidden flex-shrink-0 rounded-lg bg-gradient-to-br from-gray-600 to-gray-700 p-2.5 text-white shadow-lg hover:shadow-xl disabled:opacity-50 disabled:cursor-not-allowed transition-all hover:scale-105 active:scale-95 border border-gray-500/30"
        title="Send message"
      >
        <Send className="h-4 w-4" />
      </button>
    </div>
  )
})

Composer.displayName = "Composer"

export default Composer
