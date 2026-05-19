"use client"

import { useState, useEffect, useCallback, useMemo, useRef } from "react"
import { useSearchParams } from "next/navigation"
import { MessageSquareDashed, ArrowDownToLine, Activity, Database, GitBranch, Server, Timer, WifiOff, AlertTriangle, RotateCcw } from "lucide-react"
import { MessageList } from "./message-list"
import { Composer, type AIModel } from "./composer"
import { Button } from "@/components/ui/button"
import { LeftSidebar } from "./left-sidebar"
import { RightSidebar } from "./right-sidebar"

import { DiffViewer } from "./diff-viewer"
import { TerminalEmulator } from "./terminal-emulator"
import { cn } from "@/lib/utils"

// Backend URL — configurable via env var, defaults to localhost
const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "http://127.0.0.1:8000"
const WS_URL = BACKEND_URL.replace(/^http/, "ws")

// Data model for messages
export interface ToolStep {
  id: string
  name: string
  status: "running" | "done" | "error"
  description?: string
}

export interface TaskPlan {
  id: string
  title: string
  status: "pending" | "in_progress" | "done" | "error"
  subtasks?: TaskPlan[]
  estimatedTime?: string
}

export interface DebugAnalysis {
  errorType: string
  errorMessage: string
  filePath: string
  lineNumber: number
  rootCause: string
  suggestedFix: string
}

export interface Message {
  id: string
  role: "user" | "assistant"
  content: string
  createdAt: Date
  imageData?: string
  toolSteps?: ToolStep[]
  taskPlan?: TaskPlan[]  // Hierarchical task plan
  debugAnalysis?: DebugAnalysis  // Error analysis from debugger
  thinkingText?: string
}

export type AgentStatus = "idle" | "connecting" | "running" | "thinking" | "stabilizing" | "done" | "error" | "stopped"
export type PhaseStatus = "pending" | "running" | "done" | "error"

export interface AgentState {
  status: AgentStatus
  phase?: string
  message?: string
  startedAt?: string
  updatedAt?: string
  runtimeMs?: number
}

export interface AgentPhase {
  id: string
  label: string
  status: PhaseStatus
  description?: string
  startedAt?: string
  completedAt?: string
}

export interface ProjectIntelligence {
  status: "unknown" | "warming" | "ready" | "stale" | "error"
  workspacePath?: string
  filesIndexed?: number
  symbols?: number
  cacheHitRate?: number
  lastIndexedAt?: string
  summary?: string
}

export interface ToolActivity {
  id: string
  name: string
  status: "queued" | "running" | "done" | "error"
  message?: string
  target?: string
  startedAt?: string
  durationMs?: number
}

export interface ContextStatus {
  usedTokens?: number
  maxTokens?: number
  percent?: number
  status?: "healthy" | "compact" | "near_limit" | "overflow" | "unknown"
  cache?: "cold" | "warming" | "ready" | "stale"
}

export interface DiffStatus {
  filename?: string
  status: "none" | "proposed" | "accepted" | "rejected"
  filesChanged?: number
  additions?: number
  deletions?: number
}

export interface TestStatus {
  status: "idle" | "running" | "passed" | "failed"
  command?: string
  message?: string
  passed?: number
  failed?: number
  durationMs?: number
}

export interface RuntimeHint {
  id: string
  label: string
  value: string
  tone?: "neutral" | "good" | "warning" | "error"
}

const DEFAULT_PHASES: AgentPhase[] = [
  { id: "observe", label: "Observe", status: "pending", description: "Map workspace and request intent" },
  { id: "recall", label: "Recall", status: "pending", description: "Load project intelligence and cache" },
  { id: "reason", label: "Reason", status: "pending", description: "Plan edits and tool calls" },
  { id: "stabilize", label: "Stabilize", status: "pending", description: "Run checks and recover errors" },
  { id: "commit", label: "Finalize", status: "pending", description: "Prepare patch and summary" },
]

function normalizePhaseName(phase?: string) {
  return (phase || "").toString().toLowerCase().replace(/\s+/g, "_")
}

function formatDuration(ms?: number) {
  if (!ms || ms < 0) return "—"
  if (ms < 1000) return `${Math.round(ms)}ms`
  const seconds = Math.round(ms / 1000)
  if (seconds < 60) return `${seconds}s`
  return `${Math.floor(seconds / 60)}m ${seconds % 60}s`
}

function parseNumber(value: unknown): number | undefined {
  return typeof value === "number" && Number.isFinite(value) ? value : undefined
}

// localStorage key for persisting messages
const MODEL_STORAGE_KEY = "chat-selected-model"

// Generates a unique ID for messages
function generateId(): string {
  return `${Date.now()}-${Math.random().toString(36).substring(2, 9)}`
}

