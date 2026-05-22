"use client"

import { Suspense, useEffect, useMemo, useState } from "react"
import { CheckCircle2, KeyRound, Loader2, Plug, Power, Settings2, ShieldCheck, UserRound } from "lucide-react"
import { toast } from "sonner"
import { LeftSidebar } from "@/components/chat/left-sidebar"
import { RightSidebar } from "@/components/chat/right-sidebar"
import { cn } from "@/lib/utils"

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "http://127.0.0.1:8000"
const PROVIDERS = ["gemini", "anthropic", "openai", "openrouter"]

export default function SettingsPage() {
  const [leftSidebarOpen, setLeftSidebarOpen] = useState(true)
  const [rightSidebarOpen, setRightSidebarOpen] = useState(true)
  const [workspacePath, setWorkspacePath] = useState("")
  const [selectedModel, setSelectedModel] = useState("google/gemini-2.5-flash")
  const [autonomyLevel, setAutonomyLevel] = useState("high")
  const [accountConnected, setAccountConnected] = useState(false)
  const [githubUsername, setGithubUsername] = useState("")
  const [apiKeys, setApiKeys] = useState<Record<string, boolean>>({})
  const [keyInputs, setKeyInputs] = useState<Record<string, string>>({})
  const [savingKey, setSavingKey] = useState<string | null>(null)

  const configuredCount = useMemo(() => Object.values(apiKeys).filter(Boolean).length, [apiKeys])

  useEffect(() => {
    const load = async () => {
      const savedModel = localStorage.getItem("chat-selected-model")
      const savedPath = localStorage.getItem("sharrowkin-workspace-path")
      const savedAccount = localStorage.getItem("sharrowkin-account-connected")
      if (savedModel) setSelectedModel(savedModel)
      if (savedPath) setWorkspacePath(savedPath)
      if (savedAccount === "true") setAccountConnected(true)

      try {
        const [settingsRes, keysRes] = await Promise.all([
          fetch(`${BACKEND_URL}/api/settings`),
          fetch(`${BACKEND_URL}/api/keys`),
        ])
        if (settingsRes.ok) {
          const data = await settingsRes.json()
          if (data.workspace_path) setWorkspacePath(data.workspace_path)
          if (data.github_username) {
            setGithubUsername(data.github_username)
            setAccountConnected(true)
          }
        }
        if (keysRes.ok) {
          const data = await keysRes.json()
          setApiKeys(data.providers || {})
        }
      } catch {}
    }
    load()
  }, [])

  const handleSaveSettings = async () => {
    localStorage.setItem("chat-selected-model", selectedModel)
    localStorage.setItem("sharrowkin-workspace-path", workspacePath)
    localStorage.setItem("sharrowkin-autonomy-level", autonomyLevel)

    try {
      const response = await fetch(`${BACKEND_URL}/api/settings`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ workspace_path: workspacePath }),
      })
      const data = await response.json()
      if (data.status === "success") toast.success("Agent settings saved")
      else toast.error(data.message || "Could not save settings")
    } catch (error: any) {
      toast.error(error.message || "Backend unavailable")
    }
  }

  const handleSaveKey = async (provider: string) => {
    const apiKey = keyInputs[provider]?.trim()
    if (!apiKey) return
    setSavingKey(provider)
    try {
      const response = await fetch(`${BACKEND_URL}/api/keys`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ provider, api_key: apiKey }),
      })
      if (!response.ok) throw new Error(`Failed to save ${provider}`)
      setApiKeys((prev) => ({ ...prev, [provider]: true }))
      setKeyInputs((prev) => ({ ...prev, [provider]: "" }))
      toast.success(`${provider} connected`)
    } catch (error: any) {
      toast.error(error.message || "Could not save API key")
    } finally {
      setSavingKey(null)
    }
  }

  const handleAccountToggle = async () => {
    const next = !accountConnected
    try {
      const response = await fetch(`${BACKEND_URL}/api/git/connect`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username: next ? githubUsername.trim() : "", token: "", repo_url: "" }),
      })
      const data = await response.json()
      if (data.status !== "success") throw new Error(data.message || "Account action failed")
      setAccountConnected(next)
      localStorage.setItem("sharrowkin-account-connected", String(next))
      toast.success(data.message || (next ? "Account connected" : "Account disconnected"))
    } catch (error: any) {
      toast.error(error.message || "Backend unavailable")
    }
  }

  return (
    <div className="h-dvh overflow-hidden bg-white text-stone-900 flex">
      <Suspense>
        <LeftSidebar isOpen={leftSidebarOpen} onToggle={() => setLeftSidebarOpen(!leftSidebarOpen)} />
      </Suspense>

      <main className="flex min-w-0 flex-1 flex-col bg-white">
        <header className="flex h-12 shrink-0 items-center justify-between px-5 text-[13px]">
          <div className="flex items-center gap-2.5">
            <Settings2 size={15} strokeWidth={1.6} className="text-stone-500" />
            <span className="font-normal text-stone-900">Deploy-ready agent settings</span>
          </div>
          <div className="flex items-center gap-2 text-[12px] text-stone-500">
            <span className="rounded-full bg-emerald-50 px-2.5 py-1 text-emerald-700">{configuredCount} API connected</span>
            <span className="rounded-full bg-stone-50 px-2.5 py-1">{BACKEND_URL.replace(/^https?:\/\//, "")}</span>
          </div>
        </header>

        <div className="flex-1 overflow-y-auto px-8 py-6">
          <div className="mx-auto max-w-4xl space-y-8">
            <section>
              <h1 className="text-[22px] font-normal tracking-[-0.02em] text-stone-950">Agent control center</h1>
              <p className="mt-1 max-w-2xl text-[13px] leading-relaxed text-stone-500">
                Connect account context, configure provider keys, and prepare the autonomous coding agent for production deploy.
              </p>
            </section>

            <section className="grid gap-4 md:grid-cols-3">
              {[
                ["Backend", "FastAPI websocket", "ready"],
                ["Account", accountConnected ? "Connected profile" : "Local profile", accountConnected ? "connected" : "local"],
                ["Secrets", `${configuredCount}/${PROVIDERS.length} providers`, configuredCount ? "configured" : "missing"],
              ].map(([label, value, status]) => (
                <div key={label} className="rounded-2xl bg-stone-50/80 p-4">
                  <div className="text-[12px] text-stone-500">{label}</div>
                  <div className="mt-1 text-[14px] font-normal text-stone-900">{value}</div>
                  <div className="mt-3 inline-flex rounded-full bg-white px-2.5 py-1 text-[11.5px] text-stone-500">{status}</div>
                </div>
              ))}
            </section>

            <section className="grid gap-4 lg:grid-cols-[1fr_1.1fr]">
              <div className="rounded-2xl bg-stone-50/80 p-5">
                <div className="mb-5 flex items-center gap-2">
                  <UserRound size={16} strokeWidth={1.6} className="text-stone-500" />
                  <div>
                    <div className="text-[14px] font-normal text-stone-900">Account connection</div>
                    <div className="text-[12px] text-stone-500">Safe local profile for deploy ownership.</div>
                  </div>
                </div>
                <div className="flex items-center justify-between rounded-xl bg-white p-3">
                  <div className="min-w-0 flex-1">
                    <div className="text-[13px] text-stone-800">GitHub account</div>
                    <input
                      value={githubUsername}
                      onChange={(event) => setGithubUsername(event.target.value)}
                      disabled={accountConnected}
                      placeholder="github username"
                      className="mt-1 w-full bg-transparent text-[12px] text-stone-500 outline-none placeholder:text-stone-300 disabled:text-stone-400"
                    />
                  </div>
                  <button disabled={!accountConnected && !githubUsername.trim()} onClick={handleAccountToggle} className={cn("rounded-full px-3 py-1.5 text-[12px] transition-colors disabled:cursor-not-allowed disabled:opacity-40", accountConnected ? "bg-stone-900 text-white hover:bg-stone-800" : "bg-stone-100 text-stone-700 hover:bg-stone-200")}> 
                    {accountConnected ? "Disconnect" : "Connect"}
                  </button>
                </div>
              </div>

              <div className="rounded-2xl bg-stone-50/80 p-5">
                <div className="mb-5 flex items-center gap-2">
                  <Plug size={16} strokeWidth={1.6} className="text-stone-500" />
                  <div>
                    <div className="text-[14px] font-normal text-stone-900">Agent runtime</div>
                    <div className="text-[12px] text-stone-500">Autonomy, model, and workspace path.</div>
                  </div>
                </div>
                <div className="space-y-3">
                  <input value={workspacePath} onChange={(event) => setWorkspacePath(event.target.value)} placeholder="/path/to/workspace" className="w-full rounded-xl bg-white px-3 py-2.5 text-[13px] font-mono text-stone-800 outline-none ring-1 ring-transparent transition focus:ring-stone-200" />
                  <div className="grid gap-3 sm:grid-cols-2">
                    <select value={selectedModel} onChange={(event) => setSelectedModel(event.target.value)} className="rounded-xl bg-white px-3 py-2.5 text-[13px] text-stone-800 outline-none ring-1 ring-transparent transition focus:ring-stone-200">
                      <option value="google/gemini-2.5-flash">Gemini 2.5 Flash</option>
                      <option value="google/gemini-2.5-pro">Gemini 2.5 Pro</option>
                      <option value="openai/gpt-4o">GPT-4o</option>
                      <option value="anthropic/claude-sonnet-4">Claude Sonnet 4</option>
                    </select>
                    <select value={autonomyLevel} onChange={(event) => setAutonomyLevel(event.target.value)} className="rounded-xl bg-white px-3 py-2.5 text-[13px] text-stone-800 outline-none ring-1 ring-transparent transition focus:ring-stone-200">
                      <option value="high">High autonomy</option>
                      <option value="balanced">Balanced</option>
                      <option value="review-first">Review first</option>
                    </select>
                  </div>
                  <button onClick={handleSaveSettings} className="rounded-full bg-stone-900 px-4 py-2 text-[12.5px] text-white transition-colors hover:bg-stone-800">Save runtime</button>
                </div>
              </div>
            </section>

            <section className="rounded-2xl bg-stone-50/80 p-5">
              <div className="mb-5 flex items-center gap-2">
                <KeyRound size={16} strokeWidth={1.6} className="text-stone-500" />
                <div>
                  <div className="text-[14px] font-normal text-stone-900">API providers</div>
                  <div className="text-[12px] text-stone-500">Keys are masked in UI and stored server-side through the backend endpoint.</div>
                </div>
              </div>
              <div className="grid gap-3 md:grid-cols-2">
                {PROVIDERS.map((provider) => (
                  <div key={provider} className="rounded-xl bg-white p-3">
                    <div className="mb-2 flex items-center justify-between">
                      <div className="flex items-center gap-2 text-[13px] capitalize text-stone-800">
                        {apiKeys[provider] ? <CheckCircle2 size={14} className="text-emerald-500" /> : <ShieldCheck size={14} className="text-stone-300" />}
                        {provider}
                      </div>
                      <span className="text-[11.5px] text-stone-400">{apiKeys[provider] ? "connected" : "not set"}</span>
                    </div>
                    <div className="flex gap-2">
                      <input type="password" value={keyInputs[provider] || ""} onChange={(event) => setKeyInputs((prev) => ({ ...prev, [provider]: event.target.value }))} placeholder={apiKeys[provider] ? "•••••••• configured" : `Paste ${provider} key`} className="min-w-0 flex-1 rounded-lg bg-stone-50 px-3 py-2 text-[12px] font-mono outline-none" />
                      <button onClick={() => handleSaveKey(provider)} disabled={!keyInputs[provider]?.trim() || savingKey === provider} className="rounded-lg bg-stone-900 px-3 text-[12px] text-white transition-colors hover:bg-stone-800 disabled:bg-stone-200">
                        {savingKey === provider ? <Loader2 size={13} className="animate-spin" /> : "Save"}
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </section>

            <section className="rounded-2xl bg-stone-50/80 p-5">
              <div className="mb-4 flex items-center gap-2">
                <Power size={16} strokeWidth={1.6} className="text-stone-500" />
                <div className="text-[14px] font-normal text-stone-900">Deploy checklist</div>
              </div>
              <div className="grid gap-2 md:grid-cols-2">
                {["NEXT_PUBLIC_BACKEND_URL configured", "Backend /api/health reachable", "At least one LLM API key connected", "Workspace path points to repository"].map((item) => (
                  <div key={item} className="flex items-center gap-2 rounded-xl bg-white px-3 py-2 text-[12.5px] text-stone-600">
                    <CheckCircle2 size={14} className="text-emerald-500" />
                    {item}
                  </div>
                ))}
              </div>
            </section>
          </div>
        </div>
      </main>

      <RightSidebar
        isOpen={rightSidebarOpen}
        onToggle={() => setRightSidebarOpen(!rightSidebarOpen)}
        terminalLines={["agent settings", "api providers ready for secure configuration"]}
        selectedModel={selectedModel}
        backendUrl={BACKEND_URL}
      />
    </div>
  )
}
