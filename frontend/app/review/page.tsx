import { ReviewShell } from "@/components/chat/review-shell"
import type { Metadata } from "next"
import { Suspense } from "react"

export const metadata: Metadata = {
  title: "Review - sharrowkin",
  description: "Code Review and Pull Requests",
}

export default function ReviewPage() {
  return (
    <Suspense>
      <ReviewShell />
    </Suspense>
  )
}
