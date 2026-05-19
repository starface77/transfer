"use client"

import React, { useState, useEffect, useCallback, useMemo } from "react"
import { 
  CheckSquare2, 
  Plus, 
  Trash2, 
  Search, 
  Sparkles, 
  CheckCircle2, 
  Circle, 
  Tag, 
  Clock, 
  ArrowRight,
  ChevronDown,
  ChevronUp,
  TrendingUp,
  X
} from "lucide-react"
import { cn } from "@/lib/utils"

export interface SubTask {
  id: string
  title: string
  completed: boolean
}

export interface Todo {
  id: string
  title: string
  description: string
  priority: "high" | "medium" | "low"
  category: "NARE-Field" | "DSM" | "RLD" | "Frontend" | "General"
  completed: boolean
  dueDate?: string
  subtasks: SubTask[]
  createdAt: string
}

export function AgentTasks() {
  const [todos, setTodos] = useState<Todo[]>([])
  const [selectedTodoId, setSelectedTodoId] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState("")

  const [isFormOpen, setIsFormOpen] = useState(false)
  const [newTitle, setNewTitle] = useState("")
  const [newDescription, setNewDescription] = useState("")
  const [newCategory, setNewCategory] = useState<Todo["category"]>("General")

  // Load from localStorage
  useEffect(() => {
    const stored = localStorage.getItem("sharrowkin-todo-items")
    if (stored) {
      try {
        setTodos(JSON.parse(stored))
      } catch (e) {
        console.error("Failed to parse todos:", e)
      }
    }
  }, [])

  // Persist to localStorage
  const saveTodos = useCallback((updated: Todo[]) => {
    setTodos(updated)
    localStorage.setItem("sharrowkin-todo-items", JSON.stringify(updated))
  }, [])

  // Toggle todo completion
  const handleToggleTodo = useCallback((id: string, e?: React.MouseEvent) => {
    if (e) e.stopPropagation()
    const updated = todos.map(todo => {
      if (todo.id === id) {
        return { ...todo, completed: !todo.completed }
      }
      return todo
    })
    saveTodos(updated)
  }, [todos, saveTodos])

  // Toggle subtask completion
  const handleToggleSubtask = useCallback((todoId: string, subtaskId: string) => {
    const updated = todos.map(todo => {
      if (todo.id === todoId) {
        const nextSubtasks = todo.subtasks.map(sub => 
          sub.id === subtaskId ? { ...sub, completed: !sub.completed } : sub
        )
        return { ...todo, subtasks: nextSubtasks }
      }
      return todo
    })
    saveTodos(updated)
  }, [todos, saveTodos])

  // Create task
  const handleCreateTask = useCallback((e: React.FormEvent) => {
    e.preventDefault()
    if (!newTitle.trim()) return

    const newTodo: Todo = {
      id: `TODO-${todos.length + 100}`,
      title: newTitle.trim(),
      description: newDescription.trim(),
      priority: "medium",
      category: newCategory,
      completed: false,
      subtasks: [],
      createdAt: new Date().toISOString()
    }

    const updated = [newTodo, ...todos]
    saveTodos(updated)
    setIsFormOpen(false)
    setNewTitle("")
    setNewDescription("")
  }, [todos, newTitle, newDescription, newCategory, saveTodos])

  const filteredTodos = useMemo(() => {
    return todos.filter(todo => {
      return todo.title.toLowerCase().includes(searchQuery.toLowerCase()) || 
             todo.description.toLowerCase().includes(searchQuery.toLowerCase())
    })
  }, [todos, searchQuery])

  const completionStats = useMemo(() => {
    const total = todos.length
    const completed = todos.filter(t => t.completed).length
    const percent = total > 0 ? Math.round((completed / total) * 100) : 0
    return { total, completed, percent }
  }, [todos])

  return (
    <div className="flex flex-col h-full bg-white relative">
      {/* Header */}
      <div className="px-5 py-4 border-b border-stone-200/60 shrink-0">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-lg bg-emerald-50 border border-emerald-100 flex items-center justify-center">
              <CheckSquare2 size={14} className="text-emerald-600" />
            </div>
            <div className="flex flex-col">
              <span className="text-[13px] font-medium text-stone-850">Agent Tasks</span>
              <span className="text-[10px] font-mono text-stone-400">{completionStats.completed}/{completionStats.total} completed ({completionStats.percent}%)</span>
            </div>
          </div>
          <button
            onClick={() => setIsFormOpen(true)}
            className="w-7 h-7 rounded-full bg-stone-900 hover:bg-stone-850 text-white flex items-center justify-center transition-colors shadow-sm"
          >
            <Plus size={14} />
          </button>
        </div>

        {/* Progress Bar */}
        <div className="w-full h-1.5 bg-stone-100 rounded-full overflow-hidden mb-4">
          <div className="bg-emerald-500 h-full transition-all duration-500" style={{ width: `${completionStats.percent}%` }} />
        </div>

        {/* Search */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-stone-300" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search active tasks..."
            className="w-full pl-9 pr-3 py-1.5 border border-stone-200 rounded-lg text-[12px] placeholder:text-stone-400 focus:outline-none focus:border-stone-400/80 bg-stone-50/30 font-sans"
          />
        </div>
      </div>

      {/* Task List */}
      <div className="flex-1 overflow-y-auto no-scrollbar">
        {filteredTodos.length === 0 ? (
          <div className="p-8 text-center flex flex-col items-center justify-center text-stone-300 h-full">
            <CheckSquare2 className="w-8 h-8 stroke-[1.5] mb-2" />
            <div className="text-[12px] font-sans">No tasks found</div>
          </div>
        ) : (
          <div className="divide-y divide-stone-100/80">
            {filteredTodos.map((todo) => {
              const isSelected = selectedTodoId === todo.id
              return (
                <div key={todo.id} className={cn("flex flex-col transition-colors", isSelected ? "bg-stone-50/50" : "hover:bg-stone-50/30")}>
                  <div 
                    onClick={() => setSelectedTodoId(isSelected ? null : todo.id)}
                    className="flex items-start gap-3 px-5 py-3.5 cursor-pointer select-none"
                  >
                    <button 
                      onClick={(e) => handleToggleTodo(todo.id, e)}
                      className="shrink-0 mt-0.5 text-stone-300 hover:text-stone-600 transition-colors"
                    >
                      {todo.completed ? (
                        <CheckCircle2 size={16} className="text-emerald-500" strokeWidth={2} />
                      ) : (
                        <Circle size={16} strokeWidth={1.5} />
                      )}
                    </button>
                    <div className="flex flex-col flex-1 min-w-0">
                      <span className={cn(
                        "text-[12.5px] font-medium leading-tight font-sans truncate",
                        todo.completed ? "text-stone-400 line-through" : "text-stone-800"
                      )}>
                        {todo.title}
                      </span>
                      <div className="flex items-center gap-2 mt-1.5 flex-wrap">
                        <span className="text-[9px] px-1.5 py-0.5 rounded border border-stone-200/60 bg-white text-stone-500 font-sans uppercase tracking-wider">{todo.category}</span>
                        {todo.subtasks.length > 0 && (
                          <span className="text-[10px] text-stone-400 font-mono">
                            {todo.subtasks.filter(s => s.completed).length}/{todo.subtasks.length} steps
                          </span>
                        )}
                      </div>
                    </div>
                    <div className="shrink-0 text-stone-300">
                      {isSelected ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                    </div>
                  </div>

                  {/* Expanded View */}
                  {isSelected && (
                    <div className="px-5 pb-4 pt-1 animate-in fade-in slide-in-from-top-2 duration-200">
                      <div className="pl-7 space-y-3">
                        {todo.description && (
                          <p className="text-[11.5px] text-stone-500 leading-relaxed font-sans">{todo.description}</p>
                        )}
                        
                        {todo.subtasks.length > 0 && (
                          <div className="space-y-1.5 pt-1 border-t border-stone-100/80">
                            {todo.subtasks.map((sub) => (
                              <div key={sub.id} className="flex items-start gap-2.5 group">
                                <button 
                                  onClick={() => handleToggleSubtask(todo.id, sub.id)}
                                  className="shrink-0 mt-[1.5px] text-stone-300 group-hover:text-stone-500 transition-colors"
                                >
                                  {sub.completed ? (
                                    <CheckCircle2 size={13} className="text-emerald-500" strokeWidth={2} />
                                  ) : (
                                    <Circle size={13} strokeWidth={1.5} />
                                  )}
                                </button>
                                <span className={cn(
                                  "text-[11.5px] font-sans leading-snug",
                                  sub.completed ? "text-stone-400 line-through" : "text-stone-700"
                                )}>
                                  {sub.title}
                                </span>
                              </div>
                            ))}
                          </div>
                        )}
                        
                        {!todo.completed && (
                          <div className="pt-2">
                            <button
                              onClick={() => {
                                // Direct custom event to chat composer!
                                window.dispatchEvent(new CustomEvent("sharrowkin-insert-prompt", {
                                  detail: `Please review and help me implement the task: "${todo.title}"\n${todo.description}`
                                }))
                              }}
                              className="w-full flex items-center justify-center gap-1.5 py-1.5 px-3 bg-stone-100 hover:bg-stone-200 text-stone-700 rounded-lg text-[11px] font-medium transition-colors font-sans"
                            >
                              <Sparkles size={12} className="text-emerald-600" />
                              <span>Ask Agent to Implement</span>
                            </button>
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        )}
      </div>

      {/* Create Modal */}
      {isFormOpen && (
        <div className="absolute inset-0 bg-white z-50 flex flex-col animate-in slide-in-from-bottom-4 duration-300">
          <div className="px-5 py-4 border-b border-stone-200/60 flex items-center justify-between shrink-0 bg-stone-50/50">
            <span className="text-[13px] font-medium text-stone-850">New Agent Task</span>
            <button
              onClick={() => setIsFormOpen(false)}
              className="p-1.5 hover:bg-stone-200 rounded-full text-stone-400 hover:text-stone-600 transition-colors"
            >
              <X size={14} />
            </button>
          </div>
          <form onSubmit={handleCreateTask} className="p-5 flex-1 overflow-y-auto space-y-4">
            <div className="space-y-1.5">
              <label className="text-[10px] font-medium text-stone-400 uppercase tracking-widest block font-sans">Task Title</label>
              <input
                type="text"
                required
                value={newTitle}
                onChange={(e) => setNewTitle(e.target.value)}
                placeholder="e.g. Implement prediction loss"
                className="w-full px-3 py-2 border border-stone-200 rounded-xl text-[12px] focus:outline-none focus:border-stone-400 bg-stone-50/30 font-sans"
              />
            </div>
            <div className="space-y-1.5">
              <label className="text-[10px] font-medium text-stone-400 uppercase tracking-widest block font-sans">Description</label>
              <textarea
                rows={3}
                value={newDescription}
                onChange={(e) => setNewDescription(e.target.value)}
                placeholder="Details for the agent..."
                className="w-full px-3 py-2 border border-stone-200 rounded-xl text-[12px] focus:outline-none focus:border-stone-400 bg-stone-50/30 resize-none font-sans"
              />
            </div>
            <div className="space-y-1.5">
              <label className="text-[10px] font-medium text-stone-400 uppercase tracking-widest block font-sans">Module / Category</label>
              <select
                value={newCategory}
                onChange={(e) => setNewCategory(e.target.value as any)}
                className="w-full px-3 py-2 border border-stone-200 rounded-xl text-[12px] focus:outline-none focus:border-stone-400 bg-white font-sans text-stone-700"
              >
                <option value="General">General</option>
                <option value="NARE-Field">NARE-Field</option>
                <option value="DSM">DSM</option>
                <option value="RLD">RLD</option>
              </select>
            </div>
          </form>
          <div className="p-5 pt-0 mt-auto shrink-0">
            <button
              type="submit"
              onClick={handleCreateTask}
              disabled={!newTitle.trim()}
              className="w-full py-2.5 bg-stone-900 text-white rounded-xl text-[12px] hover:bg-stone-850 font-medium shadow-sm transition-colors disabled:opacity-40 font-sans"
            >
              Add Task
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
