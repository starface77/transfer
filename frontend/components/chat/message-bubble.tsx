"use client"

import { useState } from "react"
import { cn } from "@/lib/utils"
import type { Message, ToolStep } from "./chat-shell"
import { Loader2, CheckCircle2, ChevronRight, ChevronDown, Sparkles, CircleDashed, FileCode } from "lucide-react"
import { MarkdownRenderer } from "./markdown-renderer"
import Image from "next/image"

interface MessageBubbleProps {
  message: Message
  isStreaming?: boolean
  onOpenDiff?: (filename: string) => void
}

// Format time for display
function formatTime(date: Date): string {
  return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
}

function getStepIcon(status: string) {
  if (status === "running") return <Loader2 strokeWidth={1.5} className="w-3.5 h-3.5 text-stone-400 animate-spin" />
  if (status === "done") return <CheckCircle2 strokeWidth={1.5} className="w-3.5 h-3.5 text-stone-300" />
  
  return <CircleDashed strokeWidth={1.5} className="w-3.5 h-3.5 text-stone-200" />
}

export function MessageBubble({ message, isStreaming = false, onOpenDiff }: MessageBubbleProps) {
  const isUser = message.role === "user"
  const [expandedSteps, setExpandedSteps] = useState(true)

  // Agent Message Design
  if (!isUser) {
    const hasSteps = message.toolSteps && message.toolSteps.length > 0;
    const isWorking = hasSteps && message.toolSteps?.some(s => s.status === "running");

    return (
      <div className="flex w-full gap-4 max-w-3xl mx-auto items-start py-5 group animate-in fade-in duration-300">
        
        {/* Sharrowkin Logo Avatar */}
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
          
          {/* Agent Name Header */}
          <div className="flex items-center gap-2">
            <span className="text-[14px] font-bold text-stone-800 tracking-tight leading-none">Sharrowkin</span>
            <span className="text-[11px] font-medium text-stone-500 bg-stone-100 border border-stone-200/50 px-1.5 py-0.5 rounded-md leading-none mt-0.5 tracking-tight">Agent</span>
          </div>

          {/* Feather-Light Agent Activity Timeline */}
          {hasSteps && (
            <div className="w-full max-w-[500px]">
              
              {/* Header */}
              <button 
                onClick={() => setExpandedSteps(!expandedSteps)}
                className="flex items-center gap-2 py-1 transition-opacity hover:opacity-70 group/header"
              >
                {isWorking ? (
                  <Loader2 strokeWidth={1.5} className="w-3.5 h-3.5 text-stone-400 animate-spin" />
                ) : (
                  <CheckCircle2 strokeWidth={1.5} className="w-3.5 h-3.5 text-stone-300" />
                )}
                <span className="text-[13px] font-medium text-stone-500 tracking-wide font-sans">
                  {isWorking ? "Agent thinking" : "Task completed"}
                </span>
                {expandedSteps ? (
                  <ChevronDown strokeWidth={1.5} className="w-3.5 h-3.5 text-stone-300 ml-1" />
                ) : (
                  <ChevronRight strokeWidth={1.5} className="w-3.5 h-3.5 text-stone-300 ml-1" />
                )}
              </button>
              
              {/* Steps List */}
              {expandedSteps && (
                <div className="pt-3 pb-1 flex flex-col gap-4">
                  {message.toolSteps?.map((step: ToolStep, idx: number, arr: ToolStep[]) => {
                    const isLast = idx === arr.length - 1;
                    return (
                      <div key={step.id} className="relative flex gap-3.5 group/step">
                        {/* Feather-light Timeline Line */}
                        {!isLast && (
                          <div className="absolute left-[6px] top-[18px] bottom-[-16px] w-[1px] bg-stone-100" />
                        )}
                        
                        {/* Icon */}
                        <div className="relative z-10 flex flex-col items-center justify-center bg-white h-4">
                          {getStepIcon(step.status)}
                        </div>

                        {/* Content */}
                        <div className="flex flex-col flex-1 pb-1">
                          <div className="flex items-center gap-2">
                            <span className={cn(
                              "text-[13px] font-normal tracking-wide transition-colors font-sans",
                              step.status === "running" ? "text-stone-800" : "text-stone-500"
                            )}>
                              {step.name}
                            </span>
                            
                            {/* Barely-there Badges */}
                            {step.status === "running" && (
                              <span className="px-1.5 py-0.5 rounded-full text-[10px] font-medium bg-stone-200/40 text-stone-500 font-sans">
                                working
                              </span>
                            )}
                            {step.status === "done" && (
                              <span className="text-[11px] text-stone-400 ml-auto font-normal font-sans">
                                {formatTime(new Date())}
                              </span>
                            )}
                          </div>
                          
                          {/* Description box - naked text instead of bg-box */}
                          {step.description && (
                            <div className="mt-1 text-[12px] text-stone-400/80 font-normal leading-relaxed font-sans">
                              {step.description}
                            </div>
                          )}
                        </div>
                      </div>
                    )
                  })}
                </div>
              )}
            </div>
          )}

          {/* Live Agent Thinking Stream */}
          {(message as any).thinkingText && (
            <div className="w-full max-w-[500px] mb-1">
              <div className="text-[12px] text-stone-400 font-mono leading-relaxed whitespace-pre-wrap border-l-2 border-stone-200 pl-3 py-1">
                {(message as any).thinkingText}
              </div>
            </div>
          )}

          {/* Main Agent Text Content */}
          {message.content && (
            <div className="text-[14px] text-stone-800 font-normal leading-relaxed max-w-full overflow-x-auto">
              <MarkdownRenderer content={message.content} isStreaming={isStreaming} />
            </div>
          )}

          {/* Clean Apple Interactive Diff Action Card */}
          {message.content && message.content.includes("```diff") && onOpenDiff && (
            <div className="flex items-center justify-between p-4 bg-stone-50 border border-stone-200/60 rounded-2xl max-w-[500px] shadow-[0_1px_4px_rgba(0,0,0,0.01)] animate-in fade-in slide-in-from-bottom-2 duration-500">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-white border border-stone-200/60 flex items-center justify-center text-stone-400 shadow-[0_1px_3px_rgba(0,0,0,0.01)]">
                  <FileCode size={16} strokeWidth={1.5} className="text-stone-500" />
                </div>
                <div className="flex flex-col">
                  <span className="text-[13px] text-stone-800 font-medium font-sans">components/app.tsx</span>
                  <span className="text-[11px] text-stone-400 font-normal font-sans mt-0.5">Proposed changes from workspace planner</span>
                </div>
              </div>
              <button
                onClick={() => onOpenDiff("components/app.tsx")}
                className="px-3.5 py-1.5 bg-stone-900 hover:bg-stone-800 text-white rounded-xl text-[12.5px] font-normal transition-colors shadow-sm font-sans shrink-0 ml-4"
              >
                View Split Diff
              </button>
            </div>
          )}

          {/* Streaming Indicator */}
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

  // User Message Design
  return (
    <div className="flex w-full justify-end max-w-3xl mx-auto py-4 user-message-enter">
      <div className="flex flex-col items-end gap-1.5 max-w-[85%] md:max-w-[75%]">
        <div
          className="rounded-[20px] rounded-br-[6px] bg-[#f4f4f5] text-stone-800 font-normal px-4 py-3"
        >
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
