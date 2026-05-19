'use client';

import { useState, useEffect, useCallback } from 'react';
import Image from 'next/image';
import Link from 'next/link';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';
import { ChevronDown, Menu, X, Plus, MessageSquare, BookOpen, CheckSquare2, Settings } from 'lucide-react';
import { cn } from '@/lib/utils';

interface LeftSidebarProps {
  isOpen: boolean;
  onToggle: () => void;
}

export function LeftSidebar({ isOpen, onToggle }: LeftSidebarProps) {
  const pathname = usePathname();
  const router = useRouter();
  const searchParams = useSearchParams();
  const activeSessionId = searchParams?.get('session') || 'session-1';

  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({
    sessions: true,
    recent: true,
  });

  // --- SESSIONS STATE ---
  const [sessions, setSessions] = useState<Array<{ id: string; label: string }>>([]);

  // --- RECENT COMMANDS STATE ---
  const [recentCommands, setRecentCommands] = useState<string[]>([]);

  // Load sessions and recent commands on mount
  useEffect(() => {
    // 1. Sessions List
    const storedSessions = localStorage.getItem('sharrowkin-sessions-list');
    if (storedSessions) {
      setSessions(JSON.parse(storedSessions));
    } else {
      const defaultSessions = [
        { id: 'session-1', label: 'Clone starface77/NareCLI' },
        { id: 'session-2', label: 'Web Scraping Agent' },
        { id: 'session-3', label: 'Code Review Session' },
      ];
      localStorage.setItem('sharrowkin-sessions-list', JSON.stringify(defaultSessions));
      setSessions(defaultSessions);
    }

    // 2. Recent Commands List
    const storedCommands = localStorage.getItem('sharrowkin-recent-commands');
    if (storedCommands) {
      setRecentCommands(JSON.parse(storedCommands));
    } else {
      const defaultCommands = ['dsm status', 'npm run build', 'git status'];
      localStorage.setItem('sharrowkin-recent-commands', JSON.stringify(defaultCommands));
      setRecentCommands(defaultCommands);
    }
  }, []);

  // Watch for custom event updates to recent commands (when user submits a command in terminal)
  useEffect(() => {
    const handleCommandsUpdate = () => {
      const storedCommands = localStorage.getItem('sharrowkin-recent-commands');
      if (storedCommands) {
        setRecentCommands(JSON.parse(storedCommands));
      }
    };
    window.addEventListener('sharrowkin-commands-updated', handleCommandsUpdate);
    return () => window.removeEventListener('sharrowkin-commands-updated', handleCommandsUpdate);
  }, []);

  // Add a new session
  const handleNewChat = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    const newId = `session-${Date.now()}`;
    const newSession = {
      id: newId,
      label: `New Chat Session ${sessions.length + 1}`,
    };
    const updatedSessions = [newSession, ...sessions];
    localStorage.setItem('sharrowkin-sessions-list', JSON.stringify(updatedSessions));
    setSessions(updatedSessions);

    // Redirect to the new chat session page
    router.push(`/chat?session=${newId}`);
  }, [sessions, router]);

  // Click on a recent command (sends it directly to the terminal on the right side)
  const handleCommandClick = useCallback((cmd: string) => {
    // Custom window event which is listened to by the active TerminalEmulator component
    window.dispatchEvent(new CustomEvent('sharrowkin-terminal-cmd', { detail: cmd }));
  }, []);

  // --- APPLE MINIMALIST SIDEBAR RESIZING ---
  const [width, setWidth] = useState(260);
  const [isResizing, setIsResizing] = useState(false);

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    setIsResizing(true);
    const startX = e.clientX;
    const startWidth = width;

    const doDrag = (moveEvent: MouseEvent) => {
      const deltaX = moveEvent.clientX - startX;
      const nextWidth = Math.max(200, Math.min(startWidth + deltaX, 380));
      setWidth(nextWidth);
    };

    const stopDrag = () => {
      setIsResizing(false);
      document.removeEventListener('mousemove', doDrag);
      document.removeEventListener('mouseup', stopDrag);
    };

    document.addEventListener('mousemove', doDrag);
    document.addEventListener('mouseup', stopDrag);
  }, [width]);

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
        style={{ width: isOpen ? `${width}px` : '0px' }}
        className={cn(
          "fixed lg:relative z-40 h-full bg-stone-50/50 flex flex-col overflow-hidden border-r border-stone-200/60 select-none relative shrink-0",
          isResizing ? "transition-none" : "transition-all duration-300 ease-in-out",
          !isOpen && "border-none"
        )}
      >

        {/* Apple Style Resizer handle on the right edge */}
        {isOpen && (
          <div
            onMouseDown={handleMouseDown}
            className="absolute top-0 right-0 w-1.5 h-full cursor-col-resize hover:bg-stone-200/50 active:bg-stone-300/60 transition-colors z-50 group flex items-center justify-center"
            title="Drag right edge to resize"
          >
            <div className="w-[1.5px] h-8 bg-stone-200/40 group-hover:bg-stone-400/60 group-active:bg-stone-500 rounded-full transition-colors" />
          </div>
        )}

        {/* Branding Header */}
        <div className="px-5 pt-7 pb-4 flex items-center gap-2.5">
          <div className="flex items-center justify-center shrink-0 w-6 h-6">
            <Image
              src="/images/logo.png"
              alt="NARE Labs"
              width={24}
              height={24}
              quality={100}
              priority
              unoptimized
              className="opacity-90 drop-shadow-sm object-contain"
            />
          </div>
          <span className="text-[13.5px] font-semibold text-stone-800 tracking-tight">Sharrowkin</span>
          <span className="text-[10px] font-medium text-stone-500 bg-stone-100 border border-stone-200/50 px-1.5 py-0.5 rounded-md ml-1 leading-none">Beta</span>
        </div>

        {/* New Chat Button */}
        <div className="px-4 pb-2">
          <button
            onClick={handleNewChat}
            className="w-full flex items-center justify-between px-3 py-2 bg-transparent hover:bg-stone-100/60 transition-colors rounded-[10px] group"
          >
            <span className="text-[13px] font-medium text-stone-600 group-hover:text-stone-900 transition-colors">New Chat</span>
            <Plus strokeWidth={1.5} size={16} className="text-stone-400 group-hover:text-stone-600 transition-colors" />
          </button>
        </div>

        {/* Main Navigation */}
        <div className="flex-1 overflow-y-auto px-3 py-2 space-y-4 no-scrollbar">

          {/* Main Links */}
          <div className="space-y-0.5">
            {[
              { icon: MessageSquare, label: 'Chat', href: '/chat' },
              { icon: BookOpen, label: 'Wiki', href: '/wiki' },
              { icon: CheckSquare2, label: 'Review', href: '/review' },
              { icon: Settings, label: 'Settings', href: '/settings' },
            ].map(({ icon: Icon, label, href }) => {
              const active = pathname?.startsWith(href);
              return (
                <Link
                  key={label}
                  href={href === '/chat' ? `/chat?session=${activeSessionId}` : href}
                  className={cn(
                    "w-full flex items-center gap-3 px-3 py-2 rounded-xl transition-all duration-150 border border-transparent",
                    active
                      ? 'bg-white shadow-[0_1px_8px_rgba(0,0,0,0.02)] border-stone-200/30 text-stone-900 font-medium'
                      : 'text-stone-500 hover:bg-stone-200/20 hover:text-stone-900'
                  )}
                >
                  <Icon size={16} strokeWidth={active ? 1.5 : 1.5} className={active ? 'text-stone-850' : 'text-stone-400'} />
                  <span className="text-[13px] font-normal">{label}</span>
                </Link>
              );
            })}
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
                {sessions.map((session) => {
                  const isActive = activeSessionId === session.id;
                  return (
                    <button
                      key={session.id}
                      onClick={() => router.push(`/chat?session=${session.id}`)}
                      className={cn(
                        "w-full flex items-center gap-3 px-3 py-2 rounded-xl transition-colors text-left",
                        isActive
                          ? 'bg-stone-200/30 text-stone-900 font-medium'
                          : 'text-stone-500 hover:bg-stone-200/20 hover:text-stone-900'
                      )}
                    >
                      <div className="flex-1 truncate text-[13px] font-normal">{session.label}</div>
                    </button>
                  );
                })}
              </div>
            )}
          </div>

          {/* Recent Commands Section */}
          <div className="pt-2">
            <button
              onClick={() => toggleSection('recent')}
              className="w-full flex items-center justify-between px-3 py-1.5 group"
            >
              <span className="text-[11px] font-medium text-stone-400/80 uppercase tracking-widest group-hover:text-stone-500 transition-colors">Recent Commands</span>
              <ChevronDown
                strokeWidth={1.5}
                size={14}
                className={`text-stone-400/70 transition-transform duration-200 ${expandedSections.recent ? 'rotate-0' : '-rotate-90'}`}
              />
            </button>

            {expandedSections.recent && (
              <div className="mt-1 space-y-0.5">
                {recentCommands.map((cmd, index) => (
                  <button
                    key={index}
                    onClick={() => handleCommandClick(cmd)}
                    className="w-full flex items-center gap-3 px-3 py-2 rounded-xl text-stone-500 hover:bg-stone-200/20 hover:text-stone-900 transition-colors text-left"
                    title="Click to paste command into terminal"
                  >
                    <div className="flex-1 min-w-0">
                      <div className="text-[12.5px] truncate font-mono text-stone-600">$ {cmd}</div>
                    </div>
                  </button>
                ))}
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
            <span className="text-[13px] font-normal">Danik</span>
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
