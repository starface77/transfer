"use client"

import { useState, useEffect, useCallback } from "react"
import { useSearchParams } from "next/navigation"
import { MessageSquareDashed, ArrowDownToLine } from "lucide-react"
import { MessageList } from "./message-list"
import { Composer, type AIModel } from "./composer"
import { Button } from "@/components/ui/button"
import { LeftSidebar } from "./left-sidebar"
import { RightSidebar } from "./right-sidebar"

import { DiffViewer } from "./diff-viewer"
import { TerminalEmulator } from "./terminal-emulator"
import { cn } from "@/lib/utils"

// Data model for messages
export interface ToolStep {
  id: string
  name: string
  status: "running" | "done" | "error"
  description?: string
}

export interface Message {
  id: string
  role: "user" | "assistant"
  content: string
  createdAt: Date
  imageData?: string
  toolSteps?: ToolStep[]
}

// localStorage key for persisting messages
const MODEL_STORAGE_KEY = "chat-selected-model"

// Generates a unique ID for messages
function generateId(): string {
  return `${Date.now()}-${Math.random().toString(36).substring(2, 9)}`
}

export function ChatShell() {
  const searchParams = useSearchParams()
  const activeSessionId = searchParams?.get("session") || "session-1"
  const STORAGE_KEY = `sharrowkyn-session-messages-${activeSessionId}`

  const [messages, setMessages] = useState<Message[]>([])
  const [isStreaming, setIsStreaming] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [abortController, setAbortController] = useState<AbortController | null>(null)
  const [selectedModel, setSelectedModel] = useState<AIModel>("google/gemini-3.1-pro")
  const [isLoaded, setIsLoaded] = useState(false)
  const [leftSidebarOpen, setLeftSidebarOpen] = useState(true)
  const [rightSidebarOpen, setRightSidebarOpen] = useState(true)
  const [activeDiffFile, setActiveDiffFile] = useState<string | null>(null)

  // --- LIFTED TERMINAL EMULATOR STATE ---
  const [terminalLines, setTerminalLines] = useState<string[]>([
    "sharrowkyn-core ~ bash",
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

  const runBuildCommand = useCallback(() => {
    if (isRunningTask) return
    setIsRunningTask(true)
    setTerminalLines((prev) => [...prev, "", "$ npm run build"])

    const steps = [
      "▶ next build",
      "info  - Need to disable some telemetry rules...",
      "info  - Creating an optimized production build...",
      "info  - Compiled successfully",
      "info  - Collecting page data...",
      "info  - Generating static pages (0/14)...",
      "info  - Generating static pages (14/14)...",
      "✔ Finalizing page optimization...",
      "○  (Static)     automatically rendered as static HTML",
      "λ  (Server)     server-rendered on demand",
      "Route (app)                              Size     First Load JS",
      "┌ ○ /                                    5.24 kB        84.1 kB",
      "├ ○ /review                              4.12 kB        80.3 kB",
      "└ ○ /automations                         3.88 kB        79.1 kB",
      "✔ First load JS shared by all            74.9 kB",
      "✔ Build completed successfully inside 2.1s.",
    ]

    let idx = 0
    const interval = setInterval(() => {
      if (idx < steps.length) {
        setTerminalLines((prev) => [...prev, steps[idx]])
        idx++
      } else {
        clearInterval(interval)
        setIsRunningTask(false)
      }
    }, 150)
  }, [isRunningTask])

  const runTestCommand = useCallback(() => {
    if (isRunningTask) return
    setIsRunningTask(true)
    setTerminalLines((prev) => [...prev, "", "$ npm run test:unit"])

    const steps = [
      "▶ jest --config=jest.config.js",
      " PASS  tests/dsm-indexing.test.ts (1.24s)",
      "  ✓ should successfully index segmented memory blocks (45ms)",
      "  ✓ should query associative vectors with high cosine similarity (12ms)",
      " PASS  tests/agent-routing.test.ts (0.85s)",
      "  ✓ should fallback to reasoning loop on prompt failure (8ms)",
      "  ✓ should load regularized MoE layers (120ms)",
      " PASS  tests/diff-merger.test.ts (0.42s)",
      "  ✓ should safely parse unified diff patches (5ms)",
      "  ✓ should apply diff line replacements with no overlap (14ms)",
      "Test Suites: 3 passed, 3 total",
      "Tests:       6 passed, 6 total",
      "Snapshots:   0 total",
      "Time:        2.84s, estimated 3.0s",
      "Ran all test suites.",
      "✔ Jest unit suite passed successfully.",
    ]

    let idx = 0
    const interval = setInterval(() => {
      if (idx < steps.length) {
        setTerminalLines((prev) => [...prev, steps[idx]])
        idx++
      } else {
        clearInterval(interval)
        setIsRunningTask(false)
      }
    }, 150)
  }, [isRunningTask])

  const clearTerminal = useCallback(() => {
    setTerminalLines(["sharrowkyn-core ~ bash", "$ cleared console", "→ System ready. Awaiting input."])
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

    setIsRunningTask(true)

    try {
      const response = await fetch("http://127.0.0.1:8000/api/terminal", {
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
        // Dynamic mock onboarding messages depending on session type
        let defaultMessages: Message[] = []
        if (activeSessionId === "session-1") {
          defaultMessages = [
            {
              id: "onboarding-1",
              role: "assistant",
              content: "Welcome to your Field Workspace. I'm ready to help you coordinate, construct, and optimize **sharrowkyn-core** modules.",
              createdAt: new Date(),
            }
          ]
        } else if (activeSessionId === "session-2") {
          defaultMessages = [
            {
              id: "onboarding-2",
              role: "assistant",
              content: "Session initialized: **Web Scraping Agent**.\nHow can I help you extract, refine, and load structural data today?",
              createdAt: new Date(),
            }
          ]
        } else if (activeSessionId === "session-3") {
          defaultMessages = [
            {
              id: "onboarding-3",
              role: "assistant",
              content: "Session initialized: **Code Review Session**.\nReady to run code quality check pipelines and generate diff summaries.",
              createdAt: new Date(),
            }
          ]
        } else {
          defaultMessages = [
            {
              id: `onboarding-${activeSessionId}`,
              role: "assistant",
              content: "New Workspace chat session has been initialized. Ask me anything to get started!",
              createdAt: new Date(),
            }
          ]
        }
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

      // --- MOCK STREAMING FOR HIGH-FIDELITY AGENT DEMO ---
      // We simulate all agent steps and text generation over a timeline for a spectacular demo.
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
        const ws = new WebSocket("ws://127.0.0.1:8000/ws/agent")
        
        ws.onopen = () => {
          ws.send(JSON.stringify({
            task: content.trim(),
            workspace_path: "c:\\Users\\danik\\Documents\\Field"
          }))
          
          updateSteps([
            { id: "observe", name: "Observe (AST Workspace Analysis)", status: "running", description: "Scanning active project files..." }
          ])
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
              setTerminalLines(prev => [...prev, `➔ Transitioned to phase: ${data.phase.toUpperCase()}`])
              
            } else if (data.type === "log") {
              setTerminalLines(prev => [...prev, `[${data.level?.toUpperCase() || 'INFO'}] ${data.message}`])
              
            } else if (data.type === "patch_proposed") {
              setTerminalLines(prev => [...prev, `✔ Proposed code patch generated successfully!`])
              fullResponse += `\nI have generated a patch for your project. Please review it.\n`
              updateContent(fullResponse)
              setActiveDiffFile("agent-patch.diff") // trigger diff viewer
              
            } else if (data.type === "test_result") {
              setTerminalLines(prev => [
                ...prev, 
                `[TEST] Run complete. Success: ${data.success}`,
              ])
              
            } else if (data.type === "success") {
              updateSteps(currentSteps.map(s => ({ ...s, status: "done", description: "Finished." })))
              fullResponse += `\n**Task completed successfully.** Your workspace has been updated.`
              updateContent(fullResponse)
              setIsStreaming(false)
              setTerminalLines(prev => [...prev, `✔ Autonomous run complete.`])
              ws.close()
              
            } else if (data.type === "error") {
              updateSteps(currentSteps.map(s => s.status === "running" ? { ...s, status: "error", description: data.message } : s))
              setError(data.message)
              setIsStreaming(false)
              setTerminalLines(prev => [...prev, `✖ Error: ${data.message}`])
              ws.close()
            }
          } catch (e) {
            console.error(e)
          }
        }
        
        ws.onerror = (err) => {
          setError("WebSocket error. Could not connect to backend.")
          setIsStreaming(false)
        }
        
        ws.onclose = () => {
          if (isStreaming) setIsStreaming(false)
        }
        
      } catch (err: any) {
        console.error(err)
        setError(err.message)
        updateSteps([
          { id: "step-1", name: "Connection Error", status: "error", description: "Could not connect to Python backend. Is it running?" }
        ])
        setIsStreaming(false)
      }
    },
    [messages, isStreaming, selectedModel],
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
    setIsStreaming(false);
  }, [])

  const clearChat = useCallback(() => {
    setMessages([])
    setError(null)
    localStorage.removeItem(STORAGE_KEY)
  }, [])

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
            className="absolute top-4 left-4 z-20 h-10 w-10 rounded-full bg-stone-100 hover:bg-stone-200 text-stone-700"
            aria-label="Reset chat"
          >
            <MessageSquareDashed className="w-5 h-5" />
          </Button>

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
              onClose={() => setActiveDiffFile(null)}
              onAccept={() => {
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
      />
    </div>
  )
}
