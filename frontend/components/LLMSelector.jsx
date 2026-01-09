import React, { useState } from "react"
import { ChevronDown } from "lucide-react"

export default function LLMSelector({ selectedLLM, onLLMChange, visible = false }) {
  const [isOpen, setIsOpen] = useState(false)

  if (!visible) return null

  const llms = [
    { 
      id: "gemini", 
      name: "Gemini",
      logo: "/logos/gemini.png"
    },
    { 
      id: "openai", 
      name: "OpenAI",
      logo: "/logos/chatgpt.png"
    }
  ]

  const selectedLLMData = llms.find(l => l.id === selectedLLM)

  const handleSelect = (id) => {
    onLLMChange(id)
    setIsOpen(false)
  }

  return (
    <div className="flex items-center gap-2">
      <div className="relative">
        {/* Button */}
        <button
          onClick={() => setIsOpen(!isOpen)}
          className="flex items-center gap-2 glass-card px-3 py-1.5 text-sm rounded-lg border border-white/20 bg-white/10 dark:bg-white/5 text-foreground cursor-pointer hover:bg-white/20 dark:hover:bg-white/10 transition-colors focus:outline-none focus:ring-2 focus:ring-primary/50"
        >
          <img 
            src={selectedLLMData?.logo}
            alt={selectedLLM}
            className="h-4 w-4 object-contain"
          />
          <span>{selectedLLMData?.name}</span>
          <ChevronDown className={`h-3 w-3 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
        </button>

        {/* Dropdown Menu */}
        {isOpen && (
          <div className="absolute top-full mt-1 left-0 z-50 glass-card border border-white/20 rounded-lg overflow-hidden shadow-lg">
            {llms.map((llm) => (
              <button
                key={llm.id}
                onClick={() => handleSelect(llm.id)}
                className={`w-full flex items-center gap-2 px-3 py-2 text-sm transition-colors ${
                  selectedLLM === llm.id
                    ? 'bg-primary/20 text-foreground'
                    : 'text-foreground hover:bg-white/10 dark:hover:bg-white/5'
                }`}
              >
                <img 
                  src={llm.logo}
                  alt={llm.name}
                  className="h-4 w-4 object-contain"
                />
                <span>{llm.name}</span>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
