"use client"

import { FileCode, Terminal, TestTube, GitBranch, Search, Database, Wrench, CheckCircle2, XCircle, Loader2 } from "lucide-react"
import { cn } from "@/lib/utils"

export interface ToolCall {
  id: string
  tool: string
  status: "running" | "done" | "error"
  target?: string
  detail?: string
  lines_changed?: number
  duration_ms?: number
}

export function AgentToolsPanel({
  tools,
  className
}: {
  tools: ToolCall[]
  className?: string
}) {
  const getToolIcon = (toolName: string) => {
    const name = toolName.toLowerCase()
    if (name.includes("file") || name.includes("write") || name.includes("read")) return FileCode
    if (name.includes("terminal") || name.includes("command")) return Terminal
    if (name.includes("test") || name.includes("pytest")) return TestTube
    if (name.includes("git") || name.includes("diff")) return GitBranch
    if (name.includes("search") || name.includes("grep")) return Search
    if (name.includes("memory") || name.includes("dsm")) return Database
    return Wrench
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "done":
        return CheckCircle2
      case "error":
        return XCircle
      default:
        return Loader2
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case "done":
        return {
          bg: "from-green-500/10 to-emerald-500/10",
          border: "border-green-500/30",
          text: "text-green-400",
          icon: "text-green-500"
        }
      case "error":
        return {
          bg: "from-red-500/10 to-rose-500/10",
          border: "border-red-500/30",
          text: "text-red-400",
          icon: "text-red-500"
        }
      default:
        return {
          bg: "from-blue-500/10 to-purple-500/10",
          border: "border-blue-500/30",
          text: "text-blue-400",
          icon: "text-blue-500"
        }
    }
  }

  if (tools.length === 0) return null

  return (
    <div className={cn("space-y-2", className)}>
      {tools.map((tool, index) => {
        const ToolIcon = getToolIcon(tool.tool)
        const StatusIcon = getStatusIcon(tool.status)
        const colors = getStatusColor(tool.status)
        const isRunning = tool.status === "running"

        return (
          <div
            key={tool.id}
            className={cn(
              "relative group flex items-center gap-3 p-3 rounded-lg border backdrop-blur-sm transition-all duration-300",
              `bg-gradient-to-r ${colors.bg}`,
              colors.border,
              isRunning && "animate-pulse"
            )}
            style={{
              animationDelay: `${index * 0.1}s`
            }}
          >
            {/* Tool icon */}
            <div className="relative flex-shrink-0">
              <div className={cn(
                "flex items-center justify-center w-10 h-10 rounded-lg bg-gradient-to-br from-slate-800 to-slate-900 border",
                colors.border
              )}>
                <ToolIcon className={cn("w-5 h-5", colors.icon)} />
              </div>

              {/* Rotating ring for running state */}
              {isRunning && (
                <div className={cn(
                  "absolute inset-0 rounded-lg border-2 animate-spin",
                  colors.border
                )} />
              )}
            </div>

            {/* Tool info */}
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className={cn("text-sm font-semibold", colors.text)}>
                  {tool.tool}
                </span>
                {tool.target && (
                  <span className="text-xs text-slate-500 truncate">
                    → {tool.target}
                  </span>
                )}
              </div>

              {tool.detail && (
                <p className="text-xs text-slate-400 mt-0.5 truncate">
                  {tool.detail}
                </p>
              )}

              {/* Metrics */}
              <div className="flex items-center gap-3 mt-1">
                {tool.lines_changed !== undefined && tool.lines_changed > 0 && (
                  <span className="text-xs text-slate-500">
                    {tool.lines_changed} lines
                  </span>
                )}
                {tool.duration_ms !== undefined && (
                  <span className="text-xs text-slate-500">
                    {tool.duration_ms < 1000
                      ? `${tool.duration_ms}ms`
                      : `${(tool.duration_ms / 1000).toFixed(1)}s`}
                  </span>
                )}
              </div>
            </div>

            {/* Status icon */}
            <div className="flex-shrink-0">
              <StatusIcon className={cn(
                "w-5 h-5",
                colors.icon,
                isRunning && "animate-spin"
              )} />
            </div>

            {/* Glow effect for running state */}
            {isRunning && (
              <div className={cn(
                "absolute inset-0 rounded-lg blur-lg opacity-50 animate-pulse",
                `bg-gradient-to-r ${colors.bg}`
              )} />
            )}

            {/* Progress bar for running state */}
            {isRunning && (
              <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-slate-800 rounded-b-lg overflow-hidden">
                <div className={cn(
                  "h-full bg-gradient-to-r animate-shimmer",
                  colors.bg.replace("/10", "/50")
                )} style={{ width: "30%" }} />
              </div>
            )}

            {/* Hover effect */}
            <div className="absolute inset-0 rounded-lg bg-white/0 group-hover:bg-white/5 transition-colors duration-300" />
          </div>
        )
      })}
    </div>
  )
}
