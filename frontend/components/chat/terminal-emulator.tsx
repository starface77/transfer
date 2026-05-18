"use client"

import type React from "react"
import { useRef, useEffect, useCallback } from "react"
import { PlayCircle, Trash2, Maximize2, Minimize2, GripHorizontal } from "lucide-react"
import { cn } from "@/lib/utils"

interface TerminalEmulatorProps {
  terminalLines: string[]
  isRunningTask: boolean
  currentInput: string
  setCurrentInput: (val: string) => void
  onSubmitCommand: (e: React.FormEvent) => void
  runBuildCommand: () => void
  runTestCommand: () => void
  clearTerminal: () => void
  terminalDock: "sidebar" | "bottom"
  setTerminalDock: (dock: "sidebar" | "bottom") => void
  onDragStart?: (e: React.DragEvent) => void
  onDragEnd?: () => void
}

export function TerminalEmulator({
  terminalLines,
  isRunningTask,
  currentInput,
  setCurrentInput,
  onSubmitCommand,
  runBuildCommand,
  runTestCommand,
  clearTerminal,
  terminalDock,
  setTerminalDock,
  onDragStart,
  onDragEnd,
}: TerminalEmulatorProps) {
  const terminalEndRef = useRef<HTMLDivElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)

  // Auto-scroll to bottom
  useEffect(() => {
    terminalEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [terminalLines])

  // Listen to Recent Commands clicks from LeftSidebar
  useEffect(() => {
    const handleCommandClickEvent = (e: Event) => {
      const cmd = (e as CustomEvent).detail
      if (cmd) {
        setCurrentInput(cmd)
      }
    }
    window.addEventListener("sharrowkyn-terminal-cmd", handleCommandClickEvent)
    return () => window.removeEventListener("sharrowkyn-terminal-cmd", handleCommandClickEvent)
  }, [setCurrentInput])

  // Intercept command submissions to update localStorage "Recent Commands" dynamically!
  const handleSubmit = useCallback((e: React.FormEvent) => {
    e.preventDefault()
    if (currentInput.trim()) {
      const typed = currentInput.trim()
      const stored = localStorage.getItem("sharrowkyn-recent-commands")
      let commands = stored ? JSON.parse(stored) : []
      
      // Keep only unique, place new one at start, limit to 4
      commands = [typed, ...commands.filter((c: string) => c !== typed)].slice(0, 4)
      localStorage.setItem("sharrowkyn-recent-commands", JSON.stringify(commands))
      
      // Dispatch update notification event so LeftSidebar refreshes instantly
      window.dispatchEvent(new Event("sharrowkyn-commands-updated"))
    }
    onSubmitCommand(e)
  }, [currentInput, onSubmitCommand])

  // Focus input when clicking terminal container
  const handleContainerClick = () => {
    const inputEl = containerRef.current?.querySelector("input")
    if (inputEl) {
      inputEl.focus()
    }
  }

  return (
    <div 
      className="h-full flex flex-col bg-transparent select-none"
      onClick={handleContainerClick}
    >
      {/* Apple-Like Ultra-Minimalist Terminal Panel */}
      <div className="flex-1 bg-white border border-stone-200/60 rounded-2xl flex flex-col overflow-hidden shadow-[0_1px_8px_rgba(0,0,0,0.015)] min-h-0 relative">
        
        {/* Flat Minimalist Header */}
        <div 
          draggable={true}
          onDragStart={onDragStart}
          onDragEnd={onDragEnd}
          className="flex items-center justify-between px-5 py-2.5 border-b border-stone-100 bg-[#fafafa] shrink-0 select-none cursor-grab active:cursor-grabbing hover:bg-stone-50/80 transition-all flex-row z-10"
          title="Drag header to move or dock terminal"
        >
          <div className="flex items-center gap-3">
            {/* Flat Apple-style window indicator lights */}
            <div className="flex gap-1.5 shrink-0 select-none">
              <span className="w-2.5 h-2.5 rounded-full bg-stone-200 border border-stone-300/10"></span>
              <span className="w-2.5 h-2.5 rounded-full bg-stone-200 border border-stone-300/10"></span>
              <span className="w-2.5 h-2.5 rounded-full bg-stone-200 border border-stone-300/10"></span>
            </div>
            <div className="w-[1px] h-3 bg-stone-200 shrink-0 mx-1" />
            <div className="flex items-center gap-2">
              <GripHorizontal size={13} className="text-stone-400 hover:text-stone-600 transition-colors cursor-grab" />
              <span className="text-[10px] text-stone-400 font-mono tracking-wide">danik@sharrowkyn ~ bash</span>
            </div>
          </div>
          
          <div className="flex items-center gap-3">
            {/* Minimal flat dock toggle */}
            <button
              onClick={(e) => {
                e.stopPropagation()
                setTerminalDock(terminalDock === "sidebar" ? "bottom" : "sidebar")
              }}
              className="flex items-center gap-1 px-2 py-0.5 rounded-lg text-[9px] font-mono font-medium text-stone-400 hover:text-stone-800 hover:bg-stone-100 transition-all border border-stone-200/50"
              title={terminalDock === "sidebar" ? "Dock to Bottom" : "Dock to Right Sidebar"}
            >
              {terminalDock === "sidebar" ? (
                <>
                  <Minimize2 size={9} className="text-stone-500" />
                  <span>dock_bottom</span>
                </>
              ) : (
                <>
                  <Maximize2 size={9} className="text-stone-500" />
                  <span>dock_sidebar</span>
                </>
              )}
            </button>
          </div>
        </div>
        
        {/* Terminal Body - Light Minimalist */}
        <div 
          ref={containerRef}
          className="p-5 flex-1 overflow-y-auto font-mono text-[11.5px] leading-relaxed text-stone-600 space-y-1.5 select-text no-scrollbar cursor-text bg-white z-10"
        >
          {terminalLines.map((line, idx) => {
            const isCommand = line.startsWith("$")
            const isHeader = line.includes("~ bash")
            const isSuccess = line.startsWith("✔") || line.startsWith(" PASS") || line.startsWith("  ✓") || line.includes("successfully") || line.includes("[SUCCESS]")
            const isWarning = line.includes("[WARN]") || line.includes("info  -") || line.includes("warning") || line.startsWith("▶")
            const isSystem = line.startsWith("→")

            return (
              <div
                key={idx}
                className={cn(
                  "font-mono",
                  isCommand && "text-stone-900 font-medium flex items-center gap-1.5 mt-1",
                  isHeader && "text-stone-400 font-normal border-b border-stone-100 pb-1.5 mb-2.5",
                  isSuccess && "text-stone-700 font-medium",
                  isWarning && "text-stone-500 font-light",
                  isSystem && "text-stone-850 font-normal border-b border-stone-100 pb-1 mb-2.5 mt-4"
                )}
              >
                {isCommand ? (
                  <>
                    <span className="text-stone-400 select-none font-normal">$</span>
                    <span>{line.substring(2)}</span>
                  </>
                ) : (
                  line
                )}
              </div>
            )
          })}
          
          {/* Active Command Line input */}
          <form 
            onSubmit={handleSubmit} 
            className="flex items-center gap-1.5 pt-1.5 shrink-0 z-10"
            onClick={(e) => e.stopPropagation()}
          >
            <span className="text-stone-400 select-none font-normal">$</span>
            <div className="flex-1 flex items-center relative">
              <input
                type="text"
                value={currentInput}
                onChange={(e) => setCurrentInput(e.target.value)}
                disabled={isRunningTask}
                className="flex-1 bg-transparent border-none outline-none focus:outline-none focus:ring-0 p-0 text-[11.5px] font-mono text-stone-900 placeholder:text-stone-300"
                placeholder={isRunningTask ? "running task..." : "type command here..."}
                autoFocus
              />
              {/* Minimalist Solid Blinking Cursor */}
              {!currentInput && !isRunningTask && (
                <span className="absolute left-0 w-1.5 h-3.5 bg-stone-450 animate-[pulse_0.9s_infinite] select-none pointer-events-none ml-[0.5px]" />
              )}
            </div>
          </form>
          <div ref={terminalEndRef} />
        </div>
      </div>

      {/* Extreme Minimalist Flat Control Buttons */}
      <div className="grid grid-cols-3 gap-2 shrink-0 mt-3 font-sans">
        <button
          disabled={isRunningTask}
          onClick={(e) => { e.stopPropagation(); runBuildCommand(); }}
          className="flex items-center justify-center gap-1.5 py-1.5 border border-stone-200/60 bg-white text-stone-600 hover:text-stone-900 hover:border-stone-300 hover:bg-stone-50 transition-all rounded-xl text-[11px] font-normal shadow-[0_1px_2px_rgba(0,0,0,0.01)] disabled:opacity-50 font-sans active:scale-[0.98]"
        >
          <PlayCircle size={11} strokeWidth={1.5} className="text-stone-400" />
          <span>Build</span>
        </button>
        <button
          disabled={isRunningTask}
          onClick={(e) => { e.stopPropagation(); runTestCommand(); }}
          className="flex items-center justify-center gap-1.5 py-1.5 border border-stone-200/60 bg-white text-stone-600 hover:text-stone-900 hover:border-stone-300 hover:bg-stone-50 transition-all rounded-xl text-[11px] font-normal shadow-[0_1px_2px_rgba(0,0,0,0.01)] disabled:opacity-50 font-sans active:scale-[0.98]"
        >
          <PlayCircle size={11} strokeWidth={1.5} className="text-stone-400" />
          <span>Tests</span>
        </button>
        <button
          onClick={(e) => { e.stopPropagation(); clearTerminal(); }}
          className="flex items-center justify-center gap-1.5 py-1.5 border border-stone-200/60 bg-white text-stone-500 hover:text-stone-800 hover:border-stone-300 hover:bg-stone-50 transition-all rounded-xl text-[11px] font-normal shadow-[0_1px_2px_rgba(0,0,0,0.01)] font-sans active:scale-[0.98]"
        >
          <Trash2 size={11} strokeWidth={1.5} className="text-stone-400" />
          <span>Clear</span>
        </button>
      </div>
    </div>
  )
}
