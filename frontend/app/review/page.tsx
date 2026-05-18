import { ReviewShell } from "@/components/chat/review-shell"
import type { Metadata } from "next"

export const metadata: Metadata = {
  title: "Review - Sharrowkyn",
  description: "Code Review and Pull Requests",
}

export default function ReviewPage() {
  return <ReviewShell />
}
