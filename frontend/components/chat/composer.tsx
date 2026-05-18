"use client"

import type React from "react"
import { useState, useRef, useCallback, type KeyboardEvent, useEffect } from "react"
import { Square, Mic, MicOff, Paperclip, X, Sparkles, Plus } from "lucide-react"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  DropdownMenuPortal,
} from "@/components/ui/dropdown-menu"
import Image from "next/image"
import { AnimatedOrb } from "./animated-orb"
import { AudioWaveform } from "./audio-waveform"

export type AIModel = "google/gemini-2.0-flash-001" | "openai/gpt-4o" | "anthropic/claude-sonnet-4"

export const AI_MODELS: { id: AIModel; name: string; icon: string }[] = [
  { id: "google/gemini-2.0-flash-001", name: "Gemini", icon: "/images/google.webp" },
  { id: "openai/gpt-4o", name: "GPT-4o", icon: "/images/gpt.png" },
  { id: "anthropic/claude-sonnet-4", name: "Claude", icon: "/images/claude.svg" },
]

interface ComposerProps {
  onSend: (content: string, imageData?: string) => void
  onStop: () => void
  isStreaming: boolean
  disabled?: boolean
  selectedModel: AIModel
  onModelChange: (model: AIModel) => void
}

export function Composer({ onSend, onStop, isStreaming, disabled, selectedModel, onModelChange }: ComposerProps) {
  const [value, setValue] = useState("")
  const [isRecording, setIsRecording] = useState(false)
  const [uploadedImage, setUploadedImage] = useState<string | null>(null)
  const [showImageBounce, setShowImageBounce] = useState(false)
  const [hasAnimated, setHasAnimated] = useState(false)
  const [mediaStream, setMediaStream] = useState<MediaStream | null>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const recognitionRef = useRef<any>(null)
  const baseTextRef = useRef("")
  const finalTranscriptsRef = useRef("")

  useEffect(() => {
    if (typeof window !== "undefined") {
      const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition
      if (SpeechRecognition) {
        recognitionRef.current = new SpeechRecognition()
        recognitionRef.current.continuous = true
        recognitionRef.current.interimResults = true
        recognitionRef.current.lang = "en-US"

        recognitionRef.current.onresult = (event: any) => {
          let newFinalText = ""

          for (let i = event.resultIndex; i < event.results.length; i++) {
            if (event.results[i].isFinal) {
              const transcript = event.results[i][0].transcript
              newFinalText += transcript + " "
            }
          }

          if (newFinalText) {
            finalTranscriptsRef.current += newFinalText
            setValue(baseTextRef.current + finalTranscriptsRef.current)
            setTimeout(() => handleInput(), 0)
          }
        }

        recognitionRef.current.onerror = (event: any) => {
          console.error("[v0] Speech recognition error:", event.error)
          setIsRecording(false)
        }

        recognitionRef.current.onend = () => {
          setIsRecording(false)
        }
      }
    }

    return () => {
      if (recognitionRef.current) {
        recognitionRef.current.stop()
      }
    }
  }, [])

  useEffect(() => {
    setHasAnimated(true)
  }, [])

  const playClickSound = useCallback(() => {
    const audio = new Audio("https://hebbkx1anhila5yf.public.blob.vercel-storage.com/click-FM4Xaa1FJj237591TiZw4yL1fIxdOw.mp3")
    audio.volume = 0.5
    audio.play().catch(() => {})
  }, [])

  const toggleRecording = useCallback(() => {
    playClickSound()

    if (!recognitionRef.current) {
      alert("Speech recognition is not supported in your browser")
      return
    }

    if (isRecording) {
      recognitionRef.current.stop()
      setIsRecording(false)
      if (mediaStream) {
        mediaStream.getTracks().forEach((track) => track.stop())
        setMediaStream(null)
      }
    } else {
      baseTextRef.current = value
      finalTranscriptsRef.current = ""
      recognitionRef.current.start()
      setIsRecording(true)

      navigator.mediaDevices
        .getUserMedia({ audio: true })
        .then((stream) => {
          setMediaStream(stream)
        })
        .catch((err) => {
          console.error("Error getting microphone stream:", err)
        })
    }
  }, [isRecording, value, playClickSound, mediaStream])

  const handleInput = useCallback(() => {
    const textarea = textareaRef.current
    if (textarea) {
      textarea.style.height = "auto"
      textarea.style.height = `${Math.min(textarea.scrollHeight, 200)}px`
    }
  }, [])

  const handleSend = useCallback(() => {
    if ((!value.trim() && !uploadedImage) || isStreaming || disabled) return
    playClickSound()

    if (isRecording && recognitionRef.current) {
      recognitionRef.current.stop()
      setIsRecording(false)
    }
    onSend(value || "Describe this image", uploadedImage || undefined)
    setValue("")
    setUploadedImage(null)
    baseTextRef.current = ""
    finalTranscriptsRef.current = ""
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto"
    }
  }, [value, uploadedImage, isStreaming, disabled, onSend, isRecording, playClickSound])

  const handleKeyDown = useCallback(
    (e: KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault()
        handleSend()
      }
    },
    [handleSend],
  )

  const handleFileSelect = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      playClickSound()

      const file = e.target.files?.[0]
      if (file && file.type.startsWith("image/")) {
        const reader = new FileReader()
        reader.onload = (event) => {
          setUploadedImage(event.target?.result as string)
          setShowImageBounce(true)
          setTimeout(() => setShowImageBounce(false), 400)
        }
        reader.readAsDataURL(file)
      }
      e.target.value = ""
    },
    [playClickSound],
  )

  const removeImage = useCallback(() => {
    setUploadedImage(null)
  }, [])

  const currentModel = AI_MODELS.find((m) => m.id === selectedModel) || AI_MODELS[0]

  return (
    <div className={cn("fixed bottom-6 left-0 right-0 px-4 pointer-events-none z-10", hasAnimated && "composer-intro")}>
      <div className="relative max-w-3xl mx-auto pointer-events-auto">
        <div
          className={cn(
            "flex flex-col bg-white border border-stone-200/60 transition-all duration-300 relative rounded-[28px] overflow-hidden",
            "focus-within:border-stone-300 focus-within:shadow-[0_4px_24px_rgba(0,0,0,0.06)]",
            "shadow-[0_2px_12px_rgba(0,0,0,0.03)]"
          )}
        >
          {/* Uploaded Image Preview */}
          {uploadedImage && (
            <div className={cn("px-4 pt-4 pb-0 transition-all", showImageBounce && "image-bounce")}>
              <div className="relative inline-block">
                <div className="w-16 h-16 rounded-xl overflow-hidden border border-stone-200/60 shadow-sm">
                  <Image
                    src={uploadedImage || "/placeholder.svg"}
                    alt="Uploaded image"
                    width={64}
                    height={64}
                    className="w-full h-full object-cover"
                  />
                </div>
                <button
                  onClick={removeImage}
                  className="absolute -top-2 -right-2 w-5 h-5 bg-stone-100 border border-stone-200 text-stone-600 hover:bg-stone-200 rounded-full flex items-center justify-center transition-colors"
                  aria-label="Remove image"
                >
                  <X className="w-3 h-3" />
                </button>
              </div>
            </div>
          )}

          {/* Text Input Area */}
          <div className="flex px-4 pt-3 pb-1">
            <textarea
              ref={textareaRef}
              value={value}
              onChange={(e) => {
                setValue(e.target.value)
                handleInput()
              }}
              onKeyDown={handleKeyDown}
              placeholder={isRecording ? "Listening..." : "Message Sharrowkyn..."}
              disabled={isStreaming || disabled}
              rows={1}
              className={cn(
                "flex-1 resize-none bg-transparent py-1.5 text-[15px] font-light text-stone-800 placeholder:text-stone-400/80 leading-relaxed",
                "focus:outline-none disabled:opacity-50 disabled:cursor-not-allowed",
                "max-h-[200px] overflow-y-auto no-scrollbar",
              )}
              aria-label="Message input"
            />
          </div>

          {/* Bottom Toolbar */}
          <div className="flex items-center justify-between px-3 pb-3 pt-1">
            <div className="flex items-center gap-1">
              
              {/* Attachment Button */}
              <Button
                onClick={() => {
                  playClickSound()
                  fileInputRef.current?.click()
                }}
                disabled={isStreaming || disabled}
                variant="ghost"
                size="icon"
                className="h-8 w-8 rounded-full text-stone-500 hover:text-stone-800 hover:bg-stone-100 transition-colors"
                aria-label="Attach file"
              >
                <Plus strokeWidth={2} className="w-[18px] h-[18px]" />
              </Button>
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                onChange={handleFileSelect}
                className="hidden"
                aria-label="Upload image"
              />

              {/* Model Dropdown */}
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button
                    variant="ghost"
                    disabled={isStreaming || disabled}
                    className="h-8 px-2.5 rounded-full text-stone-500 hover:text-stone-800 hover:bg-stone-100 transition-colors flex items-center gap-1.5 font-medium text-[12px]"
                    onClick={playClickSound}
                  >
                    <Sparkles strokeWidth={2} className="w-[14px] h-[14px]" />
                    <span>{currentModel.name}</span>
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuPortal>
                  <DropdownMenuContent
                    align="start"
                    side="top"
                    sideOffset={12}
                    className="w-44 p-1.5 rounded-[16px] border border-stone-200/60 shadow-lg bg-white/90 backdrop-blur-xl z-[9999]"
                  >
                    {AI_MODELS.map((model) => (
                      <DropdownMenuItem
                        key={model.id}
                        onClick={() => {
                          playClickSound()
                          onModelChange(model.id)
                        }}
                        className={cn(
                          "flex items-center cursor-pointer gap-2.5 rounded-[10px] px-2.5 py-2 text-[13px] text-stone-700 transition-colors",
                          selectedModel === model.id ? "bg-stone-100 font-medium text-stone-900" : "hover:bg-stone-50"
                        )}
                      >
                        <Image
                          src={model.icon || "/placeholder.svg"}
                          alt={model.name}
                          width={16}
                          height={16}
                          className="rounded-sm object-contain"
                        />
                        <span>{model.name}</span>
                      </DropdownMenuItem>
                    ))}
                  </DropdownMenuContent>
                </DropdownMenuPortal>
              </DropdownMenu>
            </div>

            <div className="flex items-center gap-2">
              {/* Audio visualizer */}
              {isRecording && (
                <div className="shrink-0 w-20 mr-2">
                  <AudioWaveform isRecording={isRecording} stream={mediaStream} />
                </div>
              )}
              
              {/* Mic Button */}
              <Button
                onClick={toggleRecording}
                disabled={isStreaming || disabled}
                variant="ghost"
                size="icon"
                className={cn(
                  "h-8 w-8 rounded-full transition-colors",
                  isRecording
                    ? "bg-red-50 text-red-500 hover:bg-red-100 hover:text-red-600 animate-pulse"
                    : "text-stone-500 hover:text-stone-800 hover:bg-stone-100"
                )}
                aria-label={isRecording ? "Stop recording" : "Start voice input"}
              >
                {isRecording ? <MicOff strokeWidth={2} className="w-[16px] h-[16px]" /> : <Mic strokeWidth={2} className="w-[16px] h-[16px]" />}
              </Button>

              {/* Send / Stop Button */}
              {isStreaming ? (
                <button
                  onClick={() => {
                    playClickSound()
                    onStop()
                  }}
                  className="relative h-8 w-8 shrink-0 transition-transform rounded-full flex items-center justify-center cursor-pointer hover:scale-105 active:scale-95"
                  aria-label="Stop generating"
                >
                  <AnimatedOrb size={32} variant="red" />
                  <Square
                    className="w-3.5 h-3.5 absolute drop-shadow-sm text-red-800"
                    fill="currentColor"
                    aria-hidden="true"
                  />
                </button>
              ) : (
                <button
                  onClick={handleSend}
                  disabled={(!value.trim() && !uploadedImage) || disabled}
                  className={cn(
                    "relative h-8 w-8 shrink-0 transition-transform rounded-full flex items-center justify-center",
                    (!value.trim() && !uploadedImage) || disabled
                      ? "opacity-40 cursor-not-allowed grayscale"
                      : "cursor-pointer hover:scale-105 active:scale-95",
                  )}
                  aria-label="Send message"
                >
                  <AnimatedOrb size={32} />
                </button>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
