import React from "react"
import { ArrowRight, Github, Linkedin, Sparkles, MessageSquare, Brain, Zap } from "lucide-react"

interface LandingPageProps {
  onEnter: () => void
}

export default function LandingPage({ onEnter }: LandingPageProps) {
  return (
    <div className="min-h-screen w-full bg-gradient-to-br from-blue-100/40 via-blue-50/50 to-cyan-50/30 dark:from-slate-950 dark:via-blue-950/20 dark:to-slate-950 text-foreground overflow-hidden">
      {/* Animated background gradient */}
      <div className="fixed inset-0 -z-10 bg-gradient-to-br from-blue-300/8 via-purple-200/5 to-indigo-300/8 dark:from-blue-500/5 dark:via-transparent dark:to-indigo-500/5 pointer-events-none" />

      {/* Navigation */}
      <nav className="sticky top-0 z-40 border-b border-blue-200/30 bg-white/20 dark:border-white/10 dark:bg-white/3 backdrop-blur-xl">
        <div className="mx-auto max-w-6xl px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-blue-400/40 to-indigo-400/40 backdrop-blur-md border border-white/20">
              <Sparkles className="h-5 w-5 text-blue-600 dark:text-blue-400" />
            </div>
            <span className="text-lg font-bold tracking-tight">VISTA</span>
          </div>
          <button
            onClick={onEnter}
            className="inline-flex items-center gap-2 rounded-lg border border-blue-200/40 bg-white/40 backdrop-blur-md px-4 py-2.5 text-sm font-medium text-foreground hover:bg-white/60 hover:border-blue-300/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-400/40 transition-all dark:border-white/10 dark:bg-white/5 dark:hover:bg-white/10"
          >
            Launch App
            <ArrowRight className="h-4 w-4" />
          </button>
        </div>
      </nav>

      {/* Hero Section */}
      <div className="relative mx-auto max-w-6xl px-6 py-20 md:py-32">
        <div className="grid md:grid-cols-2 gap-12 items-center">
          {/* Left Content */}
          <div className="space-y-8">
            <div className="space-y-4">
              <h1 className="text-5xl md:text-6xl font-bold tracking-tight leading-tight">
                Meet <span className="bg-gradient-to-r from-blue-600 to-indigo-600 dark:from-blue-400 dark:to-indigo-400 bg-clip-text text-transparent">VISTA</span>
              </h1>
              <p className="text-xl text-muted-foreground leading-relaxed">
                Your personal AI assistant powered by advanced RAG technology. Ask anything about my projects, skills, and experiences.
              </p>
            </div>

            <div className="space-y-4">
              <p className="text-sm font-semibold text-foreground/70 uppercase tracking-wider">Powered by</p>
              <div className="flex flex-wrap gap-3">
                <div className="glass-card px-4 py-2 text-sm font-medium">🤖 LLM</div>
                <div className="glass-card px-4 py-2 text-sm font-medium">📚 RAG</div>
                <div className="glass-card px-4 py-2 text-sm font-medium">🧠 Knowledge Base</div>
              </div>
            </div>

            <button
              onClick={onEnter}
              className="glass-shine group relative overflow-hidden rounded-lg flex items-center gap-2 px-6 py-3.5 text-base font-medium bg-gradient-to-br from-blue-500 to-blue-600 text-white shadow-lg hover:shadow-xl transition-all hover:scale-105 active:scale-95 border border-blue-400/30 w-fit"
            >
              Start Chatting
              <ArrowRight className="h-5 w-5 group-hover:translate-x-1 transition-transform" />
            </button>
          </div>

          {/* Right Features */}
          <div className="space-y-4">
            <div className="glass-card glass-shadow p-6 space-y-4 hover:bg-white/50 dark:hover:bg-white/10 transition-all">
              <div className="flex items-start gap-4">
                <div className="flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-lg bg-blue-100/50 dark:bg-blue-500/20">
                  <MessageSquare className="h-6 w-6 text-blue-600 dark:text-blue-400" />
                </div>
                <div>
                  <h3 className="font-semibold mb-1">Intelligent Conversations</h3>
                  <p className="text-sm text-muted-foreground">Ask natural questions and get detailed, contextual answers about my background.</p>
                </div>
              </div>
            </div>

            <div className="glass-card glass-shadow p-6 space-y-4 hover:bg-white/50 dark:hover:bg-white/10 transition-all">
              <div className="flex items-start gap-4">
                <div className="flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-lg bg-indigo-100/50 dark:bg-indigo-500/20">
                  <Brain className="h-6 w-6 text-indigo-600 dark:text-indigo-400" />
                </div>
                <div>
                  <h3 className="font-semibold mb-1">RAG Technology</h3>
                  <p className="text-sm text-muted-foreground">Retrieval-Augmented Generation ensures accurate, sourced responses from my knowledge base.</p>
                </div>
              </div>
            </div>

            <div className="glass-card glass-shadow p-6 space-y-4 hover:bg-white/50 dark:hover:bg-white/10 transition-all">
              <div className="flex items-start gap-4">
                <div className="flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-lg bg-purple-100/50 dark:bg-purple-500/20">
                  <Zap className="h-6 w-6 text-purple-600 dark:text-purple-400" />
                </div>
                <div>
                  <h3 className="font-semibold mb-1">Fast & Reliable</h3>
                  <p className="text-sm text-muted-foreground">Get instant responses with a modern, responsive interface built for recruiters.</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Social Links Section */}
      <div className="relative mx-auto max-w-6xl px-6 py-16 border-t border-blue-200/30 dark:border-white/10">
        <div className="space-y-8">
          <div className="text-center space-y-3">
            <h2 className="text-3xl font-bold">Let's Connect</h2>
            <p className="text-muted-foreground">Find me on social media or explore my work</p>
          </div>

          <div className="flex flex-wrap justify-center gap-4">
            <a
              href="https://github.com"
              target="_blank"
              rel="noopener noreferrer"
              className="glass-card glass-shadow px-6 py-3 flex items-center gap-3 hover:bg-white/50 dark:hover:bg-white/10 transition-all group"
            >
              <Github className="h-5 w-5 group-hover:scale-110 transition-transform" />
              <span className="font-medium">GitHub</span>
              <ArrowRight className="h-4 w-4 opacity-0 group-hover:opacity-100 transition-opacity" />
            </a>

            <a
              href="https://linkedin.com"
              target="_blank"
              rel="noopener noreferrer"
              className="glass-card glass-shadow px-6 py-3 flex items-center gap-3 hover:bg-white/50 dark:hover:bg-white/10 transition-all group"
            >
              <Linkedin className="h-5 w-5 group-hover:scale-110 transition-transform" />
              <span className="font-medium">LinkedIn</span>
              <ArrowRight className="h-4 w-4 opacity-0 group-hover:opacity-100 transition-opacity" />
            </a>

            <a
              href="mailto:your.email@example.com"
              className="glass-card glass-shadow px-6 py-3 flex items-center gap-3 hover:bg-white/50 dark:hover:bg-white/10 transition-all group"
            >
              <span className="text-xl">✉️</span>
              <span className="font-medium">Email</span>
              <ArrowRight className="h-4 w-4 opacity-0 group-hover:opacity-100 transition-opacity" />
            </a>
          </div>
        </div>
      </div>

      {/* Footer */}
      <footer className="relative border-t border-blue-200/30 dark:border-white/10 bg-white/10 dark:bg-white/5 backdrop-blur-xl">
        <div className="mx-auto max-w-6xl px-6 py-8 text-center text-sm text-muted-foreground">
          <p>Built with ❤️ using Next.js, TypeScript, and AI • © 2025</p>
        </div>
      </footer>
    </div>
  )
}
