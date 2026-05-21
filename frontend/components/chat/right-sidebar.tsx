"use client"

import React, { useState, useEffect, useCallback } from "react"
import { Terminal as TerminalIcon, BookOpen, Settings, Cpu, Wifi, ArrowDownToLine, CheckSquare2, AlertTriangle, CheckCircle2, CircleDashed, Loader2, Brain, Wrench } from "lucide-react"
import { cn } from "@/lib/utils"
import { TerminalEmulator } from "./terminal-emulator"
import { AgentTasks } from "./agent-tasks"
import { ToolsPanel } from "./tools-panel"
import type { AgentState, AgentPhase, ProjectIntelligence, ToolActivity, ContextStatus, RuntimeHint, DiffStatus, TestStatus, PhaseStatus } from "./chat-shell"

function formatDuration(ms?: number) {
  if (!ms) return "—"
  if (ms < 1000) return `${Math.round(ms)}ms`
  const seconds = Math.round(ms / 1000)
  if (seconds < 60) return `${seconds}s`
  return `${Math.floor(seconds / 60)}m ${seconds % 60}s`
}

function getPhaseIcon(status: PhaseStatus) {
  if (status === "running") return <Loader2 size={13} strokeWidth={1.5} className="text-stone-400 animate-spin" />
  if (status === "done") return <CheckCircle2 size={13} strokeWidth={1.5} className="text-emerald-500/80" />
  if (status === "error") return <AlertTriangle size={13} strokeWidth={1.5} className="text-red-500/80" />
  return <CircleDashed size={13} strokeWidth={1.5} className="text-stone-300" />
}

function getActivityTone(status: ToolActivity["status"]) {
  if (status === "error") return "bg-red-400"
  if (status === "done") return "bg-emerald-400"
  if (status === "running") return "bg-stone-500"
  return "bg-stone-200"
}

interface RightSidebarProps {
  isOpen: boolean
  onToggle: () => void
  terminalLines?: string[]
  isRunningTask?: boolean
  currentInput?: string
  setCurrentInput?: (val: string) => void
  onSubmitCommand?: (e: React.FormEvent) => void
  runBuildCommand?: () => void
  runTestCommand?: () => void
  clearTerminal?: () => void
  terminalDock?: "sidebar" | "bottom"
  setTerminalDock?: (dock: "sidebar" | "bottom") => void
  isDraggingTerminal?: boolean
  onDragStart?: (e: React.DragEvent) => void
  onDragEnd?: () => void
  agentState?: AgentState
  phases?: AgentPhase[]
  projectIntelligence?: ProjectIntelligence
  toolActivity?: ToolActivity[]
  contextStatus?: ContextStatus
  runtimeHints?: RuntimeHint[]
  diffStatus?: DiffStatus
  testStatus?: TestStatus
  selectedModel?: string
  backendUrl?: string
  backendConnected?: boolean
  cognitiveState?: any
  setCognitiveState?: (state: any) => void
}

