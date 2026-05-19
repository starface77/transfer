"use client"

import { useState, useEffect } from "react"
import { cn } from "@/lib/utils"
import type { Message, ToolStep, TaskPlan, DebugAnalysis } from "./chat-shell"
import { Loader2, CheckCircle2, ChevronRight, ChevronDown, CircleDashed, FileCode, Sparkles, XCircle, ListTodo, Clock, Bug, AlertCircle, Lightbulb } from "lucide-react"
import { MarkdownRenderer } from "./markdown-renderer"
import Image from "next/image"
import { getAgentName } from "@/lib/persona-api"

interface MessageBubbleProps {
  message: Message
  isStreaming?: boolean
  onOpenDiff?: (filename: string) => void
}

function formatTime(date: Date): string {
  return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
}

function getStepIcon(status: string) {
  if (status === "running") return <Loader2 strokeWidth={1.5} className="w-3.5 h-3.5 text-stone-400 animate-spin" />
  if (status === "done") return <CheckCircle2 strokeWidth={1.5} className="w-3.5 h-3.5 text-emerald-400/70" />
  if (status === "error") return <XCircle strokeWidth={1.5} className="w-3.5 h-3.5 text-red-400/70" />
  return <CircleDashed strokeWidth={1.5} className="w-3.5 h-3.5 text-stone-200" />
}

function getTaskIcon(status: string) {
  if (status === "in_progress") return <Loader2 strokeWidth={1.5} className="w-3 h-3 text-blue-500 animate-spin" />
  if (status === "done") return <CheckCircle2 strokeWidth={1.5} className="w-3 h-3 text-emerald-500" />
  if (status === "error") return <XCircle strokeWidth={1.5} className="w-3 h-3 text-red-500" />
  return <CircleDashed strokeWidth={1.5} className="w-3 h-3 text-stone-300" />
}

function TaskPlanItem({ task, depth = 0 }: { task: TaskPlan; depth?: number }) {
  const [expanded, setExpanded] = useState(true)
  const hasSubtasks = task.subtasks && task.subtasks.length > 0

  return (
    <div className={cn("flex flex-col", depth > 0 && "ml-4 mt-1")}>
      <div className="flex items-center gap-2 py-1">
        {hasSubtasks && (
          <button
            onClick={() => setExpanded(!expanded)}
            className="shrink-0 hover:bg-stone-100 rounded p-0.5 transition-colors"
          >
            {expanded ? (
              <ChevronDown strokeWidth={1.5} className="w-3 h-3 text-stone-400" />
            ) : (
              <ChevronRight strokeWidth={1.5} className="w-3 h-3 text-stone-400" />
            )}
          </button>
        )}
        {!hasSubtasks && <div className="w-4" />}

        {getTaskIcon(task.status)}

        <span className={cn(
          "text-[12px] font-medium transition-colors",
          task.status === "in_progress" ? "text-stone-800" :
          task.status === "done" ? "text-stone-500 line-through" :
          task.status === "error" ? "text-red-600" :
          "text-stone-600"
        )}>
          {task.title}
        </span>

        {task.estimatedTime && task.status === "pending" && (
          <span className="flex items-center gap-1 text-[10px] text-stone-400 ml-auto">
            <Clock strokeWidth={1.5} className="w-2.5 h-2.5" />
            {task.estimatedTime}
          </span>
        )}
      </div>

      {hasSubtasks && expanded && (
        <div className="flex flex-col">
          {task.subtasks!.map((subtask) => (
            <TaskPlanItem key={subtask.id} task={subtask} depth={depth + 1} />
          ))}
        </div>
      )}
    </div>
  )
}

