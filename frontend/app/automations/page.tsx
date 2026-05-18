import { AutomationsShell } from "@/components/chat/automations-shell"
import type { Metadata } from "next"

export const metadata: Metadata = {
  title: "Automations - Sharrowkyn",
  description: "Manage autonomous agents and workflows",
}

export default function AutomationsPage() {
  return <AutomationsShell />
}
