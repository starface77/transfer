'use client';

import { useState } from 'react';
import { Terminal, BookOpen, Settings } from 'lucide-react';
import { cn } from '@/lib/utils';

interface RightSidebarProps {
  isOpen: boolean;
  onToggle: () => void;
}

export function RightSidebar({ isOpen, onToggle }: RightSidebarProps) {
  const [activeTab, setActiveTab] = useState<string>('terminal');

  const tabs = [
    { id: 'terminal', label: 'Terminal', icon: Terminal },
    { id: 'logs', label: 'Logs', icon: BookOpen },
    { id: 'info', label: 'Info', icon: Settings },
  ];

  return (
    <>
      {/* Right Sidebar - Feather-light Apple-like aesthetic */}
      <aside className="hidden lg:flex flex-col w-[300px] bg-transparent border-l border-stone-100/80 overflow-hidden">
        
        {/* Segmented Control Header */}
        <div className="p-3 border-b border-stone-100/80">
          <div className="flex bg-stone-100/50 p-1 rounded-xl">
            {tabs.map((tab) => {
              const IconComponent = tab.icon;
              const isActive = activeTab === tab.id;
              
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={cn(
                    "flex-1 flex items-center justify-center gap-2 py-1.5 px-2 text-[12px] rounded-lg transition-all duration-200",
                    isActive
                      ? "bg-white text-stone-800 shadow-[0_1px_8px_rgba(0,0,0,0.03)] border border-stone-200/30"
                      : "text-stone-400 hover:text-stone-600"
                  )}
                >
                  <IconComponent size={14} strokeWidth={1.5} />
                  <span className="font-light">{tab.label}</span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Content Area */}
        <div className="flex-1 overflow-y-auto no-scrollbar">
          {activeTab === 'terminal' && (
            <div className="p-4 h-full">
              <div className="bg-white/50 border border-stone-200/40 shadow-[0_1px_8px_rgba(0,0,0,0.02)] rounded-2xl p-4 font-mono text-[11px] h-full flex flex-col text-stone-700">
                <div className="space-y-1.5 flex-1">
                  <div className="text-stone-400/80">{`>`} Agent started...</div>
                  <div className="text-stone-400/80">{`>`} Initializing workspace...</div>
                  <div className="text-stone-700">{`>`} Ready for input</div>
                  <div className="text-[10px] text-stone-400/50 mt-6">Type commands here</div>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'logs' && (
            <div className="p-4">
              <div className="space-y-4">
                <div className="text-[10px] font-medium text-stone-400/80 uppercase tracking-widest px-1">Recent Activity</div>
                <div className="space-y-3 px-1">
                  <div className="flex gap-3 text-[13px]">
                    <span className="text-stone-400/70 font-mono text-[10px] mt-0.5">14:32</span>
                    <span className="flex-1 text-stone-700 font-light">Agent connected</span>
                  </div>
                  <div className="flex gap-3 text-[13px]">
                    <span className="text-stone-400/70 font-mono text-[10px] mt-0.5">14:31</span>
                    <span className="flex-1 text-stone-500 font-light">Model initialized</span>
                  </div>
                  <div className="flex gap-3 text-[13px]">
                    <span className="text-stone-400/70 font-mono text-[10px] mt-0.5">14:30</span>
                    <span className="flex-1 text-stone-500 font-light">System ready</span>
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'info' && (
            <div className="p-4 space-y-5">
              <div className="px-1">
                <div className="text-[10px] font-medium text-stone-400/80 uppercase tracking-widest mb-2">Status</div>
                <div className="bg-white/50 border border-stone-200/40 shadow-[0_1px_8px_rgba(0,0,0,0.02)] rounded-xl p-3">
                  <div className="flex items-center gap-2.5 text-[13px]">
                    <div className="w-1.5 h-1.5 bg-emerald-400 rounded-full"></div>
                    <span className="text-stone-700 font-light">Online</span>
                  </div>
                </div>
              </div>
              <div className="px-1">
                <div className="text-[10px] font-medium text-stone-400/80 uppercase tracking-widest mb-2">Model</div>
                <div className="text-[13px] text-stone-700 font-light bg-white/50 border border-stone-200/40 shadow-[0_1px_8px_rgba(0,0,0,0.02)] rounded-xl p-3">
                  Google Gemini 2.0
                </div>
              </div>
              <div className="px-1">
                <div className="text-[10px] font-medium text-stone-400/80 uppercase tracking-widest mb-2">Version</div>
                <div className="text-[13px] text-stone-500 font-light bg-white/50 border border-stone-200/40 shadow-[0_1px_8px_rgba(0,0,0,0.02)] rounded-xl p-3">
                  1.0.0
                </div>
              </div>
            </div>
          )}
        </div>
      </aside>
    </>
  );
}
