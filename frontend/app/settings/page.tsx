"use client"

import React, { useState, useEffect, Suspense } from "react"
import { LeftSidebar } from "@/components/chat/left-sidebar"
import { RightSidebar } from "@/components/chat/right-sidebar"
import { Sliders, Shield, Folder, RefreshCw, Cpu, Key, CheckCircle2, XCircle, Loader2 } from "lucide-react"
import { toast } from "sonner"

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "http://127.0.0.1:8000"

export default function SettingsPage() {
  const [leftSidebarOpen, setLeftSidebarOpen] = useState(true)
  const [rightSidebarOpen, setRightSidebarOpen] = useState(true)
  
  // Settings state
  const [workspacePath, setWorkspacePath] = useState("")
  const [selectedModel, setSelectedModel] = useState("google/gemini-2.5-flash")
  const [dsmSize, setDsmSize] = useState("12,408 active chunks")
  const [apiKeys, setApiKeys] = useState<Record<string, boolean>>({})
  const [keyInputs, setKeyInputs] = useState<Record<string, string>>({})
  const [savingKey, setSavingKey] = useState<string | null>(null)

  // Fetch API keys status
  useEffect(() => {
    const fetchKeys = async () => {
      try {
        const res = await fetch(`${BACKEND_URL}/api/keys`)
        if (res.ok) {
          const data = await res.json()
          setApiKeys(data.providers || {})
        }
      } catch {}
    }
    fetchKeys()
  }, [])

  const handleSaveKey = async (provider: string) => {
    const key = keyInputs[provider]
    if (!key?.trim()) return
    setSavingKey(provider)
    try {
      const res = await fetch(`${BACKEND_URL}/api/keys`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ provider, api_key: key.trim() }),
      })
      if (res.ok) {
        setApiKeys((prev) => ({ ...prev, [provider]: true }))
        setKeyInputs((prev) => ({ ...prev, [provider]: "" }))
        toast.success(`${provider} API key saved`)
      } else {
        toast.error(`Failed to save ${provider} key`)
      }
    } catch {
      toast.error("Connection error")
    } finally {
      setSavingKey(null)
    }
  }

  // Sync state with localStorage and backend on mount
  useEffect(() => {
    const fetchSettings = async () => {
      try {
        const res = await fetch(`${BACKEND_URL}/api/settings`)
        if (res.ok) {
          const data = await res.json()
          if (data.workspace_path) {
            setWorkspacePath(data.workspace_path)
            localStorage.setItem("sharrowkin-workspace-path", data.workspace_path)
          }
        }
      } catch (err) {
        console.error("Failed to load settings from backend:", err)
        const savedPath = localStorage.getItem("sharrowkin-workspace-path")
        if (savedPath) setWorkspacePath(savedPath)
      }
    }
    fetchSettings()
    
    const savedModel = localStorage.getItem("chat-selected-model")
    if (savedModel) setSelectedModel(savedModel)
  }, [])

  const handleSave = async () => {
    localStorage.setItem("sharrowkin-workspace-path", workspacePath)
    localStorage.setItem("chat-selected-model", selectedModel)
    
    try {
      const response = await fetch(`${BACKEND_URL}/api/settings`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ workspace_path: workspacePath })
      })
      const data = await response.json()
      if (data.status === "success") {
        toast.success("Settings saved and synced with backend")
      } else {
        toast.error(`Backend error: ${data.message}`)
      }
    } catch (err: any) {
      toast.error(`Failed to sync: ${err.message}`)
    }
  }

  return (
    <div className="h-dvh bg-background flex overflow-hidden">
      <Suspense>
        <LeftSidebar isOpen={leftSidebarOpen} onToggle={() => setLeftSidebarOpen(!leftSidebarOpen)} />
      </Suspense>

      {/* Main Area */}
      <div className="flex-1 flex flex-col relative min-w-0 bg-[#f7f7f9] overflow-hidden">
        
        {/* Top Header - White & Clean */}
        <div className="h-14 border-b border-stone-200/60 flex items-center justify-between px-8 bg-white/80 backdrop-blur-md z-10 shrink-0">
          <div className="flex items-center gap-2.5 text-stone-850">
            <Sliders className="w-4 h-4 text-stone-400" strokeWidth={1.5} />
            <span className="font-medium text-[13px] tracking-wide text-stone-700">Settings</span>
          </div>
        </div>

        {/* Content Area */}
        <div className="flex-1 overflow-y-auto p-8 relative">
          <div className="max-w-2xl mx-auto space-y-6 animate-in fade-in duration-300">
            
            <div className="flex flex-col gap-1">
              <h1 className="text-xl font-light text-stone-800 tracking-tight">Configuration</h1>
              <p className="text-[13px] text-stone-400 font-light">Fine-tune your local sharrowkin autonomous engine.</p>
            </div>

            {/* Apple Card */}
            <div className="border border-stone-200/60 bg-white rounded-2xl p-6 shadow-[0_1px_8px_rgba(0,0,0,0.01)] space-y-5">
              
              {/* Workspace Config */}
              <div className="space-y-2">
                <div className="flex items-center gap-2 text-stone-700">
                  <Folder className="w-4 h-4 text-stone-400" />
                  <span className="text-[13px] font-medium">Workspace Path</span>
                </div>
                <input
                  type="text"
                  value={workspacePath}
                  onChange={(e) => setWorkspacePath(e.target.value)}
                  className="w-full p-3 border border-stone-200 rounded-xl text-[12.5px] font-mono focus:outline-none focus:border-stone-450 transition-colors bg-stone-50/50"
                />
                <span className="text-[11px] text-stone-400 block">The folder sharrowkinAgent will scan, read, and write code to.</span>
              </div>

              {/* Model selection */}
              <div className="space-y-2 pt-2">
                <div className="flex items-center gap-2 text-stone-700">
                  <Cpu className="w-4 h-4 text-stone-400" />
                  <span className="text-[13px] font-medium">Active Intelligence Model</span>
                </div>
                <select
                  value={selectedModel}
                  onChange={(e) => setSelectedModel(e.target.value)}
                  className="w-full p-3 border border-stone-200 rounded-xl text-[13px] focus:outline-none focus:border-stone-450 transition-colors bg-stone-50/50"
                >
                  <option value="google/gemini-2.5-flash">Gemini 2.5 Flash</option>
                  <option value="google/gemini-2.5-pro">Gemini 2.5 Pro</option>
                  <option value="openai/gpt-4o">GPT-4o</option>
                  <option value="openai/o3-mini">o3-mini Reasoning</option>
                  <option value="anthropic/claude-sonnet-4">Claude Sonnet 4</option>
                </select>
              </div>

              {/* Memory vector specs */}
              <div className="space-y-2 pt-2">
                <div className="flex items-center gap-2 text-stone-700">
                  <Shield className="w-4 h-4 text-stone-400" />
                  <span className="text-[13px] font-medium">Dynamic Segmented Memory Status</span>
                </div>
                <div className="p-3 border border-stone-100 rounded-xl bg-stone-50/30 text-[12px] font-mono text-stone-600">
                  {dsmSize}
                </div>
              </div>

              <div className="pt-4 border-t border-stone-100 flex justify-end">
                <button
                  onClick={handleSave}
                  className="px-5 py-2 bg-stone-900 hover:bg-stone-850 text-white rounded-xl text-[12.5px] transition-colors shadow-sm font-sans"
                >
                  Save Settings
                </button>
              </div>

            </div>

            {/* API Keys Card */}
            <div className="border border-stone-200/60 bg-white rounded-2xl p-6 shadow-[0_1px_8px_rgba(0,0,0,0.01)] space-y-5">
              <div className="flex items-center gap-2 text-stone-700">
                <Key className="w-4 h-4 text-stone-400" />
                <span className="text-[13px] font-medium">API Keys</span>
              </div>
              <p className="text-[11px] text-stone-400">Configure API keys for LLM providers. Keys are stored in the backend session only.</p>

              {["gemini", "openai", "anthropic", "openrouter"].map((provider) => (
                <div key={provider} className="space-y-1.5">
                  <div className="flex items-center gap-2">
                    <span className="text-[12px] font-medium text-stone-600 capitalize">{provider}</span>
                    {apiKeys[provider] ? (
                      <CheckCircle2 size={13} className="text-emerald-500" />
                    ) : (
                      <XCircle size={13} className="text-stone-300" />
                    )}
                  </div>
                  <div className="flex gap-2">
                    <input
                      type="password"
                      value={keyInputs[provider] || ""}
                      onChange={(e) => setKeyInputs((prev) => ({ ...prev, [provider]: e.target.value }))}
                      placeholder={apiKeys[provider] ? "••••••• (configured)" : `Enter ${provider} API key`}
                      className="flex-1 p-2.5 border border-stone-200 rounded-xl text-[12px] font-mono focus:outline-none focus:border-stone-400 transition-colors bg-stone-50/50"
                    />
                    <button
                      onClick={() => handleSaveKey(provider)}
                      disabled={!keyInputs[provider]?.trim() || savingKey === provider}
                      className="px-3 py-2 bg-stone-900 hover:bg-stone-800 disabled:bg-stone-300 text-white rounded-xl text-[11px] transition-colors"
                    >
                      {savingKey === provider ? <Loader2 size={12} className="animate-spin" /> : "Save"}
                    </button>
                  </div>
                </div>
              ))}
            </div>

          </div>
        </div>
      </div>

      {/* Right Sidebar */}
      <RightSidebar 
        isOpen={rightSidebarOpen} 
        onToggle={() => setRightSidebarOpen(!rightSidebarOpen)} 
        terminalLines={["sharrowkin-core ~ settings console"]}
        isRunningTask={false}
        currentInput=""
        setCurrentInput={() => {}}
        onSubmitCommand={() => {}}
        runBuildCommand={() => {}}
        runTestCommand={() => {}}
        clearTerminal={() => {}}
        terminalDock="sidebar"
        setTerminalDock={() => {}}
        isDraggingTerminal={false}
        onDragStart={() => {}}
        onDragEnd={() => {}}
      />
    </div>
  )
}
