"use client"

import React, { useState, useEffect } from "react"
import { LeftSidebar } from "@/components/chat/left-sidebar"
import { RightSidebar } from "@/components/chat/right-sidebar"
import { Sliders, Shield, Folder, RefreshCw, Cpu } from "lucide-react"

export default function SettingsPage() {
  const [leftSidebarOpen, setLeftSidebarOpen] = useState(true)
  const [rightSidebarOpen, setRightSidebarOpen] = useState(true)
  
  // Settings state
  const [workspacePath, setWorkspacePath] = useState("c:\\Users\\danik\\Documents\\Field")
  const [selectedModel, setSelectedModel] = useState("google/gemini-3.1-pro")
  const [dsmSize, setDsmSize] = useState("12,408 active chunks")

  // Sync state with localStorage and backend on mount
  useEffect(() => {
    const fetchSettings = async () => {
      try {
        const res = await fetch("http://127.0.0.1:8000/api/settings")
        if (res.ok) {
          const data = await res.json()
          if (data.workspace_path) {
            setWorkspacePath(data.workspace_path)
            localStorage.setItem("sharrowkyn-workspace-path", data.workspace_path)
          }
        }
      } catch (err) {
        console.error("Failed to load settings from backend:", err)
        const savedPath = localStorage.getItem("sharrowkyn-workspace-path")
        if (savedPath) setWorkspacePath(savedPath)
      }
    }
    fetchSettings()
    
    const savedModel = localStorage.getItem("chat-selected-model")
    if (savedModel) setSelectedModel(savedModel)
  }, [])

  const handleSave = async () => {
    localStorage.setItem("sharrowkyn-workspace-path", workspacePath)
    localStorage.setItem("chat-selected-model", selectedModel)
    
    try {
      const response = await fetch("http://127.0.0.1:8000/api/settings", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ workspace_path: workspacePath })
      })
      const data = await response.json()
      if (data.status === "success") {
        alert("Settings saved successfully and synced with backend!")
      } else {
        alert(`Settings saved locally, but backend error: ${data.message}`)
      }
    } catch (err: any) {
      alert(`Settings saved locally, but failed to sync with backend: ${err.message}`)
    }
  }

  return (
    <div className="h-dvh bg-background flex overflow-hidden">
      <LeftSidebar isOpen={leftSidebarOpen} onToggle={() => setLeftSidebarOpen(!leftSidebarOpen)} />

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
              <p className="text-[13px] text-stone-400 font-light">Fine-tune your local Sharrowkyn autonomous engine.</p>
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
                <span className="text-[11px] text-stone-400 block">The folder SharrowkynAgent will scan, read, and write code to.</span>
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
                  <option value="google/gemini-3.1-pro">Gemini 3.1 Pro</option>
                  <option value="google/gemini-3.1-flash">Gemini 3.1 Flash</option>
                  <option value="openai/gpt-5.5">GPT-5.5 Flagship</option>
                  <option value="openai/o3-mini">o3-mini Reasoning</option>
                  <option value="anthropic/claude-4.7-opus">Claude 4.7 Opus</option>
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

          </div>
        </div>
      </div>

      {/* Right Sidebar */}
      <RightSidebar 
        isOpen={rightSidebarOpen} 
        onToggle={() => setRightSidebarOpen(!rightSidebarOpen)} 
        terminalLines={["sharrowkyn-core ~ settings console"]}
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
