import { Brain, MessageSquare, Sparkles, Zap } from "lucide-react"

export function WelcomeScreen() {
  const suggestions = [
    { icon: Brain, text: "What are your skills?", color: "from-blue-500 to-cyan-500" },
    { icon: MessageSquare, text: "Tell me about your projects", color: "from-purple-500 to-pink-500" },
    { icon: Zap, text: "What is your experience?", color: "from-orange-500 to-red-500" },
    { icon: Sparkles, text: "How can I contact you?", color: "from-green-500 to-emerald-500" },
  ]

  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] text-center px-4">
      <div className="relative mb-8">
        <div className="w-24 h-24 rounded-3xl bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center shadow-2xl shadow-primary/30">
          <Sparkles className="w-12 h-12 text-white" />
        </div>
        <div className="absolute -inset-4 bg-gradient-to-br from-blue-500/20 to-purple-600/20 rounded-3xl blur-2xl -z-10 animate-pulse" />
      </div>

      <h2 className="text-4xl md:text-5xl font-bold mb-4 bg-gradient-to-r from-blue-400 via-purple-400 to-pink-400 bg-clip-text text-transparent">
        Welcome to VISTA
      </h2>

      <p className="text-lg text-muted-foreground max-w-2xl mb-12 leading-relaxed">
        Your personal RAG-based AI assistant that knows everything about me. Ask any question and get accurate,
        context-aware responses.
      </p>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 w-full max-w-3xl">
        {suggestions.map((suggestion, index) => {
          const Icon = suggestion.icon
          return (
            <button
              key={index}
              className="glass-card rounded-2xl p-6 text-left hover:scale-105 transition-all duration-300 hover:shadow-xl group"
            >
              <div className="flex items-center gap-4">
                <div
                  className={`w-12 h-12 rounded-xl bg-gradient-to-br ${suggestion.color} flex items-center justify-center flex-shrink-0 shadow-lg group-hover:shadow-xl transition-shadow duration-300`}
                >
                  <Icon className="w-6 h-6 text-white" />
                </div>
                <span className="text-foreground font-medium">{suggestion.text}</span>
              </div>
            </button>
          )
        })}
      </div>

      <div className="mt-12 glass-card rounded-2xl px-6 py-4 max-w-md">
        <p className="text-sm text-muted-foreground">
          Powered by advanced <span className="text-primary font-semibold">Retrieval-Augmented Generation</span>{" "}
          technology
        </p>
      </div>
    </div>
  )
}
