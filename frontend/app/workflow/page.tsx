"use client"

import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import { ArrowLeft, Loader2, FolderTree, RotateCw } from "lucide-react"
import { FileTree, type FileNode } from "@/components/workflow/file-tree"
import { CodeViewer } from "@/components/workflow/code-viewer"
import { LeftSidebar } from "@/components/chat/left-sidebar"

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "http://127.0.0.1:8000"

export default function WorkflowPage() {
  const router = useRouter()
  const [treeData, setTreeData] = useState<FileNode | null>(null)
  const [isLoadingTree, setIsLoadingTree] = useState(true)
  const [selectedFilePath, setSelectedFilePath] = useState<string | null>(null)
  const [selectedFileName, setSelectedFileName] = useState<string | null>(null)
  const [fileContent, setFileContent] = useState<string | null>(null)
  const [isLoadingFile, setIsLoadingFile] = useState(false)
  const [leftSidebarOpen, setLeftSidebarOpen] = useState(true)

  const fetchTree = async () => {
    setIsLoadingTree(true)
    try {
      const res = await fetch(`${BACKEND_URL}/api/workspace/tree`)
      if (res.ok) {
        const data = await res.json()
        setTreeData(data)
      }
    } catch (err) {
      console.error("Failed to fetch tree:", err)
    } finally {
      setIsLoadingTree(false)
    }
  }

  useEffect(() => {
    fetchTree()
  }, [])

  const handleSelectFile = async (path: string, name: string) => {
    setSelectedFilePath(path)
    setSelectedFileName(name)
    setIsLoadingFile(true)
    setFileContent(null)
    
    try {
      const res = await fetch(`${BACKEND_URL}/api/docs/content?filename=${encodeURIComponent(path)}`)
      if (res.ok) {
        const data = await res.json()
        setFileContent(data.content)
      } else {
        setFileContent("Failed to load file.")
      }
    } catch (err) {
      setFileContent(`Error loading file: ${err}`)
    } finally {
      setIsLoadingFile(false)
    }
  }

  return (
    <div className="h-dvh bg-background flex overflow-hidden">
      <LeftSidebar isOpen={leftSidebarOpen} onToggle={() => setLeftSidebarOpen(!leftSidebarOpen)} />

      <div className="flex-1 flex flex-col overflow-hidden bg-white font-sans relative z-10">
        {/* Header */}
        <header className="h-[52px] bg-white flex items-center justify-between px-5 shrink-0 border-b border-stone-100/50">
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2 text-stone-700 font-medium text-[13.5px]">
              <FolderTree size={16} className="text-emerald-500" />
              <span>Project Explorer</span>
            </div>
          </div>
          
          <button 
            onClick={fetchTree}
            className="flex items-center gap-1.5 px-3 py-1.5 text-[12px] font-medium text-stone-500 hover:text-stone-700 bg-stone-50 hover:bg-stone-100 border border-stone-200/60 rounded-md transition-colors"
            disabled={isLoadingTree}
          >
            <RotateCw size={13} className={isLoadingTree ? "animate-spin" : ""} />
            Refresh
          </button>
        </header>

        {/* Main Content */}
        <div className="flex-1 flex overflow-hidden">
          {/* Sidebar - File Tree */}
          <div className="w-[280px] bg-[#fafafa] flex flex-col shrink-0">
            <div className="px-4 py-3 flex items-center text-[12.5px] font-medium text-stone-600">
              Workspace Files
            </div>
            <div className="flex-1 overflow-y-auto px-2 pb-4">
              {isLoadingTree ? (
                <div className="flex flex-col items-center justify-center h-32 text-stone-400 gap-2">
                  <Loader2 className="w-5 h-5 animate-spin" />
                  <span className="text-[12px]">Loading tree...</span>
                </div>
              ) : treeData ? (
                <FileTree 
                  node={treeData} 
                  onSelectFile={handleSelectFile} 
                  selectedPath={selectedFilePath} 
                />
              ) : (
                <div className="p-4 text-center text-[12px] text-stone-500">
                  Failed to load workspace tree.
                </div>
              )}
            </div>
          </div>

          {/* Main - Code Viewer */}
          <div className="flex-1 overflow-hidden bg-white">
            <CodeViewer 
              filename={selectedFilePath} 
              content={fileContent} 
              isLoading={isLoadingFile} 
            />
          </div>
        </div>
      </div>
    </div>
  )
}
