"use client"

import { useEffect, useState } from "react"
import { Brain, Cpu, Zap, Activity } from "lucide-react"

export function AgentThinkingIndicator({
  phase = "thinking",
  message = "Processing...",
  intensity = "medium"
}: {
  phase?: string
  message?: string
  intensity?: "low" | "medium" | "high"
}) {
  const [pulseCount, setPulseCount] = useState(0)

  useEffect(() => {
    const interval = setInterval(() => {
      setPulseCount(c => c + 1)
    }, 1000)
    return () => clearInterval(interval)
  }, [])

  const getPhaseIcon = () => {
    switch (phase.toLowerCase()) {
      case "observe":
      case "explore":
        return <Activity className="w-5 h-5" />
      case "recall":
      case "context":
        return <Brain className="w-5 h-5" />
      case "reason":
      case "plan":
        return <Cpu className="w-5 h-5" />
      case "stabilize":
      case "verify":
        return <Zap className="w-5 h-5" />
      default:
        return <Brain className="w-5 h-5" />
    }
  }

  const getIntensityClass = () => {
    switch (intensity) {
      case "high":
        return "animate-pulse-fast"
      case "medium":
        return "animate-pulse"
      case "low":
        return "animate-pulse-slow"
      default:
        return "animate-pulse"
    }
  }

  return (
    <div className="relative inline-flex items-center gap-3 px-6 py-4 rounded-2xl bg-gradient-to-br from-blue-500/10 via-purple-500/10 to-pink-500/10 border border-blue-500/20 backdrop-blur-xl">
      {/* Animated background glow */}
      <div className="absolute inset-0 rounded-2xl bg-gradient-to-r from-blue-500/20 via-purple-500/20 to-pink-500/20 blur-xl animate-pulse" />

      {/* Rotating ring */}
      <div className="relative">
        <div className="absolute inset-0 rounded-full border-2 border-blue-500/30 animate-spin-slow" />
        <div className="absolute inset-0 rounded-full border-2 border-t-blue-500 border-r-purple-500 border-b-pink-500 border-l-transparent animate-spin" />

        {/* Icon */}
        <div className={`relative z-10 p-2 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 text-white ${getIntensityClass()}`}>
          {getPhaseIcon()}
        </div>
      </div>

      {/* Text content */}
      <div className="relative z-10 flex flex-col">
        <span className="text-sm font-semibold text-blue-600 dark:text-blue-400 uppercase tracking-wider">
          {phase}
        </span>
        <span className="text-xs text-gray-600 dark:text-gray-400">
          {message}
        </span>
      </div>

      {/* Pulse rings */}
      <div className="absolute inset-0 rounded-2xl">
        {[0, 1, 2].map(i => (
          <div
            key={i}
            className="absolute inset-0 rounded-2xl border border-blue-500/30 animate-ping"
            style={{
              animationDelay: `${i * 0.5}s`,
              animationDuration: "2s"
            }}
          />
        ))}
      </div>

      {/* Energy particles */}
      <div className="absolute inset-0 overflow-hidden rounded-2xl">
        {Array.from({ length: 8 }).map((_, i) => (
          <div
            key={i}
            className="absolute w-1 h-1 bg-blue-400 rounded-full animate-float"
            style={{
              left: `${Math.random() * 100}%`,
              top: `${Math.random() * 100}%`,
              animationDelay: `${Math.random() * 2}s`,
              animationDuration: `${2 + Math.random() * 2}s`
            }}
          />
        ))}
      </div>
    </div>
  )
}
