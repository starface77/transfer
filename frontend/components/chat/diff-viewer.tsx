"use client"

import { useState } from "react"
import { X, Check, ArrowRight, Columns, Rows, FileCode, CheckCircle2 } from "lucide-react"
import { cn } from "@/lib/utils"

interface DiffViewerProps {
  filename: string
  onClose: () => void
  onAccept: () => void
}

export function DiffViewer({ filename, onClose, onAccept }: DiffViewerProps) {
  const [viewMode, setViewMode] = useState<"split" | "unified">("split")
  const [hasAccepted, setHasAccepted] = useState(false)

  // A very beautiful mock file diff for the demo
  const oldCode = [
    `import { useState } from 'react';`,
    `import { cn } from '@/lib/utils';`,
    ``,
    `export function LegacyContainer() {`,
    `  return (`,
    `    <div className="bg-stone-50 border border-stone-200 p-5 rounded-2xl">`,
    `      <h3 className="font-semibold text-[16px] mb-2 text-stone-900">`,
    `        Workspace Tasks`,
    `      </h3>`,
    `      <p className="text-[13px] font-light text-stone-500">`,
    `        Manage your automated routines here.`,
    `      </p>`,
    `    </div>`,
    `  );`,
    `}`
  ]

  const newCode = [
    `import { useState } from 'react';`,
    `import { cn } from '@/lib/utils';`,
    ``,
    `export function StandardContainer() {`,
    `  return (`,
    `    <div className="bg-white border border-stone-200/60 rounded-2xl shadow-[0_1px_8px_rgba(0,0,0,0.01)] hover:shadow-[0_4px_16px_rgba(0,0,0,0.02)] transition-all p-5">`,
    `      <h3 className="font-medium text-[15px] mb-1 text-stone-850">`,
    `        Workspace Tasks`,
    `      </h3>`,
    `      <p className="text-[13px] text-stone-400 font-normal">`,
    `        Manage your automated routines here.`,
    `      </p>`,
    `    </div>`,
    `  );`,
    `}`
  ]

  const handleAcceptClick = () => {
    setHasAccepted(true)
    setTimeout(() => {
      onAccept()
    }, 1000)
  }

  return (
    <div className="h-full flex flex-col bg-white">
      {/* Diff Header */}
      <div className="h-14 border-b border-stone-200/60 flex items-center justify-between px-6 bg-white shrink-0">
        <div className="flex items-center gap-2.5">
          <FileCode className="w-4 h-4 text-stone-400" strokeWidth={1.5} />
          <span className="font-medium text-[13px] text-stone-700">{filename}</span>
          <span className="text-[10px] text-stone-400 font-mono bg-stone-100 px-1.5 py-0.5 rounded-md">edited</span>
        </div>
        
        {/* Toggle modes & actions */}
        <div className="flex items-center gap-4">
          <div className="flex bg-stone-100 p-0.5 rounded-lg shrink-0">
            <button
              onClick={() => setViewMode("split")}
              className={cn(
                "p-1 rounded-md transition-all",
                viewMode === "split" ? "bg-white text-stone-800 shadow-sm" : "text-stone-400 hover:text-stone-600"
              )}
              title="Split View"
            >
              <Columns size={14} strokeWidth={1.5} />
            </button>
            <button
              onClick={() => setViewMode("unified")}
              className={cn(
                "p-1 rounded-md transition-all",
                viewMode === "unified" ? "bg-white text-stone-800 shadow-sm" : "text-stone-400 hover:text-stone-600"
              )}
              title="Unified View"
            >
              <Rows size={14} strokeWidth={1.5} />
            </button>
          </div>

          <div className="w-[1px] h-5 bg-stone-200"></div>

          <button onClick={onClose} className="p-1 text-stone-400 hover:text-stone-600 transition-colors">
            <X size={16} strokeWidth={1.5} />
          </button>
        </div>
      </div>

      {/* Code diff container */}
      <div className="flex-1 overflow-y-auto p-6 bg-stone-50/40 no-scrollbar">
        {hasAccepted ? (
          <div className="h-full flex flex-col items-center justify-center text-center p-8 animate-in fade-in duration-300">
            <div className="w-12 h-12 rounded-full bg-emerald-50 border border-emerald-100 flex items-center justify-center mb-4 text-emerald-500">
              <CheckCircle2 size={24} strokeWidth={1.5} />
            </div>
            <h3 className="text-[15px] font-medium text-stone-800">Changes Accepted Successfully</h3>
            <p className="text-[13px] text-stone-400 font-normal mt-1">Merging changes into master branch...</p>
          </div>
        ) : (
          <div className="border border-stone-200/60 bg-white rounded-2xl overflow-hidden shadow-[0_1px_8px_rgba(0,0,0,0.01)]">
            {viewMode === "split" ? (
              // Side by Side View
              <div className="grid grid-cols-2 divide-x divide-stone-100 text-[12.5px] font-mono leading-relaxed select-text">
                {/* Left Side: Legacy */}
                <div className="p-4 overflow-x-auto min-w-0">
                  <div className="text-[10px] font-sans font-semibold text-stone-400 uppercase tracking-widest mb-3">Legacy Code</div>
                  <div className="space-y-0.5">
                    {oldCode.map((line, idx) => {
                      const isChanged = idx >= 3 && idx <= 13
                      return (
                        <div
                          key={idx}
                          className={cn(
                            "px-2 py-0.5 rounded truncate",
                            isChanged ? "bg-red-50/50 text-red-700 line-through decoration-red-200" : "text-stone-500"
                          )}
                        >
                          <span className="w-5 inline-block text-stone-300 text-[10px] select-none font-sans mr-2">{idx + 1}</span>
                          {line || " "}
                        </div>
                      )
                    })}
                  </div>
                </div>

                {/* Right Side: Proposed */}
                <div className="p-4 overflow-x-auto min-w-0">
                  <div className="text-[10px] font-sans font-semibold text-stone-400 uppercase tracking-widest mb-3">Proposed Changes</div>
                  <div className="space-y-0.5">
                    {newCode.map((line, idx) => {
                      const isChanged = idx >= 3 && idx <= 13
                      return (
                        <div
                          key={idx}
                          className={cn(
                            "px-2 py-0.5 rounded truncate",
                            isChanged ? "bg-emerald-50/70 text-emerald-700 font-medium" : "text-stone-500"
                          )}
                        >
                          <span className="w-5 inline-block text-stone-300 text-[10px] select-none font-sans mr-2">{idx + 1}</span>
                          {line || " "}
                        </div>
                      )
                    })}
                  </div>
                </div>
              </div>
            ) : (
              // Unified View
              <div className="p-4 overflow-x-auto text-[12.5px] font-mono leading-relaxed select-text">
                <div className="space-y-0.5">
                  {/* First unchanged block */}
                  {[0, 1, 2].map(idx => (
                    <div key={idx} className="px-2 py-0.5 text-stone-500">
                      <span className="w-5 inline-block text-stone-300 text-[10px] select-none font-sans mr-2">{idx + 1}</span>
                      {oldCode[idx] || " "}
                    </div>
                  ))}

                  {/* Red/legacy block */}
                  {oldCode.slice(3, 14).map((line, idx) => (
                    <div key={`old-${idx}`} className="px-2 py-0.5 bg-red-50/50 text-red-700 line-through decoration-red-200 rounded">
                      <span className="w-5 inline-block text-stone-350 text-[10px] select-none font-sans mr-2">-</span>
                      {line}
                    </div>
                  ))}

                  {/* Green/proposed block */}
                  {newCode.slice(3, 14).map((line, idx) => (
                    <div key={`new-${idx}`} className="px-2 py-0.5 bg-emerald-50/70 text-emerald-700 font-medium rounded">
                      <span className="w-5 inline-block text-stone-350 text-[10px] select-none font-sans mr-2">+</span>
                      {line}
                    </div>
                  ))}

                  {/* End unchanged block */}
                  {[14].map(idx => (
                    <div key={idx} className="px-2 py-0.5 text-stone-500">
                      <span className="w-5 inline-block text-stone-300 text-[10px] select-none font-sans mr-2">{idx + 1}</span>
                      {oldCode[idx] || " "}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Floating Action Bar */}
      {!hasAccepted && (
        <div className="h-16 border-t border-stone-200/60 px-6 flex items-center justify-between bg-white shrink-0 shadow-[0_-4px_16px_rgba(0,0,0,0.01)]">
          <span className="text-[12px] text-stone-400">Review changes building block by building block</span>
          <div className="flex gap-2">
            <button
              onClick={onClose}
              className="px-3.5 py-1.5 border border-stone-200 text-stone-500 rounded-lg hover:bg-stone-50 transition-colors text-[12.5px] font-normal"
            >
              Reject
            </button>
            <button
              onClick={handleAcceptClick}
              className="flex items-center gap-1 px-4 py-1.5 bg-stone-900 hover:bg-stone-800 text-white rounded-lg text-[12.5px] font-normal transition-colors shadow-sm"
            >
              <Check size={14} className="mr-0.5" />
              <span>Accept Changes</span>
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
