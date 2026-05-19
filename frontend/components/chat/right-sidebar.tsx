"use client"

import React, { useState, useEffect, useCallback } from "react"
import { Terminal as TerminalIcon, BookOpen, Settings, Cpu, Wifi, ArrowDownToLine, CheckSquare2 } from "lucide-react"
import { cn } from "@/lib/utils"
import { TerminalEmulator } from "./terminal-emulator"
import { AgentTasks } from "./agent-tasks"

interface RightSidebarProps {
  isOpen: boolean
  onToggle: () => void
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
  isDraggingTerminal: boolean
  onDragStart?: (e: React.DragEvent) => void
  onDragEnd?: () => void
}

export function RightSidebar({ 
  isOpen, 
  onToggle,
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
  isDraggingTerminal,
  onDragStart,
  onDragEnd,
}: RightSidebarProps) {
  const [activeTab, setActiveTab] = useState<string>("terminal")

  // Backend URL
  const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "http://127.0.0.1:8000"

  // --- STATS SYSTEM (LIVE DATA from backend) ---
  const [cpuUsage, setCpuUsage] = useState(0)
  const [memoryUsage, setMemoryUsage] = useState(0) // GB
  const [networkPing, setNetworkPing] = useState(0) // ms

  // --- APPLE STYLE RESIZING ---
  const [width, setWidth] = useState(320)
  const [isResizing, setIsResizing] = useState(false)

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault()
    setIsResizing(true)
    const startX = e.clientX
    const startWidth = width

    const doDrag = (moveEvent: MouseEvent) => {
      const deltaX = startX - moveEvent.clientX // Dragging left increases width
      // Apple sidebar bounds constraints: 280px to 480px width limits
      const nextWidth = Math.max(280, Math.min(startWidth + deltaX, 480))
      setWidth(nextWidth)
    }

    const stopDrag = () => {
      setIsResizing(false)
      document.removeEventListener("mousemove", doDrag)
      document.removeEventListener("mouseup", stopDrag)
    }

    document.addEventListener("mousemove", doDrag)
    document.addEventListener("mouseup", stopDrag)
  }, [width])

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const res = await fetch(`${BACKEND_URL}/api/stats`)
        if (res.ok) {
          const data = await res.json()
          setCpuUsage(Math.round(data.cpu ?? 0))
          setMemoryUsage(data.memory_gb ?? 0)
          setNetworkPing(data.ping ?? 0)
        }
      } catch {
        // Backend not available — keep last values
      }
    }
    fetchStats()
    const timer = setInterval(fetchStats, 3000)
    return () => clearInterval(timer)
  }, [BACKEND_URL])

  const tabs = [
    { id: "terminal", label: "Terminal", icon: TerminalIcon },
    { id: "tasks", label: "Tasks", icon: CheckSquare2 },
    { id: "logs", label: "Logs", icon: BookOpen },
    { id: "info", label: "Info", icon: Settings },
  ]

  return (
    <>
      <aside 
        style={{ width: isOpen ? `${width}px` : "0px" }}
        className={cn(
          "hidden lg:flex flex-col bg-[#fcfcfc] overflow-hidden shrink-0 relative select-none",
          isOpen && "border-l border-stone-200/60",
          isResizing ? "transition-none" : "transition-all duration-300 ease-in-out"
        )}
      >
        {/* Apple Style Resizer handle on the left edge */}
        {isOpen && (
          <div
            onMouseDown={handleMouseDown}
            className="absolute top-0 left-0 w-1.5 h-full cursor-col-resize hover:bg-stone-200/50 active:bg-stone-300/60 transition-colors z-50 group flex items-center justify-center"
            title="Drag left edge to resize"
          >
            <div className="w-[1.5px] h-8 bg-stone-200/40 group-hover:bg-stone-400/60 group-active:bg-stone-500 rounded-full transition-colors" />
          </div>
        )}

        {/* Sleek Segmented Control Header */}
        <div className="px-4 py-3 border-b border-stone-200/60 bg-transparent shrink-0">
          <div className="flex bg-stone-100 p-0.5 rounded-xl">
            {tabs.map((tab) => {
              const IconComponent = tab.icon
              const isActive = activeTab === tab.id

              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={cn(
                    "flex-1 flex items-center justify-center gap-2 py-1.5 px-2 text-[12px] font-medium rounded-lg transition-all duration-150 font-sans",
                    isActive
                      ? "bg-white text-stone-900 shadow-[0_1px_4px_rgba(0,0,0,0.04)] border border-stone-200/20"
                      : "text-stone-400 hover:text-stone-600"
                  )}
                >
                  <IconComponent size={14} strokeWidth={1.5} />
                  <span>{tab.label}</span>
                </button>
              )
            })}
          </div>
        </div>

        {/* Content Area - Clean Background */}
        <div className="flex-1 overflow-y-auto no-scrollbar bg-transparent">
          
          {/* TERMINAL VIEW */}
          {activeTab === "terminal" && (
            <div className="p-4 h-full">
              {terminalDock === "sidebar" ? (
                <TerminalEmulator
                  terminalLines={terminalLines}
                  isRunningTask={isRunningTask}
                  currentInput={currentInput}
                  setCurrentInput={setCurrentInput}
                  onSubmitCommand={onSubmitCommand}
                  runBuildCommand={runBuildCommand}
                  runTestCommand={runTestCommand}
                  clearTerminal={clearTerminal}
                  terminalDock={terminalDock}
                  setTerminalDock={setTerminalDock}
                  onDragStart={onDragStart}
                  onDragEnd={onDragEnd}
                />
              ) : isDraggingTerminal ? (
                /* Dynamic Drag and Drop Zone inside right sidebar */
                <div 
                  onDragOver={(e) => {
                    e.preventDefault()
                    e.dataTransfer.dropEffect = "move"
                  }}
                  onDrop={() => setTerminalDock("sidebar")}
                  className="h-full flex flex-col items-center justify-center p-6 text-center border-2 border-dashed border-emerald-400/60 bg-emerald-50/10 rounded-2xl cursor-pointer transition-all hover:border-emerald-500 hover:bg-emerald-50/20 shadow-[inset_0_2px_8px_rgba(16,185,129,0.02)] min-h-[300px]"
                >
                  <div className="w-10 h-10 rounded-full bg-emerald-50 border border-emerald-100 flex items-center justify-center text-emerald-600 shadow-sm mb-3">
                    <ArrowDownToLine size={18} strokeWidth={1.5} className="animate-bounce" />
                  </div>
                  <h4 className="text-[13px] font-medium text-emerald-800 font-sans">Drop here to Dock Sidebar</h4>
                  <p className="text-[11px] text-emerald-500/70 font-sans mt-1 max-w-[200px] leading-relaxed">
                    Release the terminal header to snap it back to the sidebar.
                  </p>
                </div>
              ) : (
                <div className="h-full flex flex-col items-center justify-center p-6 text-center bg-stone-50 border border-stone-200/60 rounded-2xl animate-in fade-in duration-300 min-h-[300px]">
                  <div className="w-10 h-10 rounded-full bg-white border border-stone-200 flex items-center justify-center text-stone-400 shadow-sm mb-3">
                    <TerminalIcon size={18} strokeWidth={1.5} />
                  </div>
                  <h4 className="text-[13px] font-medium text-stone-700 font-sans">Terminal docked at bottom</h4>
                  <p className="text-[11px] text-stone-400 font-sans mt-1 max-w-[200px] leading-relaxed">
                    The terminal panel has been moved under the main workspace for wider viewing.
                  </p>
                  <button
                    onClick={() => setTerminalDock("sidebar")}
                    className="mt-4 px-3.5 py-1.5 bg-stone-900 hover:bg-stone-850 text-white rounded-xl text-[11px] font-normal transition-colors shadow-sm font-sans"
                  >
                    Dock Sidebar
                  </button>
                </div>
              )}
            </div>
          )}

          {/* TASKS VIEW - Integrated Todo Manager */}
          {activeTab === "tasks" && (
            <div className="h-full bg-stone-50/20">
              <AgentTasks />
            </div>
          )}

          {/* LOGS VIEW - Ultra-Sleek Accent Bar Layout */}
          {activeTab === "logs" && (
            <div className="p-0 bg-transparent">
              <div className="border-b border-stone-200/60 px-5 py-3 flex items-center justify-between">
                <span className="text-[11px] font-medium text-stone-400 uppercase tracking-widest font-sans">Event Stream</span>
                <span className="relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                </span>
              </div>
              <div className="py-2 divide-y divide-stone-50 select-none">
                {[
                  { time: "11:43:53", type: "success", tag: "merger", msg: "Applied diff line replacements inside composer.tsx" },
                  { time: "11:42:01", type: "info", tag: "engine", msg: "Rendered agentic timeline on websocket client" },
                  { time: "11:41:45", type: "info", tag: "dsm", msg: "Querying dynamic associative vector segments" },
                  { time: "11:40:44", type: "warning", tag: "router", msg: "Load-balancing load adjustment triggered" },
                  { time: "11:40:00", type: "info", tag: "system", msg: "Autonomous workspace listener initialized" },
                ].map((log, i) => (
                  <div 
                    key={i} 
                    className="px-5 py-2.5 flex items-center gap-3.5 hover:bg-stone-50/70 transition-colors cursor-default"
                  >
                    {/* Left thin accent line indicator */}
                    <div 
                      className={cn(
                        "w-[3px] h-6 rounded-full shrink-0",
                        log.type === "success" && "bg-emerald-400",
                        log.type === "info" && "bg-stone-200",
                        log.type === "warning" && "bg-amber-400"
                      )} 
                    />
                    
                    <div className="flex-1 min-w-0 flex items-center justify-between gap-4">
                      <div className="flex items-center gap-3 min-w-0">
                        <span className="text-[11px] font-mono text-stone-300 shrink-0">{log.time}</span>
                        <span className="text-[12.5px] font-normal text-stone-600 truncate font-sans">
                          {log.msg}
                        </span>
                      </div>
                      <span className="text-[10px] font-mono text-stone-400 shrink-0 uppercase tracking-wider font-medium">
                        {log.tag}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* INFO VIEW - Breathtaking Real-time Performance Indicators */}
          {activeTab === "info" && (
            <div className="p-4 space-y-6">
              
              {/* Performance Section */}
              <div>
                <div className="text-[11px] font-medium text-stone-400 uppercase tracking-widest mb-3 px-1 font-sans">System Performance</div>
                <div className="bg-white border border-stone-200/80 rounded-2xl p-4 shadow-[0_1px_8px_rgba(0,0,0,0.01)] space-y-4">
                  {/* CPU usage with live bar */}
                  <div className="space-y-1.5">
                    <div className="flex justify-between items-center text-[12px] font-sans text-stone-500">
                      <span>Compute Usage (CPU)</span>
                      <span className="font-mono text-stone-850 font-semibold">{cpuUsage}%</span>
                    </div>
                    <div className="h-2 w-full bg-stone-100 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-stone-900 rounded-full transition-all duration-1000 ease-out"
                        style={{ width: `${cpuUsage}%` }}
                      ></div>
                    </div>
                  </div>

                  {/* Memory usage with live bar */}
                  <div className="space-y-1.5">
                    <div className="flex justify-between items-center text-[12px] font-sans text-stone-500">
                      <span>DSM Allocated Cache</span>
                      <span className="font-mono text-stone-850 font-semibold">{memoryUsage.toFixed(2)} GB</span>
                    </div>
                    <div className="h-2 w-full bg-stone-100 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-stone-400 rounded-full transition-all duration-1000 ease-out"
                        style={{ width: `${(memoryUsage / 2.0) * 100}%` }}
                      ></div>
                    </div>
                    <div className="flex justify-between text-[9px] text-stone-400 font-sans pt-0.5">
                      <span>0.00 GB</span>
                      <span>Cap: 2.00 GB</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Status Section */}
              <div>
                <div className="text-[11px] font-medium text-stone-400 uppercase tracking-widest mb-3 px-1 font-sans">Network & Intel</div>
                <div className="bg-white border border-stone-200/80 rounded-2xl overflow-hidden shadow-[0_1px_8px_rgba(0,0,0,0.01)] select-none">
                  <div className="flex items-center justify-between p-3.5 border-b border-stone-100">
                    <div className="flex items-center gap-2.5">
                      <Wifi strokeWidth={1.5} className="w-4 h-4 text-stone-400" />
                      <span className="text-[13px] text-stone-600 font-normal font-sans">DSM Sync Latency</span>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <div className="w-1.5 h-1.5 rounded-full bg-emerald-400"></div>
                      <span className="text-[12px] font-mono text-stone-500">{networkPing}ms</span>
                    </div>
                  </div>
                  <div className="flex items-center justify-between p-3.5">
                    <div className="flex items-center gap-2.5">
                      <Cpu strokeWidth={1.5} className="w-4 h-4 text-stone-400" />
                      <span className="text-[13px] text-stone-600 font-normal font-sans">MoE Load Balancing</span>
                    </div>
                    <span className="text-[12px] font-mono text-stone-400/80">stable</span>
                  </div>
                </div>
              </div>

              {/* Active Sub-routines Section */}
              <div>
                <div className="text-[11px] font-medium text-stone-400 uppercase tracking-widest mb-3 px-1 font-sans">Active Cognitive Routines</div>
                <div className="bg-white border border-stone-200/80 rounded-2xl p-4 shadow-[0_1px_8px_rgba(0,0,0,0.01)] space-y-3.5">
                  {[
                    { name: "Associative Indexer", desc: "Clustering workspace segments", active: true },
                    { name: "MoE Routing Protocol", desc: "Balancing local model instances", active: true },
                    { name: "Trace Context Resolver", desc: "Idle - awaiting context clearing", active: false },
                  ].map((sub, i) => (
                    <div key={i} className="flex items-start gap-3">
                      <div className="mt-0.5 shrink-0">
                        {sub.active ? (
                          <span className="relative flex h-2 w-2 mt-1">
                            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                            <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                          </span>
                        ) : (
                          <div className="w-2 h-2 rounded-full bg-stone-300 mt-1"></div>
                        )}
                      </div>
                      <div className="flex flex-col">
                        <span className="text-[12.5px] text-stone-850 font-medium font-sans leading-tight">{sub.name}</span>
                        <span className="text-[11px] text-stone-400 font-sans mt-0.5 leading-normal">{sub.desc}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

            </div>
          )}
        </div>
      </aside>
    </>
  )
}
