import { WikiShell } from "@/components/chat/wiki-shell"
import type { Metadata } from "next"

export const metadata: Metadata = {
  title: "Wiki - Sharrowkyn",
  description: "Project Knowledge Base",
}

export default function WikiPage() {
  return <WikiShell />
}