export function MessageBubble({ message, isStreaming = false, onOpenDiff }: MessageBubbleProps) {
  const isUser = message.role === "user"
  const [expandedSteps, setExpandedSteps] = useState(true)
  const [agentName, setAgentName] = useState("Sharrowkin")

  // Fetch agent name on mount and when persona changes
  useEffect(() => {
    const fetchAgentName = async () => {
      try {
        const response = await getAgentName()
        setAgentName(response.agent_name)
      } catch (error) {
        console.error("Failed to fetch agent name:", error)
      }
    }

    fetchAgentName()

    // Listen for persona change events
    const handlePersonaChange = () => {
      fetchAgentName()
    }

    window.addEventListener("persona-changed", handlePersonaChange)
    return () => window.removeEventListener("persona-changed", handlePersonaChange)
  }, [])

  if (!isUser) {
    const hasSteps = message.toolSteps && message.toolSteps.length > 0;
    const isWorking = hasSteps && message.toolSteps?.some(s => s.status === "running");

    return (
      <div className="flex w-full gap-4 max-w-3xl mx-auto items-start py-5 group animate-in fade-in duration-300">
        
        {/* Avatar */}
        <div className="w-8 h-8 flex items-center justify-center shrink-0 mt-0.5">
          <Image 
            src="/images/logo.png" 
            alt="Sharrowkin" 
            width={28} 
            height={28} 
            quality={100}
            priority
            unoptimized
            className="object-contain drop-shadow-sm" 
          />
        </div>

        <div className="flex flex-col flex-1 min-w-0 gap-3.5">
          
          {/* Name */}
          <div className="flex items-center gap-2">
            <span className="text-[14px] font-bold text-stone-800 tracking-tight leading-none">{agentName}</span>
            <span className="text-[11px] font-medium text-stone-500 bg-stone-100 border border-stone-200/50 px-1.5 py-0.5 rounded-md leading-none mt-0.5 tracking-tight">Agent</span>
          </div>

          {/* Task Plan (TODO) */}
          {message.taskPlan && message.taskPlan.length > 0 && (
            <div className="w-full max-w-[600px]">
              <div className="bg-gradient-to-br from-blue-50/50 to-indigo-50/30 border border-blue-100/60 rounded-xl p-3 shadow-sm">
                <div className="flex items-center gap-2 mb-2">
                  <ListTodo strokeWidth={1.5} className="w-4 h-4 text-blue-600" />
                  <span className="text-[13px] font-semibold text-blue-900">Execution Plan</span>
                  <span className="text-[10px] text-blue-600 bg-blue-100/60 px-1.5 py-0.5 rounded-md ml-auto">
                    {message.taskPlan.filter(t => t.status === "done").length}/{message.taskPlan.length} completed
                  </span>
                </div>
                <div className="flex flex-col gap-0.5">
                  {message.taskPlan.map((task) => (
                    <TaskPlanItem key={task.id} task={task} />
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Timeline Steps */}
          {hasSteps && (
            <div className="w-full max-w-[500px]">

              <button
                onClick={() => setExpandedSteps(!expandedSteps)}
                className="flex items-center gap-2 py-1 transition-opacity hover:opacity-70"
              >
                {isWorking ? (
                  <Loader2 strokeWidth={1.5} className="w-3.5 h-3.5 text-stone-400 animate-spin" />
                ) : (
                  <CheckCircle2 strokeWidth={1.5} className="w-3.5 h-3.5 text-emerald-400/70" />
                )}
                <span className="text-[13px] font-medium text-stone-500 tracking-wide">
                  {isWorking ? "Agent thinking" : "Task completed"}
                </span>
                {expandedSteps ? (
                  <ChevronDown strokeWidth={1.5} className="w-3.5 h-3.5 text-stone-300 ml-1" />
                ) : (
                  <ChevronRight strokeWidth={1.5} className="w-3.5 h-3.5 text-stone-300 ml-1" />
                )}
              </button>
              
              <div className={cn(
                "overflow-hidden transition-all duration-300 ease-out",
                expandedSteps ? "max-h-[600px] opacity-100" : "max-h-0 opacity-0"
              )}>
                <div className="pt-3 pb-1 flex flex-col gap-4">
                  {message.toolSteps?.map((step: ToolStep, idx: number, arr: ToolStep[]) => {
                    const isLast = idx === arr.length - 1;
                    return (
                      <div key={step.id} className="relative flex gap-3.5 animate-in fade-in slide-in-from-top-1 duration-300" style={{ animationDelay: `${idx * 60}ms` }}>
                        {/* Timeline connector */}
                        {!isLast && (
                          <div className="absolute left-[6px] top-[18px] bottom-[-16px] w-[1px] bg-stone-100 transition-colors duration-500" />
                        )}
                        
                        {/* Icon */}
                        <div className="relative z-10 flex items-center justify-center bg-white h-4">
                          {getStepIcon(step.status)}
                        </div>

                        {/* Content */}
                        <div className="flex flex-col flex-1 pb-1">
                          <div className="flex items-center gap-2">
                            <span className={cn(
                              "text-[13px] font-normal tracking-wide transition-colors duration-300",
                              step.status === "running" ? "text-stone-800" : 
                              step.status === "error" ? "text-red-500" : "text-stone-400"
                            )}>
                              {step.name}
                            </span>
                            
                            {step.status === "running" && (
                              <span className="px-1.5 py-0.5 rounded-full text-[10px] font-medium bg-stone-100/60 text-stone-400 animate-in fade-in duration-200">
                                working
                              </span>
                            )}
                          </div>
                          
                          {step.description && step.status === "running" && (
                            <div className="mt-1 text-[12px] text-stone-400/70 font-normal leading-relaxed animate-in fade-in duration-200">
                              {step.description}
                            </div>
                          )}
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>
            </div>
          )}

          {/* Debug Analysis */}
          {message.debugAnalysis && (
            <div className="w-full max-w-[600px]">
              <div className="bg-gradient-to-br from-red-50/50 to-orange-50/30 border border-red-100/60 rounded-xl p-3 shadow-sm">
                <div className="flex items-center gap-2 mb-2">
                  <Bug strokeWidth={1.5} className="w-4 h-4 text-red-600" />
                  <span className="text-[13px] font-semibold text-red-900">Error Analysis</span>
                  <span className="text-[10px] text-red-600 bg-red-100/60 px-1.5 py-0.5 rounded-md ml-auto">
                    {message.debugAnalysis.errorType}
                  </span>
                </div>

                <div className="flex flex-col gap-2">
                  {/* Error location */}
                  {message.debugAnalysis.filePath && (
                    <div className="flex items-center gap-2 text-[11px] text-stone-600">
                      <FileCode strokeWidth={1.5} className="w-3 h-3" />
                      <span className="font-mono">
                        {message.debugAnalysis.filePath}:{message.debugAnalysis.lineNumber}
                      </span>
                    </div>
                  )}

                  {/* Root cause */}
                  <div className="flex items-start gap-2">
                    <AlertCircle strokeWidth={1.5} className="w-3.5 h-3.5 text-red-500 mt-0.5 shrink-0" />
                    <div className="flex flex-col gap-0.5">
                      <span className="text-[11px] font-medium text-red-700">Root Cause:</span>
                      <span className="text-[12px] text-stone-700 leading-relaxed">
                        {message.debugAnalysis.rootCause}
                      </span>
                    </div>
                  </div>

                  {/* Suggested fix */}
                  <div className="flex items-start gap-2">
                    <Lightbulb strokeWidth={1.5} className="w-3.5 h-3.5 text-amber-500 mt-0.5 shrink-0" />
                    <div className="flex flex-col gap-0.5">
                      <span className="text-[11px] font-medium text-amber-700">Suggested Fix:</span>
                      <span className="text-[12px] text-stone-700 leading-relaxed font-mono bg-stone-50 px-2 py-1 rounded">
                        {message.debugAnalysis.suggestedFix}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Live Thinking — subtle left border */}
          {(message as any).thinkingText && (
            <div className="w-full max-w-[500px] animate-in fade-in duration-200">
              <div className="text-[12px] text-stone-400 leading-relaxed whitespace-pre-wrap border-l-[1.5px] border-stone-200/80 pl-3 py-1">
                {(message as any).thinkingText.split("\n").slice(-5).join("\n")}
              </div>
            </div>
          )}

          {/* Main Content */}
          {message.content && (
            <div className="text-[14px] text-stone-800 font-normal leading-relaxed max-w-full overflow-x-auto animate-in fade-in duration-300">
              <MarkdownRenderer content={message.content} isStreaming={isStreaming} />
            </div>
          )}

          {/* Diff Card */}
          {message.content && message.content.includes("```diff") && onOpenDiff && (
            <div className="flex items-center justify-between p-4 bg-stone-50 border border-stone-200/60 rounded-2xl max-w-[500px] shadow-[0_1px_4px_rgba(0,0,0,0.01)] animate-in fade-in slide-in-from-bottom-2 duration-500">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-white border border-stone-200/60 flex items-center justify-center shadow-[0_1px_3px_rgba(0,0,0,0.01)]">
                  <FileCode size={16} strokeWidth={1.5} className="text-stone-500" />
                </div>
                <div className="flex flex-col">
                  <span className="text-[13px] text-stone-800 font-medium">Proposed Changes</span>
                  <span className="text-[11px] text-stone-400 font-normal mt-0.5">Review agent patch</span>
                </div>
              </div>
              <button
                onClick={() => onOpenDiff("agent-patch.diff")}
                className="px-3.5 py-1.5 bg-stone-900 hover:bg-stone-800 text-white rounded-xl text-[12.5px] font-normal transition-colors shadow-sm shrink-0 ml-4"
              >
                View Diff
              </button>
            </div>
          )}

          {/* Streaming dots */}
          {isStreaming && !message.content && !isWorking && (
            <div className="flex items-center gap-1.5 h-6">
              <div className="w-1.5 h-1.5 rounded-full bg-stone-200 animate-pulse" />
              <div className="w-1.5 h-1.5 rounded-full bg-stone-200 animate-pulse delay-75" />
              <div className="w-1.5 h-1.5 rounded-full bg-stone-200 animate-pulse delay-150" />
            </div>
          )}
        </div>
      </div>
    )
  }

  // User Message
  return (
    <div className="flex w-full justify-end max-w-3xl mx-auto py-4 user-message-enter">
      <div className="flex flex-col items-end gap-1.5 max-w-[85%] md:max-w-[75%]">
        <div className="rounded-[20px] rounded-br-[6px] bg-[#f4f4f5] text-stone-800 font-normal px-4 py-3">
          <div className="flex flex-col gap-2">
            {message.imageData && (
              <div className="w-32 h-32 rounded-xl overflow-hidden border border-stone-100 shadow-sm image-bounce">
                <Image
                  src={message.imageData || "/placeholder.svg"}
                  alt="Uploaded image"
                  width={128}
                  height={128}
                  className="w-full h-full object-cover hover:scale-105 transition-transform duration-500"
                />
              </div>
            )}
            <p className="text-[14px] leading-relaxed whitespace-pre-wrap break-words">{message.content}</p>
          </div>
        </div>
      </div>
    </div>
  )
}
