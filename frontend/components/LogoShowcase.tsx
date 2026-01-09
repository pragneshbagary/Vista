import React from "react"

export default function LogoShowcase() {
  return (
    <section className="relative mx-auto max-w-6xl px-6 py-[30px]">
      {/* Section Header */}
      <div className="text-center space-y-4 mb-12">
        <h2 className="text-3xl md:text-4xl font-bold">Meet VISTA</h2>
        <p className="text-muted-foreground text-lg">Your intelligent AI assistant</p>
      </div>

      {/* Logo Showcase Card */}
      <div className="glass-card glass-shadow p-12 md:p-16 flex flex-col items-center justify-center space-y-8 hover:bg-white/50 dark:hover:bg-white/10 transition-all">
        {/* Logo Container */}
        <div className="relative">
          {/* Glow effect behind logo */}
          <div className="absolute inset-0 bg-gradient-to-br from-blue-400/20 to-indigo-400/20 rounded-3xl blur-2xl" />
          
          {/* Logo */}
          <img 
            src="/vista_logo.png" 
            alt="VISTA Logo" 
            className="relative h-48 w-48 md:h-64 md:w-64 object-contain drop-shadow-lg"
          />
        </div>

        {/* Logo Description */}
        <div className="text-center space-y-3 max-w-2xl">
          <h3 className="text-2xl font-bold">VISTA</h3>
          <p className="text-muted-foreground leading-relaxed">
            Powered by advanced AI and Retrieval-Augmented Generation technology, VISTA brings intelligent conversations to life. Explore my projects, skills, and experiences through natural dialogue.
          </p>
        </div>

        {/* Features Grid */}
        <div className="grid grid-cols-3 gap-4 w-full mt-8 pt-8 border-t border-white/10">
          <div className="text-center">
            <div className="text-2xl font-bold text-blue-600 dark:text-blue-400">100%</div>
            <p className="text-xs text-muted-foreground mt-1">Accurate</p>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-indigo-600 dark:text-indigo-400">24/7</div>
            <p className="text-xs text-muted-foreground mt-1">Available</p>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-purple-600 dark:text-purple-400">∞</div>
            <p className="text-xs text-muted-foreground mt-1">Scalable</p>
          </div>
        </div>
      </div>
    </section>
  )
}
