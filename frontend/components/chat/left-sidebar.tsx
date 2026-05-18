'use client';

import { useState } from 'react';
import { ChevronDown, Menu, X, Plus, MessageSquare, BookOpen, CheckSquare2, Zap, History, Search } from 'lucide-react';

interface LeftSidebarProps {
  isOpen: boolean;
  onToggle: () => void;
}

export function LeftSidebar({ isOpen, onToggle }: LeftSidebarProps) {
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({
    sessions: true,
    recent: false,
  });

  const toggleSection = (section: string) => {
    setExpandedSections((prev) => ({
      ...prev,
      [section]: !prev[section],
    }));
  };

  return (
    <>
      {/* Mobile Toggle Button */}
      <button
        onClick={onToggle}
        className="fixed left-4 top-4 z-50 lg:hidden p-2 hover:bg-stone-100 rounded-full transition-colors"
        aria-label="Toggle sidebar"
      >
        {isOpen ? <X strokeWidth={1.5} size={20} className="text-stone-700" /> : <Menu strokeWidth={1.5} size={20} className="text-stone-700" />}
      </button>

      {/* Sidebar - Feather-light Apple-like aesthetic */}
      <aside
        className={`
          fixed lg:relative z-40 h-full w-[260px] bg-transparent
          transition-transform duration-300 ease-in-out
          ${isOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
          flex flex-col overflow-hidden border-r border-stone-100/80
        `}
      >
        {/* Header */}
        <div className="px-4 pt-6 pb-2">
          <button className="w-full flex items-center justify-between px-3 py-2 bg-white/50 border border-stone-200/30 rounded-[12px] hover:bg-white transition-colors shadow-[0_1px_8px_rgba(0,0,0,0.02)] group">
            <span className="text-[13px] font-light text-stone-600 group-hover:text-stone-900 transition-colors">New Chat</span>
            <Plus strokeWidth={1.5} size={16} className="text-stone-400 group-hover:text-stone-600 transition-colors" />
          </button>
        </div>

        {/* Main Navigation */}
        <div className="flex-1 overflow-y-auto px-3 py-2 space-y-4 no-scrollbar">
          
          {/* Main Links */}
          <div className="space-y-0.5">
            {[
              { icon: MessageSquare, label: 'Chat', active: true },
              { icon: BookOpen, label: 'Wiki', active: false },
              { icon: CheckSquare2, label: 'Review', active: false },
              { icon: Zap, label: 'Automations', active: false },
            ].map(({ icon: Icon, label, active }) => (
              <button
                key={label}
                className={`w-full flex items-center gap-3 px-3 py-2 rounded-xl transition-colors ${
                  active ? 'bg-white shadow-[0_1px_8px_rgba(0,0,0,0.02)] border border-stone-200/30 text-stone-900' : 'text-stone-500 hover:bg-stone-200/20 hover:text-stone-900'
                }`}
              >
                <Icon size={16} strokeWidth={active ? 1.5 : 1.5} className={active ? 'text-stone-800' : 'text-stone-400'} />
                <span className={`text-[13px] font-light ${active ? 'text-stone-800 font-normal' : ''}`}>{label}</span>
              </button>
            ))}
          </div>

          {/* Sessions Section */}
          <div className="pt-2">
            <button
              onClick={() => toggleSection('sessions')}
              className="w-full flex items-center justify-between px-3 py-1.5 group"
            >
              <span className="text-[11px] font-medium text-stone-400/80 uppercase tracking-widest group-hover:text-stone-500 transition-colors">Sessions</span>
              <ChevronDown
                strokeWidth={1.5}
                size={14}
                className={`text-stone-400/70 transition-transform duration-200 ${expandedSections.sessions ? 'rotate-0' : '-rotate-90'}`}
              />
            </button>
            
            {expandedSections.sessions && (
              <div className="mt-1 space-y-0.5">
                {[
                  { label: 'Clone starface77/NareCLI', active: true },
                  { label: 'Web Scraping Agent', active: false },
                  { label: 'Code Review Session', active: false },
                ].map((session) => (
                  <button
                    key={session.label}
                    className={`w-full flex items-center gap-3 px-3 py-2 rounded-xl transition-colors ${
                      session.active
                        ? 'bg-stone-200/30 text-stone-900'
                        : 'text-stone-500 hover:bg-stone-200/20 hover:text-stone-900'
                    }`}
                  >
                    <div className="flex-1 text-left truncate text-[13px] font-light">{session.label}</div>
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Recent Section */}
          <div className="pt-2">
            <button
              onClick={() => toggleSection('recent')}
              className="w-full flex items-center justify-between px-3 py-1.5 group"
            >
              <span className="text-[11px] font-medium text-stone-400/80 uppercase tracking-widest group-hover:text-stone-500 transition-colors">Recent</span>
              <ChevronDown
                strokeWidth={1.5}
                size={14}
                className={`text-stone-400/70 transition-transform duration-200 ${expandedSections.recent ? 'rotate-0' : '-rotate-90'}`}
              />
            </button>
            
            {expandedSections.recent && (
              <div className="mt-1 space-y-0.5">
                <button className="w-full flex items-center gap-3 px-3 py-2 rounded-xl text-stone-500 hover:bg-stone-200/20 hover:text-stone-900 transition-colors">
                  <div className="flex-1 text-left min-w-0">
                    <div className="text-[13px] truncate font-light">Refactoring API endpoints</div>
                    <div className="text-[11px] text-stone-400/70 mt-0.5 font-mono">Yesterday</div>
                  </div>
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-stone-100/80">
          <button className="w-full flex items-center gap-3 px-3 py-2 text-stone-500 hover:bg-stone-200/20 hover:text-stone-900 rounded-xl transition-colors">
            <div className="w-6 h-6 rounded-full bg-stone-100 flex items-center justify-center shrink-0">
              <span className="text-[10px] font-medium text-stone-500">D</span>
            </div>
            <span className="text-[13px] font-light">Danik</span>
          </button>
        </div>
      </aside>

      {/* Mobile Overlay */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-stone-900/10 backdrop-blur-sm z-30 lg:hidden transition-opacity"
          onClick={onToggle}
        />
      )}
    </>
  );
}