export function RightSidebar({ 
  isOpen, 
  onToggle,
  terminalLines = ["sharrowkin-core ~ bash", "→ Terminal idle."],
  isRunningTask = false,
  currentInput = "",
  setCurrentInput = () => {},
  onSubmitCommand = (event: React.FormEvent) => event.preventDefault(),
  runBuildCommand = () => {},
  runTestCommand = () => {},
  clearTerminal = () => {},
  terminalDock = "sidebar",
  setTerminalDock = () => {},
  isDraggingTerminal = false,
  onDragStart,
  onDragEnd,
  agentState = { status: "idle", message: "Workspace ready" },
  phases = [],
  projectIntelligence = { status: "unknown" },
  toolActivity = [],
  contextStatus = { status: "unknown" },
  runtimeHints = [],
  diffStatus = { status: "none" },
  testStatus = { status: "idle" },
  selectedModel = "default",
  backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || "http://127.0.0.1:8000",
  backendConnected = true,
  cognitiveState: propCognitiveState,
  setCognitiveState: propSetCognitiveState,
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

  // --- COGNITIVE STATE SYSTEM ---
  const [cognitiveState, setCognitiveState] = useState<any>(propCognitiveState || {
    mode: "Full NARE-Field",
    energy_ledger: {
      forward: 15.45,
      memory_search: 12.50,
      trace_replay: 22.00,
      expert_reasoning: 35.50,
      hebbian: 0.00,
      total: 85.45
    },
    attractors: [],
    traces: [],
    dim: 128,
    matrix_density: 0.0,
    sampled_matrix: Array(16).fill(0).map(() => Array(16).fill(0))
  })

  useEffect(() => {
    if (propCognitiveState) {
      setCognitiveState(propCognitiveState)
    }
  }, [propCognitiveState])

  useEffect(() => {
    const fetchCognitive = async () => {
      try {
        const res = await fetch(`${BACKEND_URL}/api/cognitive/state`)
        if (res.ok) {
          const data = await res.json()
          setCognitiveState(data)
          if (propSetCognitiveState) {
            propSetCognitiveState(data)
          }
        }
      } catch {
        // Backend not available
      }
    }
    fetchCognitive()
    const timer = setInterval(fetchCognitive, 3000)
    return () => clearInterval(timer)
  }, [BACKEND_URL, propSetCognitiveState])

  const tabs = [
    { id: "terminal", label: "Terminal", icon: TerminalIcon },
    { id: "tools", label: "Tools", icon: Wrench },
    { id: "tasks", label: "Tasks", icon: CheckSquare2 },
    { id: "logs", label: "Logs", icon: BookOpen },
    { id: "info", label: "Info", icon: Settings },
  ]

  return (
    <>
      <aside 
        style={{ width: isOpen ? `${width}px` : "0px" }}
        className={cn(
          "hidden lg:flex flex-col bg-white overflow-hidden shrink-0 relative select-none",
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

        <div className="px-4 py-3 border-b border-stone-200/70 bg-white shrink-0">
          <div className="grid grid-cols-5 gap-1 rounded-xl border border-stone-200/70 bg-stone-50/70 p-1">
            {tabs.map((tab) => {
              const IconComponent = tab.icon
              const isActive = activeTab === tab.id

              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={cn(
                    "flex items-center justify-center gap-1.5 rounded-lg px-2 py-1.5 text-[12px] font-normal transition-all duration-150 font-sans",
                    isActive
                      ? "bg-white text-stone-900 shadow-[0_1px_5px_rgba(0,0,0,0.045)]"
                      : "text-stone-400 hover:text-stone-650"
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

          {/* TOOLS VIEW */}
          {activeTab === "tools" && (
            <div className="h-full overflow-y-auto">
              <ToolsPanel />
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
                {toolActivity.length === 0 ? (
                  <div className="px-5 py-8 text-center">
                    <CircleDashed size={22} strokeWidth={1.5} className="mx-auto text-stone-300 mb-2" />
                    <div className="text-[12px] text-stone-400">Tool activity will appear here during a run.</div>
                  </div>
                ) : toolActivity.map((activity) => (
                  <div 
                    key={activity.id} 
                    className="px-5 py-2.5 flex items-center gap-3.5 hover:bg-stone-50/70 transition-colors cursor-default"
                  >
                    <div className={cn("w-[3px] h-6 rounded-full shrink-0", getActivityTone(activity.status))} />
                    
                    <div className="flex-1 min-w-0 flex items-center justify-between gap-4">
                      <div className="flex items-center gap-3 min-w-0">
                        <span className="text-[11px] font-mono text-stone-300 shrink-0">
                          {activity.startedAt ? new Date(activity.startedAt).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" }) : "--:--:--"}
                        </span>
                        <span className="text-[12.5px] font-normal text-stone-600 truncate font-sans">
                          {activity.message || activity.name}
                        </span>
                      </div>
                      <span className="text-[10px] font-mono text-stone-400 shrink-0 uppercase tracking-wider font-medium">
                        {activity.name}
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
              
              <div>
                <div className="text-[11px] font-medium text-stone-400 uppercase tracking-widest mb-3 px-1 font-sans">Active Workspace</div>
                <div className="bg-white border border-stone-200/80 rounded-2xl overflow-hidden shadow-[0_1px_8px_rgba(0,0,0,0.01)]">
                  <div className="p-3.5 border-b border-stone-100 flex items-center justify-between gap-3">
                    <span className="text-[12.5px] text-stone-600 truncate">Model</span>
                    <span className="text-[11px] font-mono text-stone-500 truncate max-w-[170px]">{selectedModel}</span>
                  </div>
                  <div className="p-3.5 border-b border-stone-100 flex items-center justify-between gap-3">
                    <span className="text-[12.5px] text-stone-600 truncate">Backend</span>
                    <span className="text-[11px] font-mono text-stone-500 truncate max-w-[170px]">{backendUrl.replace(/^https?:\/\//, "")}</span>
                  </div>
                  <div className="p-3.5 flex items-center justify-between gap-3">
                    <span className="text-[12.5px] text-stone-600 truncate">Diff / Tests</span>
                    <span className="text-[11px] font-mono text-stone-500 truncate">{diffStatus.status} · {testStatus.status}</span>
                  </div>
                </div>
              </div>

              {/* Workspace Intelligence Section */}
              {projectIntelligence.status !== "unknown" && (
                <div>
                  <div className="text-[11px] font-medium text-stone-400 uppercase tracking-widest mb-3 px-1 font-sans">Workspace Intelligence</div>
                  <div className="bg-white border border-stone-200/80 rounded-2xl p-4 shadow-[0_1px_8px_rgba(0,0,0,0.01)] space-y-4">
                    
                    <div className="grid grid-cols-2 gap-3">
                      <div className="flex flex-col">
                        <span className="text-[10px] text-stone-400 uppercase tracking-wider mb-0.5">Files</span>
                        <span className="text-[13px] font-mono text-stone-700">{projectIntelligence.filesIndexed ?? 0}</span>
                      </div>
                      <div className="flex flex-col">
                        <span className="text-[10px] text-stone-400 uppercase tracking-wider mb-0.5">Lines</span>
                        <span className="text-[13px] font-mono text-stone-700">{projectIntelligence.linesIndexed ?? 0}</span>
                      </div>
                    </div>

                    <div className="h-px w-full bg-stone-100" />

                    <div className="space-y-1.5">
                      <div className="flex justify-between items-center text-[12px] font-sans text-stone-500">
                        <span>Avg Complexity</span>
                        <span className={cn(
                          "font-mono font-semibold",
                          (projectIntelligence.complexityAvg || 0) > 10 ? "text-red-500" :
                          (projectIntelligence.complexityAvg || 0) > 5 ? "text-amber-500" : "text-emerald-500"
                        )}>{projectIntelligence.complexityAvg?.toFixed(1) || "1.0"}</span>
                      </div>
                      <div className="h-1.5 w-full bg-stone-100 rounded-full overflow-hidden">
                        <div
                          className={cn(
                            "h-full rounded-full transition-all duration-1000 ease-out",
                            (projectIntelligence.complexityAvg || 0) > 10 ? "bg-red-400" :
                            (projectIntelligence.complexityAvg || 0) > 5 ? "bg-amber-400" : "bg-emerald-400"
                          )}
                          style={{ width: `${Math.min(((projectIntelligence.complexityAvg || 0) / 15) * 100, 100)}%` }}
                        ></div>
                      </div>
                    </div>

                    <div className="flex justify-between items-center text-[12px] font-sans text-stone-500">
                      <span>Circular Dependencies</span>
                      {projectIntelligence.circularDependencies ? (
                        <span className="flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-red-50 text-red-600 text-[10px] font-medium border border-red-100">
                          <AlertTriangle size={10} />
                          {projectIntelligence.circularDependencies} Found
                        </span>
                      ) : (
                        <span className="flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-600 text-[10px] font-medium border border-emerald-100">
                          <CheckCircle2 size={10} />
                          Clean
                        </span>
                      )}
                    </div>

                    {projectIntelligence.mostComplexFunctions && projectIntelligence.mostComplexFunctions.length > 0 && (
                      <div className="pt-2">
                        <div className="text-[10px] text-stone-400 uppercase tracking-wider mb-2">Code Hotspots</div>
                        <div className="space-y-1.5 max-h-[120px] overflow-y-auto no-scrollbar pr-1">
                          {projectIntelligence.mostComplexFunctions.map((func, i) => (
                            <div key={i} className="flex items-center justify-between gap-3 text-[11px] font-mono p-1.5 rounded-lg hover:bg-stone-50">
                              <span className="text-stone-600 truncate" title={func.id}>{func.id.split('.').pop()}</span>
                              <span className={cn(
                                "shrink-0",
                                func.complexity > 10 ? "text-red-500" : func.complexity > 5 ? "text-amber-500" : "text-stone-400"
                              )}>
                                {func.complexity}
                              </span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {runtimeHints.length > 0 && (
                <div>
                  <div className="text-[11px] font-medium text-stone-400 uppercase tracking-widest mb-3 px-1 font-sans">Runtime Hints</div>
                  <div className="bg-white border border-stone-200/80 rounded-2xl p-3 shadow-[0_1px_8px_rgba(0,0,0,0.01)] space-y-2">
                    {runtimeHints.map((hint) => (
                      <div key={hint.id} className="flex items-center justify-between gap-3">
                        <span className="text-[12px] text-stone-500 truncate">{hint.label}</span>
                        <span className={cn("text-[11px] font-mono truncate", hint.tone === "good" ? "text-emerald-600" : hint.tone === "warning" ? "text-amber-600" : hint.tone === "error" ? "text-red-600" : "text-stone-400")}>{hint.value}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

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
                      <span>Memory Usage</span>
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
                <div className="text-[11px] font-medium text-stone-400 uppercase tracking-widest mb-3 px-1 font-sans">Connection</div>
                <div className="bg-white border border-stone-200/80 rounded-2xl overflow-hidden shadow-[0_1px_8px_rgba(0,0,0,0.01)] select-none">
                  <div className="flex items-center justify-between p-3.5 border-b border-stone-100">
                    <div className="flex items-center gap-2.5">
                      <Wifi strokeWidth={1.5} className="w-4 h-4 text-stone-400" />
                      <span className="text-[13px] text-stone-600 font-normal font-sans">Backend latency</span>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <div className="w-1.5 h-1.5 rounded-full bg-emerald-400"></div>
                      <span className="text-[12px] font-mono text-stone-500">{networkPing}ms</span>
                    </div>
                  </div>
                  <div className="flex items-center justify-between p-3.5">
                    <div className="flex items-center gap-2.5">
                      <Cpu strokeWidth={1.5} className="w-4 h-4 text-stone-400" />
                      <span className="text-[13px] text-stone-600 font-normal font-sans">Agent runtime</span>
                    </div>
                    <span className="text-[12px] font-mono text-stone-400/80">stable</span>
                  </div>
                </div>
              </div>

              {/* Active Services Section */}
              <div>
                <div className="text-[11px] font-medium text-stone-400 uppercase tracking-widest mb-3 px-1 font-sans">Agent Services</div>
                <div className="bg-white border border-stone-200/80 rounded-2xl p-4 shadow-[0_1px_8px_rgba(0,0,0,0.01)] space-y-3.5">
                  {[
                    { name: "Repository index", desc: "Project files and symbols", active: true },
                    { name: "Command runner", desc: "Build, test, and verification tasks", active: true },
                    { name: "Patch reviewer", desc: "Available when changes are proposed", active: false },
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