function AgentWorkspaceHeader({
  agentState,
  phases,
  projectIntelligence,
  contextStatus,
  selectedModel,
  backendConnected,
  backendUrl,
  runtimeHints,
  diffStatus,
  testStatus,
  onRetry,
  onReset,
}: {
  agentState: AgentState
  phases: AgentPhase[]
  projectIntelligence: ProjectIntelligence
  contextStatus: ContextStatus
  selectedModel: AIModel
  backendConnected: boolean
  backendUrl: string
  runtimeHints: RuntimeHint[]
  diffStatus: DiffStatus
  testStatus: TestStatus
  onRetry: () => void
  onReset: () => void
}) {
  const runningPhase = phases.find((phase) => phase.status === "running")
  const completedCount = phases.filter((phase) => phase.status === "done").length
  const contextPercent = contextStatus.percent ?? (contextStatus.usedTokens && contextStatus.maxTokens ? Math.round((contextStatus.usedTokens / contextStatus.maxTokens) * 100) : undefined)
  const stateTone = agentState.status === "error" ? "text-red-600 bg-red-50 border-red-100" : agentState.status === "done" ? "text-emerald-700 bg-emerald-50 border-emerald-100" : agentState.status === "running" || agentState.status === "thinking" || agentState.status === "stabilizing" ? "text-stone-800 bg-white border-stone-200" : "text-stone-500 bg-stone-50 border-stone-200"

  return (
    <div className="absolute top-4 left-16 right-4 z-10 pointer-events-none">
      <div className="max-w-4xl mx-auto pointer-events-auto rounded-2xl border border-stone-200/70 bg-white/90 backdrop-blur-xl shadow-[0_8px_30px_rgba(0,0,0,0.045)] px-4 py-3">
        <div className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-3 min-w-0">
            <div className={cn("h-8 w-8 rounded-full border flex items-center justify-center shrink-0", stateTone)}>
              {backendConnected ? <Activity size={15} strokeWidth={1.5} className={cn((agentState.status === "running" || agentState.status === "thinking") && "animate-pulse")} /> : <WifiOff size={15} strokeWidth={1.5} />}
            </div>
            <div className="min-w-0">
              <div className="flex items-center gap-2 min-w-0">
                <span className="text-[13px] font-semibold text-stone-850 tracking-tight truncate">{agentState.message || (runningPhase ? `${runningPhase.label} in progress` : "Workspace ready")}</span>
                <span className="text-[10px] font-medium text-stone-400 uppercase tracking-wider shrink-0">{agentState.status}</span>
              </div>
              <div className="flex items-center gap-2 mt-1 text-[11px] text-stone-400 min-w-0">
                <Server size={12} strokeWidth={1.5} className="shrink-0" />
                <span className="truncate">{backendConnected ? backendUrl.replace(/^https?:\/\//, "") : "backend disconnected"}</span>
                <span className="text-stone-300">•</span>
                <span className="truncate">{selectedModel}</span>
              </div>
            </div>
          </div>

          <div className="hidden xl:flex items-center gap-2 shrink-0">
            <div className="px-2.5 py-1.5 rounded-xl bg-stone-50 border border-stone-200/70 flex items-center gap-2">
              <Database size={13} strokeWidth={1.5} className="text-stone-400" />
              <span className="text-[11px] text-stone-500">{projectIntelligence.status}</span>
              {typeof projectIntelligence.filesIndexed === "number" && <span className="text-[11px] font-mono text-stone-400">{projectIntelligence.filesIndexed} files</span>}
            </div>
            <div className="px-2.5 py-1.5 rounded-xl bg-stone-50 border border-stone-200/70 flex items-center gap-2">
              <Timer size={13} strokeWidth={1.5} className="text-stone-400" />
              <span className="text-[11px] text-stone-500">{formatDuration(agentState.runtimeMs)}</span>
            </div>
            {(diffStatus.status !== "none" || testStatus.status !== "idle") && (
              <div className="px-2.5 py-1.5 rounded-xl bg-stone-50 border border-stone-200/70 flex items-center gap-2">
                <GitBranch size={13} strokeWidth={1.5} className="text-stone-400" />
                <span className="text-[11px] text-stone-500">{diffStatus.status !== "none" ? `${diffStatus.filesChanged ?? 0} files` : "no diff"}</span>
                <span className={cn("text-[11px]", testStatus.status === "passed" ? "text-emerald-600" : testStatus.status === "failed" ? "text-red-600" : "text-stone-400")}>{testStatus.status}</span>
              </div>
            )}
          </div>

          <div className="flex items-center gap-1.5 shrink-0">
            <button onClick={onRetry} className="h-7 px-2.5 rounded-lg hover:bg-stone-100 text-[11px] text-stone-500 transition-colors flex items-center gap-1.5">
              <RotateCcw size={12} strokeWidth={1.5} />
              Retry
            </button>
            <button onClick={onReset} className="h-7 px-2.5 rounded-lg hover:bg-stone-100 text-[11px] text-stone-500 transition-colors">Reset</button>
          </div>
        </div>

        <div className="mt-3 flex items-center gap-2">
          {phases.map((phase, index) => (
            <div key={phase.id} className="flex items-center gap-2 flex-1 min-w-0">
              <div className={cn("h-1.5 flex-1 rounded-full transition-colors", phase.status === "done" ? "bg-stone-800" : phase.status === "running" ? "bg-stone-400 animate-pulse" : phase.status === "error" ? "bg-red-300" : "bg-stone-100")} />
              {index < phases.length - 1 && <span className="text-stone-200 text-[10px]">/</span>}
            </div>
          ))}
          <span className="text-[10px] font-mono text-stone-400 shrink-0">{completedCount}/{phases.length}</span>
        </div>

        {(contextPercent !== undefined || runtimeHints.length > 0 || agentState.status === "error") && (
          <div className="mt-2 flex items-center gap-3 text-[11px] text-stone-400 overflow-hidden">
            {contextPercent !== undefined && <span className="shrink-0">context {contextPercent}% · cache {contextStatus.cache || projectIntelligence.status}</span>}
            {runtimeHints.slice(0, 2).map((hint) => <span key={hint.id} className={cn("truncate", hint.tone === "warning" && "text-amber-600", hint.tone === "error" && "text-red-600", hint.tone === "good" && "text-emerald-600")}>{hint.label}: {hint.value}</span>)}
            {agentState.status === "error" && <span className="flex items-center gap-1 text-red-600 shrink-0"><AlertTriangle size={12} strokeWidth={1.5} /> recoverable</span>}
          </div>
        )}
      </div>
    </div>
  )
}

export function ChatShell() {
  const searchParams = useSearchParams()
  const activeSessionId = searchParams?.get("session") || "session-1"
  const STORAGE_KEY = `sharrowkin-session-messages-${activeSessionId}`

  const [messages, setMessages] = useState<Message[]>([])
  const [isStreaming, setIsStreaming] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const socketRef = useRef<WebSocket | null>(null)
  const startedAtRef = useRef<number | null>(null)
  const [selectedModel, setSelectedModel] = useState<AIModel>("google/gemini-2.5-flash")
  const [isLoaded, setIsLoaded] = useState(false)
  const [leftSidebarOpen, setLeftSidebarOpen] = useState(true)
  const [rightSidebarOpen, setRightSidebarOpen] = useState(true)
  const [activeDiffFile, setActiveDiffFile] = useState<string | null>(null)
  const [lastDiffContent, setLastDiffContent] = useState("")
  const [agentState, setAgentState] = useState<AgentState>({ status: "idle", message: "Workspace ready" })
  const [agentPhases, setAgentPhases] = useState<AgentPhase[]>(DEFAULT_PHASES)
  const [projectIntelligence, setProjectIntelligence] = useState<ProjectIntelligence>({ status: "unknown" })
  const [toolActivity, setToolActivity] = useState<ToolActivity[]>([])
  const [contextStatus, setContextStatus] = useState<ContextStatus>({ status: "unknown", cache: "cold" })
  const [runtimeHints, setRuntimeHints] = useState<RuntimeHint[]>([])
  const [diffStatus, setDiffStatus] = useState<DiffStatus>({ status: "none" })
  const [testStatus, setTestStatus] = useState<TestStatus>({ status: "idle" })

  const backendConnected = agentState.status !== "error" || !error

  const workspacePath = useMemo(() => projectIntelligence.workspacePath || "active workspace", [projectIntelligence.workspacePath])

  // --- LIFTED TERMINAL EMULATOR STATE ---
  const [terminalLines, setTerminalLines] = useState<string[]>([
    "sharrowkin-core ~ bash",
    "$ agent start --mode=autonomous",
    "[INFO] Initializing workspace...",
    "[INFO] Loading memory buffers (DSM)...",
    "[INFO] Connecting to language model...",
    "→ System ready. Awaiting input.",
  ])
  const [isRunningTask, setIsRunningTask] = useState(false)
  const [currentInput, setCurrentInput] = useState("")
  const [terminalDock, setTerminalDock] = useState<"sidebar" | "bottom">("sidebar")
  const [isDraggingTerminal, setIsDraggingTerminal] = useState(false)
  const [terminalHeight, setTerminalHeight] = useState(250)
  const [isResizingTerminal, setIsResizingTerminal] = useState(false)

  // Run a real command via the backend terminal API
  const runRealCommand = useCallback(async (cmd: string) => {
    if (isRunningTask) return
    setIsRunningTask(true)
    setTerminalLines((prev) => [...prev, "", `$ ${cmd}`])
    try {
      const response = await fetch(`${BACKEND_URL}/api/terminal`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ command: cmd }),
      })
      const data = await response.json()
      if (data.output && Array.isArray(data.output)) {
        setTerminalLines((prev) => [...prev, ...data.output])
      }
    } catch (err: any) {
      setTerminalLines((prev) => [...prev, `error: ${err.message}`])
    } finally {
      setIsRunningTask(false)
    }
  }, [isRunningTask])

  const runBuildCommand = useCallback(() => {
    runRealCommand("npm run build")
  }, [runRealCommand])

  const runTestCommand = useCallback(() => {
    runRealCommand("npm test")
  }, [runRealCommand])

  const clearTerminal = useCallback(() => {
    setTerminalLines(["sharrowkin-core ~ bash", "$ cleared console", "→ System ready. Awaiting input."])
  }, [])

  const handleCommandSubmit = useCallback(async (e: React.FormEvent) => {
    e.preventDefault()
    if (!currentInput.trim() || isRunningTask) return

    const cmd = currentInput.trim()
    setTerminalLines((prev) => [...prev, `$ ${cmd}`])
    setCurrentInput("")

    const normalizedCmd = cmd.toLowerCase()

    if (normalizedCmd === "clear") {
      clearTerminal()
      return
    }

    setIsRunningTask(true)

    try {
      const response = await fetch(`${BACKEND_URL}/api/terminal`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ command: cmd }),
      })

      if (!response.ok) {
        throw new Error("Failed to communicate with NARE-Field backend.")
      }

      const data = await response.json()
      if (data.output && Array.isArray(data.output)) {
        setTerminalLines((prev) => [...prev, ...data.output])
      }
    } catch (err: any) {
      setTerminalLines((prev) => [
        ...prev,
        `bash: command failed: ${cmd}`,
        `error: ${err.message}`
      ])
    } finally {
      setIsRunningTask(false)
    }
  }, [currentInput, isRunningTask, clearTerminal, runBuildCommand, runTestCommand])

  const handleDragStart = useCallback((e: React.DragEvent) => {
    setIsDraggingTerminal(true)
    if (e.dataTransfer) {
      e.dataTransfer.setData("text/plain", "terminal")
      e.dataTransfer.effectAllowed = "move"
    }
  }, [])

  const handleDragEnd = useCallback(() => {
    setIsDraggingTerminal(false)
  }, [])

  // Safe global drag end reset
  useEffect(() => {
    const handleGlobalDragEnd = () => {
      setIsDraggingTerminal(false)
    }
    window.addEventListener("dragend", handleGlobalDragEnd)
    window.addEventListener("drop", handleGlobalDragEnd)
    return () => {
      window.removeEventListener("dragend", handleGlobalDragEnd)
      window.removeEventListener("drop", handleGlobalDragEnd)
    }
  }, [])

  const handleTerminalResizeStart = useCallback((e: React.MouseEvent) => {
    e.preventDefault()
    setIsResizingTerminal(true)
    const startY = e.clientY
    const startHeight = terminalHeight

    const doDrag = (moveEvent: MouseEvent) => {
      const deltaY = startY - moveEvent.clientY // drag up increases height
      const nextHeight = Math.max(160, Math.min(startHeight + deltaY, 480))
      setTerminalHeight(nextHeight)
    }

    const stopDrag = () => {
      setIsResizingTerminal(false)
      document.removeEventListener("mousemove", doDrag)
      document.removeEventListener("mouseup", stopDrag)
    }

    document.addEventListener("mousemove", doDrag)
    document.addEventListener("mouseup", stopDrag)
  }, [terminalHeight])

  // Load messages from localStorage on mount and when active session changes
  useEffect(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY)
      if (stored) {
        const parsed = JSON.parse(stored)
        const messagesWithDates = parsed.map((msg: Message) => ({
          ...msg,
          createdAt: new Date(msg.createdAt),
        }))
        setMessages(messagesWithDates)
      } else {
        // Clean welcome for new sessions
        let defaultMessages: Message[] = []
        setMessages(defaultMessages)
      }
      const savedModel = localStorage.getItem(MODEL_STORAGE_KEY) as AIModel | null
      if (savedModel) {
        setSelectedModel(savedModel)
      }
    } catch (e) {
      console.error("Failed to load from localStorage:", e)
    } finally {
      setIsLoaded(true)
    }
  }, [activeSessionId, STORAGE_KEY])

  // Persist messages to localStorage whenever they change
  useEffect(() => {
    if (!isLoaded) return
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(messages))
    } catch (e) {
      console.error("Failed to save messages to localStorage:", e)
    }
  }, [messages, STORAGE_KEY, isLoaded])

  const handleModelChange = useCallback((model: AIModel) => {
    setSelectedModel(model)
    localStorage.setItem(MODEL_STORAGE_KEY, model)
  }, [])

  const resetAgentWorkspace = useCallback(() => {
    socketRef.current?.close()
    socketRef.current = null
    startedAtRef.current = null
    setIsStreaming(false)
    setError(null)
    setAgentState({ status: "idle", message: "Workspace ready" })
    setAgentPhases(DEFAULT_PHASES)
    setToolActivity([])
    setContextStatus({ status: "unknown", cache: projectIntelligence.status === "ready" ? "ready" : "cold" })
    setRuntimeHints([])
    setDiffStatus({ status: "none" })
    setTestStatus({ status: "idle" })
  }, [projectIntelligence.status])

  const setPhaseStatus = useCallback((phase: string, status: PhaseStatus, description?: string) => {
    const normalized = normalizePhaseName(phase)
    const phaseIndex = DEFAULT_PHASES.findIndex((item) => item.id === normalized)
    const now = new Date().toISOString()

    setAgentPhases((prev) => {
      const source = prev.length ? prev : DEFAULT_PHASES
      return source.map((item, index) => {
        if (phaseIndex >= 0) {
          if (index < phaseIndex) return { ...item, status: item.status === "error" ? "error" : "done", completedAt: item.completedAt || now }
          if (index === phaseIndex) return { ...item, status, description: description || item.description, startedAt: item.startedAt || now, completedAt: status === "done" ? now : item.completedAt }
          return status === "error" && index === phaseIndex ? { ...item, status: "error" } : item
        }
        if (item.id === normalized) return { ...item, status, description: description || item.description, startedAt: item.startedAt || now }
        return item
      })
    })
  }, [])

  const appendToolActivity = useCallback((activity: Omit<ToolActivity, "id" | "startedAt"> & { id?: string; startedAt?: string }) => {
    const entry: ToolActivity = {
      ...activity,
      id: activity.id || generateId(),
      startedAt: activity.startedAt || new Date().toISOString(),
    }
    setToolActivity((prev) => [entry, ...prev.filter((item) => item.id !== entry.id)].slice(0, 40))
  }, [])

  // Send a message to the AI
  const sendMessage = useCallback(
    async (content: string, imageData?: string) => {
      if ((!content.trim() && !imageData) || isStreaming) return

      setError(null)

      const userMessage: Message = {
        id: generateId(),
        role: "user",
        content: content.trim() || "Describe this image",
        createdAt: new Date(),
        imageData,
      }

      const assistantMessage: Message = {
        id: generateId(),
        role: "assistant",
        content: "",
        createdAt: new Date(),
        toolSteps: [
          { id: "step-1", name: "Recalling memory context (DSM)", status: "running", description: "Querying Dynamic Segmented Memory server..." }
        ]
      }

      const newMessages = [...messages, userMessage, assistantMessage]
      setMessages(newMessages)
      setIsStreaming(true)
      startedAtRef.current = Date.now()
      setAgentState({ status: "connecting", phase: "connect", message: "Connecting to autonomous backend", startedAt: new Date().toISOString() })
      setAgentPhases(DEFAULT_PHASES)
      setToolActivity([])
      setRuntimeHints([{ id: "model", label: "model", value: selectedModel, tone: "neutral" }])
      setDiffStatus({ status: "none" })
      setTestStatus({ status: "idle" })
      appendToolActivity({ name: "Open agent websocket", status: "running", message: "Negotiating live workspace channel" })

      // --- REAL STREAMING VIA WEBSOCKET TO BACKEND AGENT ---
      let currentSteps: ToolStep[] = [
        { id: "step-1", name: "Recalling memory context (DSM)", status: "running", description: "Querying Dynamic Segmented Memory server..." }
      ];

      const updateSteps = (newSteps: ToolStep[]) => {
        currentSteps = newSteps;
        setMessages(prev => prev.map(msg => {
          if (msg.id === assistantMessage.id) {
            return { ...msg, toolSteps: newSteps };
          }
          return msg;
        }));
      };

      const updateContent = (chunk: string) => {
        setMessages(prev => prev.map(msg => {
          if (msg.id === assistantMessage.id) {
            return { ...msg, content: msg.content + chunk };
          }
          return msg;
        }));
      };

      // Fetch via WebSocket to our autonomous agent backend!
      try {
        socketRef.current?.close()
        const ws = new WebSocket(`${WS_URL}/ws/agent`)
        socketRef.current = ws
        
        ws.onopen = () => {
          ws.send(JSON.stringify({
            task: content.trim(),
            workspace_path: "",
            model: selectedModel,
          }))
          
          updateSteps([
            { id: "observe", name: "Observe (AST Workspace Analysis)", status: "running", description: "Scanning active project files..." }
          ])
          setAgentState({ status: "running", phase: "observe", message: "Observing workspace", startedAt: new Date(startedAtRef.current || Date.now()).toISOString(), updatedAt: new Date().toISOString() })
          setPhaseStatus("observe", "running", "Scanning active project files")
          appendToolActivity({ name: "Autonomous run", status: "running", message: content.trim(), target: workspacePath })
          setProjectIntelligence((prev) => ({ ...prev, status: prev.status === "ready" ? "ready" : "warming" }))
          setTerminalLines(prev => [...prev, "", `[AGENT] Task started: "${content.trim()}"`])
        }
        
        let fullResponse = ""
        
        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data)
            
            if (data.type === "phase_change") {
              // Update tool steps based on phase
              const phaseNames: Record<string, string> = {
                observe: "Observe (AST Analysis)",
                recall: "Recall (Memory Retrieval)",
                reason: "Reason (Patch Generation)",
                stabilize: "Stabilize (Test Verification)",
                commit: "Commit (Evolutionary DNA Update)"
              }
              
              const currentPhaseKey = data.phase
              const newSteps: ToolStep[] = []
              const allKeys = ["observe", "recall", "reason", "stabilize", "commit"]
              
              for (const key of allKeys) {
                if (key === currentPhaseKey) {
                  newSteps.push({ id: key, name: phaseNames[key], status: "running", description: "Active cognitive phase..." })
                } else if (allKeys.indexOf(key) < allKeys.indexOf(currentPhaseKey)) {
                  newSteps.push({ id: key, name: phaseNames[key], status: "done", description: "Completed." })
                }
              }
              updateSteps(newSteps)
              setAgentState((prev) => ({ ...prev, status: currentPhaseKey === "stabilize" ? "stabilizing" : "running", phase: currentPhaseKey, message: `${phaseNames[currentPhaseKey] || currentPhaseKey} active`, updatedAt: new Date().toISOString(), runtimeMs: startedAtRef.current ? Date.now() - startedAtRef.current : prev.runtimeMs }))
              setPhaseStatus(currentPhaseKey, "running", data.message || "Active cognitive phase")
              appendToolActivity({ name: phaseNames[currentPhaseKey] || currentPhaseKey, status: "running", message: data.message || "Phase transition" })
              setTerminalLines(prev => [...prev, `➔ Transitioned to phase: ${data.phase.toUpperCase()}`])
              
            } else if (data.type === "thinking") {
              // Show agent's thinking/reasoning in the chat
              const thinkingText = data.content || ""
              setMessages(prev => prev.map(msg => {
                if (msg.id === assistantMessage.id) {
                  return { ...msg, thinkingText: msg.thinkingText ? msg.thinkingText + "\n" + thinkingText : thinkingText }
                }
                return msg
              }))
              setAgentState((prev) => ({ ...prev, status: "thinking", message: thinkingText.slice(0, 120) || "Reasoning", updatedAt: new Date().toISOString(), runtimeMs: startedAtRef.current ? Date.now() - startedAtRef.current : prev.runtimeMs }))
              appendToolActivity({ name: "Reasoning", status: "running", message: thinkingText.slice(0, 180) })
              setTerminalLines(prev => [...prev, `💭 ${thinkingText}`])

            } else if (data.type === "task_plan") {
              // Hierarchical task plan from planner
              const plan = data.plan || []
              setMessages(prev => prev.map(msg => {
                if (msg.id === assistantMessage.id) {
                  return { ...msg, taskPlan: plan }
                }
                return msg
              }))
              appendToolActivity({ name: "Execution plan", status: "done", message: `${plan.length} top-level tasks` })
              setTerminalLines(prev => [...prev, `📋 Execution plan generated: ${plan.length} top-level tasks`])

            } else if (data.type === "task_update") {
              // Update task status in plan
              const taskId = data.task_id
              const newStatus = data.status

              const updateTaskStatus = (tasks: TaskPlan[]): TaskPlan[] => {
                return tasks.map(task => {
                  if (task.id === taskId) {
                    return { ...task, status: newStatus }
                  }
                  if (task.subtasks) {
                    return { ...task, subtasks: updateTaskStatus(task.subtasks) }
                  }
                  return task
                })
              }

              setMessages(prev => prev.map(msg => {
                if (msg.id === assistantMessage.id && msg.taskPlan) {
                  return { ...msg, taskPlan: updateTaskStatus(msg.taskPlan) }
                }
                return msg
              }))

            } else if (data.type === "log") {
              appendToolActivity({ name: data.tag || data.level || "log", status: data.level === "error" ? "error" : "done", message: data.message })
              setTerminalLines(prev => [...prev, `[${data.level?.toUpperCase() || 'INFO'}] ${data.message}`])

            } else if (data.type === "debug_analysis") {
              // Intelligent error analysis from debugger
              const debugInfo = {
                errorType: data.error_type || "Unknown",
                errorMessage: data.error_message || "",
                filePath: data.file_path || "",
                lineNumber: data.line_number || 0,
                rootCause: data.root_cause || "",
                suggestedFix: data.suggested_fix || ""
              }

              // Add debug analysis to message
              setMessages(prev => prev.map(msg => {
                if (msg.id === assistantMessage.id) {
                  return { ...msg, debugAnalysis: debugInfo }
                }
                return msg
              }))

              setAgentState((prev) => ({ ...prev, status: "error", message: debugInfo.errorMessage || debugInfo.errorType, updatedAt: new Date().toISOString(), runtimeMs: startedAtRef.current ? Date.now() - startedAtRef.current : prev.runtimeMs }))
              appendToolActivity({ name: "Recoverable error", status: "error", message: debugInfo.rootCause || debugInfo.errorMessage, target: debugInfo.filePath })
              setTerminalLines(prev => [
                ...prev,
                `🐛 Error Analysis: ${debugInfo.errorType}`,
                `   Root cause: ${debugInfo.rootCause}`,
                `   Suggested fix: ${debugInfo.suggestedFix}`
              ])

            } else if (data.type === "diff" || data.type === "patch_proposed") {
              const diffText = data.diff || ""
              const additions = diffText.split("\n").filter((line: string) => line.startsWith("+") && !line.startsWith("+++")).length
              const deletions = diffText.split("\n").filter((line: string) => line.startsWith("-") && !line.startsWith("---")).length
              const filesChanged = Array.isArray(data.files) ? data.files.length : undefined
              setLastDiffContent(diffText)
              setDiffStatus({ filename: "agent-patch.diff", status: "proposed", filesChanged, additions, deletions })
              appendToolActivity({ name: "Patch proposed", status: "done", message: `${filesChanged ?? 0} file(s), +${additions}/-${deletions}` })
              setTerminalLines(prev => [...prev, `✔ Patch generated: ${(data.files || []).length} file(s) changed`])
              if (diffText) {
                setTerminalLines(prev => [...prev, ...diffText.split("\n").slice(0, 30)])
              }
              // Store diff content and trigger diff viewer
              setActiveDiffFile("agent-patch.diff")
              
            } else if (data.type === "test_result") {
              const passed = data.success === true
              setTestStatus({ status: passed ? "passed" : "failed", command: data.command, message: data.message, passed: parseNumber(data.passed), failed: parseNumber(data.failed), durationMs: parseNumber(data.duration_ms ?? data.durationMs) })
              appendToolActivity({ name: "Test verification", status: passed ? "done" : "error", message: data.message || `Success: ${data.success}` })
              setTerminalLines(prev => [
                ...prev, 
                `[TEST] Run complete. Success: ${data.success}`,
              ])
              
            } else if (data.type === "agent_state") {
              setAgentState((prev) => ({
                ...prev,
                status: data.status || prev.status,
                phase: data.phase || prev.phase,
                message: data.message || data.detail || prev.message,
                updatedAt: data.updated_at || new Date().toISOString(),
                runtimeMs: parseNumber(data.runtime_ms ?? data.runtimeMs) ?? (startedAtRef.current ? Date.now() - startedAtRef.current : prev.runtimeMs),
              }))
              if (data.phase) setPhaseStatus(data.phase, data.status === "error" ? "error" : data.status === "done" ? "done" : "running", data.message)

            } else if (data.type === "project_intelligence") {
              setProjectIntelligence((prev) => ({
                ...prev,
                status: data.status || prev.status || "unknown",
                workspacePath: data.workspace_path || data.workspacePath || prev.workspacePath,
                filesIndexed: parseNumber(data.files_indexed ?? data.filesIndexed) ?? prev.filesIndexed,
                symbols: parseNumber(data.symbols) ?? prev.symbols,
                cacheHitRate: parseNumber(data.cache_hit_rate ?? data.cacheHitRate) ?? prev.cacheHitRate,
                lastIndexedAt: data.last_indexed_at || data.lastIndexedAt || prev.lastIndexedAt,
                summary: data.summary || prev.summary,
              }))
              appendToolActivity({ name: "Project intelligence", status: data.status === "error" ? "error" : "done", message: data.summary || data.status })

            } else if (data.type === "tool_activity") {
              appendToolActivity({
                id: data.id,
                name: data.name || data.tool || "Tool activity",
                status: data.status || "running",
                message: data.message || data.detail,
                target: data.target || data.path,
                durationMs: parseNumber(data.duration_ms ?? data.durationMs),
              })

            } else if (data.type === "context_status") {
              setContextStatus({
                usedTokens: parseNumber(data.used_tokens ?? data.usedTokens),
                maxTokens: parseNumber(data.max_tokens ?? data.maxTokens),
                percent: parseNumber(data.percent ?? data.percentage),
                status: data.status || "unknown",
                cache: data.cache,
              })

            } else if (data.type === "runtime_hint" || data.type === "performance_hint") {
              const hint: RuntimeHint = { id: data.id || generateId(), label: data.label || data.name || "hint", value: String(data.value || data.message || ""), tone: data.tone || "neutral" }
              setRuntimeHints((prev) => [hint, ...prev.filter((item) => item.id !== hint.id)].slice(0, 6))

            } else if (data.type === "content") {
              // Direct content from agent (e.g. conversational reply)
              fullResponse += data.content || ""
              updateContent(data.content || "")
              
            } else if (data.type === "status") {
              if (data.status === "done") {
                updateSteps(currentSteps.map(s => ({ ...s, status: "done", description: "Finished." })))
                setAgentPhases((prev) => prev.map((phase) => ({ ...phase, status: phase.status === "error" ? "error" : "done", completedAt: phase.completedAt || new Date().toISOString() })))
                setAgentState((prev) => ({ ...prev, status: "done", message: "Autonomous run complete", updatedAt: new Date().toISOString(), runtimeMs: startedAtRef.current ? Date.now() - startedAtRef.current : prev.runtimeMs }))
                appendToolActivity({ name: "Autonomous run", status: "done", message: "Complete" })
                setIsStreaming(false)
                setTerminalLines(prev => [...prev, `✔ Autonomous run complete.`])
                ws.close()
              } else if (data.status === "error" || data.status === "needs_key") {
                updateSteps(currentSteps.map(s => s.status === "running" ? { ...s, status: "error", description: data.status === "needs_key" ? "API key required" : "Error" } : s))
                setAgentState((prev) => ({ ...prev, status: "error", message: data.status === "needs_key" ? "API key required" : "Agent run needs attention", updatedAt: new Date().toISOString(), runtimeMs: startedAtRef.current ? Date.now() - startedAtRef.current : prev.runtimeMs }))
                setPhaseStatus(agentState.phase || "reason", "error", data.status)
                appendToolActivity({ name: "Agent status", status: "error", message: data.status })
                setIsStreaming(false)
                setTerminalLines(prev => [...prev, `✖ Status: ${data.status}`])
                ws.close()
              }
              
            } else if (data.type === "error") {
              updateSteps(currentSteps.map(s => s.status === "running" ? { ...s, status: "error", description: data.message } : s))
              setError(data.message)
              setAgentState((prev) => ({ ...prev, status: "error", message: data.message || "Agent error", updatedAt: new Date().toISOString(), runtimeMs: startedAtRef.current ? Date.now() - startedAtRef.current : prev.runtimeMs }))
              setPhaseStatus(agentState.phase || "reason", "error", data.message)
              appendToolActivity({ name: "Agent error", status: "error", message: data.message })
              setIsStreaming(false)
              setTerminalLines(prev => [...prev, `✖ Error: ${data.message}`])
              ws.close()
            }
          } catch (e) {
            console.error(e)
          }
        }
        
        ws.onerror = () => {
          setError("WebSocket error. Could not connect to backend.")
          setAgentState((prev) => ({ ...prev, status: "error", message: "Backend websocket unavailable", updatedAt: new Date().toISOString(), runtimeMs: startedAtRef.current ? Date.now() - startedAtRef.current : prev.runtimeMs }))
          appendToolActivity({ name: "WebSocket", status: "error", message: "Could not connect to backend" })
          setIsStreaming(false)
        }
        
        ws.onclose = () => {
          if (socketRef.current === ws) socketRef.current = null
          setIsStreaming(false)
        }
        
      } catch (err: any) {
        console.error(err)
        setError(err.message)
        setAgentState((prev) => ({ ...prev, status: "error", message: err.message || "Connection error", updatedAt: new Date().toISOString(), runtimeMs: startedAtRef.current ? Date.now() - startedAtRef.current : prev.runtimeMs }))
        updateSteps([
          { id: "step-1", name: "Connection Error", status: "error", description: "Could not connect to Python backend. Is it running?" }
        ])
        appendToolActivity({ name: "Connection error", status: "error", message: "Could not connect to Python backend" })
        setIsStreaming(false)
      }
    },
    [messages, isStreaming, selectedModel, appendToolActivity, setPhaseStatus, workspacePath, agentState.phase],
  )

  const retry = useCallback(() => {
    if (messages.length === 0) return
    const lastUserMessage = [...messages].reverse().find((m) => m.role === "user")
    if (lastUserMessage) {
      const index = messages.findIndex((m) => m.id === lastUserMessage.id)
      setMessages(messages.slice(0, index))
      setError(null)
      setTimeout(() => sendMessage(lastUserMessage.content, lastUserMessage.imageData), 100)
    }
  }, [messages, sendMessage])

  const stopStreaming = useCallback(() => {
    socketRef.current?.close()
    socketRef.current = null
    setAgentState((prev) => ({ ...prev, status: "stopped", message: "Run stopped by user", updatedAt: new Date().toISOString(), runtimeMs: startedAtRef.current ? Date.now() - startedAtRef.current : prev.runtimeMs }))
    appendToolActivity({ name: "Run stopped", status: "done", message: "Stopped by user" })
    setIsStreaming(false)
  }, [appendToolActivity])

  const clearChat = useCallback(() => {
    setMessages([])
    setError(null)
    resetAgentWorkspace()
    localStorage.removeItem(STORAGE_KEY)
  }, [STORAGE_KEY, resetAgentWorkspace])

  return (
    <div className="h-dvh bg-background flex overflow-hidden">
      {/* Left Sidebar */}
      <LeftSidebar isOpen={leftSidebarOpen} onToggle={() => setLeftSidebarOpen(!leftSidebarOpen)} />

      {/* Main Workspace split */}
      <div className="flex-1 flex overflow-hidden relative">
        
        {/* Main Chat Area - Center */}
        <div className={cn("flex-1 flex flex-col relative min-w-0 transition-all duration-300", activeDiffFile ? "max-w-[50%]" : "max-w-full")}>
          <Button
            onClick={clearChat}
            variant="ghost"
            size="icon"
            className="absolute top-4 left-4 z-20 h-9 w-9 rounded-xl bg-white/80 backdrop-blur-sm hover:bg-stone-100 text-stone-500 hover:text-stone-700 border border-stone-200/50 shadow-sm transition-all"
            aria-label="Reset chat"
          >
            <MessageSquareDashed className="w-4 h-4" />
          </Button>

          <AgentWorkspaceHeader
            agentState={agentState}
            phases={agentPhases}
            projectIntelligence={projectIntelligence}
            contextStatus={contextStatus}
            selectedModel={selectedModel}
            backendConnected={backendConnected}
            backendUrl={BACKEND_URL}
            runtimeHints={runtimeHints}
            diffStatus={diffStatus}
            testStatus={testStatus}
            onRetry={retry}
            onReset={clearChat}
          />

          <div className="flex-1 overflow-hidden">
            <MessageList 
              messages={messages} 
              isStreaming={isStreaming} 
              error={error} 
              onRetry={retry} 
              isLoaded={isLoaded} 
              onOpenDiff={setActiveDiffFile}
            />
          </div>

          {/* Bottom Terminal Drag Drop Zone */}
          {isDraggingTerminal && terminalDock === "sidebar" && (
            <div 
              onDragOver={(e) => {
                e.preventDefault()
                e.dataTransfer.dropEffect = "move"
              }}
              onDrop={() => {
                setTerminalDock("bottom")
                setIsDraggingTerminal(false)
              }}
              className="mx-6 my-3 h-[180px] border-2 border-dashed border-emerald-400/60 bg-emerald-50/10 rounded-2xl flex flex-col items-center justify-center gap-2.5 cursor-pointer transition-all hover:border-emerald-500 hover:bg-emerald-50/20 animate-pulse shrink-0"
            >
              <div className="w-10 h-10 rounded-full bg-emerald-50 border border-emerald-100 flex items-center justify-center text-emerald-600 shadow-sm mb-1">
                <ArrowDownToLine size={18} strokeWidth={1.5} className="animate-bounce" />
              </div>
              <h4 className="text-[13px] font-medium text-emerald-800 font-sans">Drop here to Dock Terminal</h4>
              <p className="text-[11px] text-emerald-500/70 font-sans max-w-[240px] text-center leading-relaxed">
                Release your drag here to snap the terminal panel horizontally below the chat.
              </p>
            </div>
          )}

          {/* Bottom terminal dock */}
          {terminalDock === "bottom" && (
            <div 
              style={{ height: `${terminalHeight}px` }}
              className={cn(
                "border-t border-stone-200/60 bg-white px-6 pb-4 pt-5 shrink-0 relative flex flex-col min-h-0",
                isResizingTerminal ? "transition-none" : "transition-all duration-300 ease-in-out"
              )}
            >
              {/* Apple style horizontal resize bar on top edge */}
              <div 
                onMouseDown={handleTerminalResizeStart}
                className="absolute top-0 left-0 w-full h-1.5 cursor-row-resize hover:bg-stone-200/50 active:bg-stone-350/60 transition-colors z-50 flex items-center justify-center group"
                title="Drag top edge to resize terminal height"
              >
                <div className="h-[1.5px] w-12 bg-stone-200/40 group-hover:bg-stone-400/60 group-active:bg-stone-500 rounded-full transition-colors" />
              </div>

              <div className="flex-1 min-h-0 pt-1">
                <TerminalEmulator
                  terminalLines={terminalLines}
                  isRunningTask={isRunningTask}
                  currentInput={currentInput}
                  setCurrentInput={setCurrentInput}
                  onSubmitCommand={handleCommandSubmit}
                  runBuildCommand={runBuildCommand}
                  runTestCommand={runTestCommand}
                  clearTerminal={clearTerminal}
                  terminalDock={terminalDock}
                  setTerminalDock={setTerminalDock}
                  onDragStart={handleDragStart}
                  onDragEnd={handleDragEnd}
                />
              </div>
            </div>
          )}

          <div className="flex-shrink-0 border-t border-stone-200/60">
            <Composer
              onSend={sendMessage}
              onStop={stopStreaming}
              isStreaming={isStreaming}
              disabled={!!error}
              selectedModel={selectedModel}
              onModelChange={handleModelChange}
              bottomOffset={terminalDock === "bottom" ? (terminalHeight + 24) : (isDraggingTerminal && terminalDock === "sidebar") ? 204 : 24}
            />
          </div>
        </div>

        {/* Diff Viewer panel */}
        {activeDiffFile && (
          <div className="w-1/2 border-l border-stone-200/60 bg-white flex flex-col overflow-hidden animate-in slide-in-from-right duration-300">
            <DiffViewer
              filename={activeDiffFile}
              diffContent={lastDiffContent}
              onClose={() => setActiveDiffFile(null)}
              onAccept={() => {
                setDiffStatus((prev) => ({ ...prev, status: "accepted" }))
                setActiveDiffFile(null)
              }}
            />
          </div>
        )}
      </div>

      {/* Right Sidebar with Terminal/Logs/Info */}
      <RightSidebar 
        isOpen={rightSidebarOpen} 
        onToggle={() => setRightSidebarOpen(!rightSidebarOpen)} 
        terminalLines={terminalLines}
        isRunningTask={isRunningTask}
        currentInput={currentInput}
        setCurrentInput={setCurrentInput}
        onSubmitCommand={handleCommandSubmit}
        runBuildCommand={runBuildCommand}
        runTestCommand={runTestCommand}
        clearTerminal={clearTerminal}
        terminalDock={terminalDock}
        setTerminalDock={setTerminalDock}
        isDraggingTerminal={isDraggingTerminal}
        onDragStart={handleDragStart}
        onDragEnd={handleDragEnd}
        agentState={agentState}
        phases={agentPhases}
        projectIntelligence={projectIntelligence}
        toolActivity={toolActivity}
        contextStatus={contextStatus}
        runtimeHints={runtimeHints}
        diffStatus={diffStatus}
        testStatus={testStatus}
        selectedModel={selectedModel}
        backendUrl={BACKEND_URL}
        backendConnected={backendConnected}
      />
    </div>
  )
}
