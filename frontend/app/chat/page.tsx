import { ChatShell } from "@/components/chat/chat-shell"
import type { Metadata } from "next"

export const metadata: Metadata = {
  title: "Chat - AI Assistant",
  description: "Chat with our AI assistant powered by Gemini 3.1 Pro",
}

export default function ChatPage() {
  return <ChatShell />
}
