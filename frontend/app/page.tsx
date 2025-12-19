"use client"

import { useState } from "react"
import AIAssistantUI from "../components/AIAssistantUI"
import LandingPage from "../components/LandingPage"

export default function Page() {
  const [showApp, setShowApp] = useState(false)

  if (showApp) {
    return <AIAssistantUI />
  }

  return <LandingPage onEnter={() => setShowApp(true)} />
}
