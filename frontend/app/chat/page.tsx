import { ChatShell } from "@/components/chat/chat-shell"
import type { Metadata } from "next"
import { Suspense } from "react"

export const metadata: Metadata = {
  title: "Chat - AI Assistant",
  description: "Chat with our AI assistant powered by Sharrowkin",
}

export default function ChatPage() {
  return (
    <Suspense>
      <ChatShell />
    </Suspense>
  )
}
