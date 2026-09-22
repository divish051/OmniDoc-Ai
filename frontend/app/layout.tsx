import type { Metadata } from "next"
import "./globals.css"

export const metadata: Metadata = {
  title: "OmniDoc AI — Multimodal Document QA",
  description: "Visual Source Attribution & Zero-Hallucination Guardrails for Financial, Medical, and Legal PDFs",
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="en" className="dark">
      <body className="antialiased min-h-screen">
        {children}
      </body>
    </html>
  )
}
