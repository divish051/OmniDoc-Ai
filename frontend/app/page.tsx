"use client"

import React, { useState, useEffect, useRef } from "react"
import {
  FileText,
  Upload,
  Send,
  Mic,
  MicOff,
  AlertTriangle,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  ZoomIn,
  ZoomOut,
  RotateCcw,
  Sparkles,
  KeyRound,
  ShieldCheck,
  Eye,
  EyeOff
} from "lucide-react"

interface PageData {
  page_num: number
  url: string
  width: number
  height: number
}

interface DocData {
  doc_id: string
  filename: string
  total_pages: number
  pages: PageData[]
}

interface Message {
  id: string
  role: "user" | "assistant"
  content: string
  is_data_missing?: boolean
  missing_reason?: string
  source_page?: number
  timestamp: string
}

export default function OmniDocApp() {
  const [apiKey, setApiKey] = useState("")
  const [showApiKey, setShowApiKey] = useState(false)
  const [selectedModel, setSelectedModel] = useState("gemini-2.5-pro")
  const [availableModels, setAvailableModels] = useState<string[]>([
    "gemini-2.5-pro",
    "gemini-2.5-flash",
    "gemini-1.5-pro",
    "gemini-1.5-flash",
  ])

  // Document state
  const [currentDoc, setCurrentDoc] = useState<DocData | null>(null)
  const [activePage, setActivePage] = useState<number>(1)
  const [isUploading, setIsUploading] = useState(false)
  const [zoomLevel, setZoomLevel] = useState(100)

  // Chat & Query state
  const [messages, setMessages] = useState<Message[]>([])
  const [inputQuery, setInputQuery] = useState("")
  const [isQuerying, setIsQuerying] = useState(false)

  // Voice recording state
  const [isRecording, setIsRecording] = useState(false)
  const [recordingStatus, setRecordingStatus] = useState("")
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const audioChunksRef = useRef<Blob[]>([])

  const chatEndRef = useRef<HTMLDivElement>(null)

  // Auto-scroll chat
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages, isQuerying])

  // Fetch available models on load
  useEffect(() => {
    fetch("/api/models")
      .then((res) => res.json())
      .then((data) => {
        if (data.models && data.models.length > 0) {
          setAvailableModels(data.models)
          if (!data.models.includes(selectedModel)) {
            setSelectedModel(data.models[0])
          }
        }
      })
      .catch(() => {})
  }, [apiKey])

  // File Upload Handler
  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    setIsUploading(true)
    const formData = new FormData()
    formData.append("file", file)
    if (apiKey) formData.append("api_key", apiKey)

    try {
      const res = await fetch("/api/upload", {
        method: "POST",
        body: formData,
      })

      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || "Upload failed")
      }

      const data: DocData = await res.json()
      setCurrentDoc(data)
      setActivePage(1)
      setZoomLevel(100)
    } catch (err: any) {
      alert("Upload failed: " + err.message)
    } finally {
      setIsUploading(false)
    }
  }

  // Submit Query
  const handleSendQuery = async (queryText?: string) => {
    const query = queryText || inputQuery
    if (!query.trim()) return
    if (!currentDoc) {
      alert("Please upload a PDF document first.")
      return
    }

    const userMsg: Message = {
      id: Date.now().toString(),
      role: "user",
      content: query,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
    }

    setMessages((prev) => [...prev, userMsg])
    setInputQuery("")
    setIsQuerying(true)

    try {
      const res = await fetch("/api/query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          doc_id: currentDoc.doc_id,
          query: query,
          api_key: apiKey,
          model_name: selectedModel,
          target_page: currentDoc.total_pages === 1 ? 1 : activePage,
        })
      })

      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || "Query failed")
      }

      const data = await res.json()

      // Automatically sync Left Pane to the identified source page!
      if (data.source_page) {
        setActivePage(data.source_page)
      }

      const assistantMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: data.answer,
        is_data_missing: data.is_data_missing,
        missing_reason: data.missing_reason,
        source_page: data.source_page,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
      }

      setMessages((prev) => [...prev, assistantMsg])
    } catch (err: any) {
      const errorMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: `Error: ${err.message}`,
        is_data_missing: true,
        missing_reason: err.message,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
      }
      setMessages((prev) => [...prev, errorMsg])
    } finally {
      setIsQuerying(false)
    }
  }

  // Voice Recording
  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const mediaRecorder = new MediaRecorder(stream)
      mediaRecorderRef.current = mediaRecorder
      audioChunksRef.current = []

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data)
        }
      }

      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: "audio/wav" })
        stream.getTracks().forEach((track) => track.stop())
        await processAudio(audioBlob)
      }

      mediaRecorder.start()
      setIsRecording(true)
      setRecordingStatus("Recording... Speak in Tamil, Hindi, Tanglish, or English")
    } catch (err) {
      alert("Microphone access denied or not available.")
    }
  }

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop()
      setIsRecording(false)
      setRecordingStatus("Transcribing audio via Gemini...")
    }
  }

  const processAudio = async (blob: Blob) => {
    const formData = new FormData()
    formData.append("audio", blob, "recording.wav")
    if (apiKey) formData.append("api_key", apiKey)

    try {
      const res = await fetch("/api/transcribe", {
        method: "POST",
        body: formData,
      })
      const data = await res.json()
      if (data.transcription) {
        setRecordingStatus(`Recognized: "${data.transcription}"`)
        handleSendQuery(data.transcription)
      } else {
        setRecordingStatus(data.error || "Could not transcribe audio.")
      }
    } catch (err: any) {
      setRecordingStatus("Audio transcription failed.")
    }
  }

  return (
    <div className="flex flex-col h-screen bg-[#090d16] text-slate-100">
      {/* Top Navigation Bar */}
      <header className="flex items-center justify-between px-6 py-3.5 border-b border-slate-800/80 bg-slate-950/70 backdrop-blur-md">
        <div className="flex items-center space-x-3">
          <div className="flex items-center justify-center w-10 h-10 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-500 shadow-lg shadow-blue-500/20">
            <Sparkles className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="text-lg font-bold tracking-tight bg-gradient-to-r from-blue-400 via-indigo-300 to-purple-400 bg-clip-text text-transparent">
              OmniDoc AI
            </h1>
            <p className="text-xs text-slate-400">
              Visual Source Attribution • Zero-Hallucination Guardrails
            </p>
          </div>
        </div>

        {/* Controls */}
        <div className="flex items-center space-x-3">
          {/* API Key Input */}
          <div className="relative flex items-center">
            <KeyRound className="absolute left-3 w-4 h-4 text-slate-400" />
            <input
              type={showApiKey ? "text" : "password"}
              placeholder="Gemini API Key (AIzaSy...)"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              className="w-56 pl-9 pr-9 py-1.5 text-xs bg-slate-900/90 border border-slate-700/80 rounded-lg focus:outline-none focus:border-blue-500 text-slate-200"
            />
            <button
              onClick={() => setShowApiKey(!showApiKey)}
              className="absolute right-2.5 text-slate-400 hover:text-slate-200"
            >
              {showApiKey ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
            </button>
          </div>

          {/* Model Selector */}
          <select
            value={selectedModel}
            onChange={(e) => setSelectedModel(e.target.value)}
            className="px-3 py-1.5 text-xs bg-slate-900/90 border border-slate-700/80 rounded-lg focus:outline-none focus:border-blue-500 text-slate-200"
          >
            {availableModels.map((m) => (
              <option key={m} value={m}>
                {m}
              </option>
            ))}
          </select>

          {/* Upload Button */}
          <label className="flex items-center space-x-2 px-3.5 py-1.5 text-xs font-semibold rounded-lg bg-blue-600 hover:bg-blue-500 text-white cursor-pointer shadow-sm transition">
            <Upload className="w-3.5 h-3.5" />
            <span>{isUploading ? "Processing..." : "Upload PDF"}</span>
            <input
              type="file"
              accept=".pdf"
              onChange={handleFileUpload}
              className="hidden"
            />
          </label>
        </div>
      </header>

      {/* Main Dual-Pane Area */}
      <div className="flex-1 flex overflow-hidden">
        {/* ========================================================= */}
        {/* LEFT PANE: VISUAL SOURCE ATTRIBUTION (50%)               */}
        {/* ========================================================= */}
        <div className="w-1/2 flex flex-col border-r border-slate-800/80 bg-slate-950/40">
          {/* Viewer Toolbar */}
          <div className="flex items-center justify-between px-4 py-2.5 border-b border-slate-800/80 bg-slate-900/50">
            <div className="flex items-center space-x-2">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-400">
                🖼️ Ground Truth Visual Viewer
              </span>
              {currentDoc && (
                <span className="px-2 py-0.5 text-[11px] font-semibold bg-indigo-500/10 border border-indigo-500/30 text-indigo-300 rounded-md">
                  Page {activePage} of {currentDoc.total_pages}
                </span>
              )}
            </div>

            {currentDoc && (
              <div className="flex items-center space-x-1.5 text-xs">
                <button
                  disabled={activePage <= 1}
                  onClick={() => setActivePage((p) => Math.max(1, p - 1))}
                  className="p-1 rounded bg-slate-800 hover:bg-slate-700 disabled:opacity-40"
                  title="Previous Page"
                >
                  <ChevronLeft className="w-4 h-4" />
                </button>
                <button
                  disabled={activePage >= currentDoc.total_pages}
                  onClick={() => setActivePage((p) => Math.min(currentDoc.total_pages, p + 1))}
                  className="p-1 rounded bg-slate-800 hover:bg-slate-700 disabled:opacity-40"
                  title="Next Page"
                >
                  <ChevronRight className="w-4 h-4" />
                </button>
                <div className="h-4 w-[1px] bg-slate-700 mx-1" />
                <button
                  onClick={() => setZoomLevel((z) => Math.max(50, z - 15))}
                  className="p-1 rounded bg-slate-800 hover:bg-slate-700"
                  title="Zoom Out"
                >
                  <ZoomOut className="w-4 h-4" />
                </button>
                <span className="text-[11px] text-slate-400 w-10 text-center">
                  {zoomLevel}%
                </span>
                <button
                  onClick={() => setZoomLevel((z) => Math.min(200, z + 15))}
                  className="p-1 rounded bg-slate-800 hover:bg-slate-700"
                  title="Zoom In"
                >
                  <ZoomIn className="w-4 h-4" />
                </button>
                <button
                  onClick={() => setZoomLevel(100)}
                  className="p-1 rounded bg-slate-800 hover:bg-slate-700"
                  title="Reset Zoom"
                >
                  <RotateCcw className="w-3.5 h-3.5" />
                </button>
              </div>
            )}
          </div>

          {/* Viewer Content */}
          <div className="flex-1 overflow-auto p-4 flex items-center justify-center bg-black/20">
            {currentDoc ? (
              <div
                style={{ width: `${zoomLevel}%` }}
                className="transition-all duration-150 flex flex-col items-center"
              >
                <img
                  src={`/api/page/${currentDoc.doc_id}/${activePage}`}
                  alt={`Page ${activePage}`}
                  className="rounded-lg shadow-2xl border border-slate-700/60 max-w-full"
                />
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center text-center p-8 border-2 border-dashed border-slate-800 rounded-2xl max-w-md">
                <div className="w-16 h-16 mb-4 rounded-full bg-slate-900 flex items-center justify-center text-slate-500">
                  <FileText className="w-8 h-8" />
                </div>
                <h3 className="text-sm font-semibold text-slate-300">
                  No Document Active
                </h3>
                <p className="text-xs text-slate-500 mt-1 max-w-xs">
                  Upload an earnings report, balance sheet, or financial PDF to inspect high-resolution sliced pages.
                </p>
              </div>
            )}
          </div>
        </div>

        {/* ========================================================= */}
        {/* RIGHT PANE: CONVERSATIONAL QA & GUARDRAILS (50%)          */}
        {/* ========================================================= */}
        <div className="w-1/2 flex flex-col bg-slate-950/20">
          {/* Header */}
          <div className="flex items-center justify-between px-6 py-2.5 border-b border-slate-800/80 bg-slate-900/50">
            <div className="flex items-center space-x-2">
              <ShieldCheck className="w-4 h-4 text-blue-400" />
              <span className="text-xs font-bold uppercase tracking-wider text-slate-300">
                Verified Document Intelligence
              </span>
            </div>
            {messages.length > 0 && (
              <button
                onClick={() => setMessages([])}
                className="text-xs text-slate-500 hover:text-slate-300"
              >
                Clear History
              </button>
            )}
          </div>

          {/* Messages Scroll Area */}
          <div className="flex-1 overflow-y-auto p-6 space-y-4">
            {messages.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full text-center text-slate-500">
                <Sparkles className="w-8 h-8 mb-2 text-slate-600" />
                <p className="text-sm font-medium text-slate-400">
                  Ask anything about the document
                </p>
                <p className="text-xs max-w-xs mt-1">
                  Questions are answered strictly from visible charts, tables, and text. Missing data triggers the zero-hallucination guardrail.
                </p>
              </div>
            ) : (
              messages.map((msg) => (
                <div
                  key={msg.id}
                  className={`flex flex-col ${
                    msg.role === "user" ? "items-end" : "items-start"
                  }`}
                >
                  {msg.role === "user" ? (
                    <div className="max-w-[80%] rounded-2xl rounded-tr-none px-4 py-2.5 bg-blue-600 text-white text-sm shadow-md">
                      {msg.content}
                    </div>
                  ) : msg.is_data_missing ? (
                    /* RED SECURITY WARNING BANNER */
                    <div className="w-full max-w-[95%] rounded-xl border border-red-500/80 bg-red-950/40 p-4 text-red-200 security-pulse-alert">
                      <div className="flex items-center space-x-2 text-xs font-extrabold uppercase tracking-wider text-red-400 mb-1.5">
                        <AlertTriangle className="w-4 h-4 text-red-500" />
                        <span>[DATA_MISSING] Zero-Hallucination Guardrail Triggered</span>
                      </div>
                      <p className="text-xs font-medium text-red-300 mb-1">
                        Security Notice: The requested figure or information is not visually verifiable on the source page.
                      </p>
                      <div className="text-xs text-slate-300 mt-2 pt-2 border-t border-red-900/60 leading-relaxed">
                        {msg.missing_reason || msg.content}
                      </div>
                    </div>
                  ) : (
                    /* VERIFIED ANSWER CARD */
                    <div className="w-full max-w-[95%] rounded-xl border border-slate-800 bg-slate-900/70 p-4 shadow-lg backdrop-blur-sm">
                      <div className="flex items-center justify-between pb-2 mb-2 border-b border-slate-800/80">
                        <span className="flex items-center space-x-1.5 text-[11px] font-bold tracking-wider text-blue-400">
                          <CheckCircle2 className="w-3.5 h-3.5 text-blue-400" />
                          <span>VERIFIED BY GEMINI</span>
                        </span>
                        {msg.source_page && (
                          <button
                            onClick={() => setActivePage(msg.source_page!)}
                            className="px-2 py-0.5 text-[11px] font-semibold bg-indigo-500/10 border border-indigo-500/30 text-indigo-300 rounded hover:bg-indigo-500/20 transition"
                          >
                            📌 Grounded in Page {msg.source_page}
                          </button>
                        )}
                      </div>
                      <div className="text-xs text-slate-200 leading-relaxed whitespace-pre-wrap">
                        {msg.content}
                      </div>
                    </div>
                  )}
                  <span className="text-[10px] text-slate-600 mt-1 px-1">
                    {msg.timestamp}
                  </span>
                </div>
              ))
            )}

            {isQuerying && (
              <div className="flex items-center space-x-2 text-xs text-slate-400 p-3 bg-slate-900/40 rounded-lg w-fit border border-slate-800/60">
                <Sparkles className="w-4 h-4 animate-spin text-blue-400" />
                <span>Auditing document image via Gemini...</span>
              </div>
            )}
            <div ref={chatEndRef} />
          </div>

          {/* Voice Status Toast */}
          {recordingStatus && (
            <div className="px-6 py-1.5 bg-blue-950/40 border-t border-blue-900/40 text-xs text-blue-300 flex items-center justify-between">
              <span>{recordingStatus}</span>
              <button
                onClick={() => setRecordingStatus("")}
                className="text-blue-400 hover:text-blue-200"
              >
                ✕
              </button>
            </div>
          )}

          {/* Bottom Query Bar */}
          <div className="p-4 border-t border-slate-800/80 bg-slate-900/50">
            <form
              onSubmit={(e) => {
                e.preventDefault()
                handleSendQuery()
              }}
              className="flex items-center space-x-2"
            >
              {/* Voice Record Button */}
              <button
                type="button"
                onClick={isRecording ? stopRecording : startRecording}
                className={`p-2.5 rounded-xl border transition ${
                  isRecording
                    ? "bg-red-600 border-red-500 text-white animate-pulse"
                    : "bg-slate-800/80 border-slate-700 hover:bg-slate-700 text-slate-300"
                }`}
                title={isRecording ? "Stop Recording" : "Speak question (Tamil, Hindi, Tanglish, English)"}
              >
                {isRecording ? <MicOff className="w-4 h-4" /> : <Mic className="w-4 h-4" />}
              </button>

              {/* Text Input */}
              <input
                type="text"
                placeholder="Ask about charts, tables, or financials (e.g. 'What is Q4 revenue?')..."
                value={inputQuery}
                onChange={(e) => setInputQuery(e.target.value)}
                disabled={isQuerying}
                className="flex-1 px-4 py-2.5 text-xs bg-slate-900/90 border border-slate-700/80 rounded-xl focus:outline-none focus:border-blue-500 text-slate-200 placeholder-slate-500 disabled:opacity-50"
              />

              {/* Send Button */}
              <button
                type="submit"
                disabled={!inputQuery.trim() || isQuerying}
                className="p-2.5 rounded-xl bg-blue-600 hover:bg-blue-500 disabled:opacity-40 text-white transition shadow-md shadow-blue-500/20"
              >
                <Send className="w-4 h-4" />
              </button>
            </form>
          </div>
        </div>
      </div>
    </div>
  )
}
