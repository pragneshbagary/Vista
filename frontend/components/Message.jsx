import React, { useState } from "react"
import { User, Bot, Copy, Check, RotateCcw, Edit2 } from "lucide-react"

export default function Message({ message, onEdit, onResend }) {
  const [copied, setCopied] = useState(false)
  const [isEditing, setIsEditing] = useState(false)
  const [editContent, setEditContent] = useState(message.content)
  const isUser = message.role === "user"

  const handleCopy = async () => {
    await navigator.clipboard.writeText(message.content)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const handleSaveEdit = () => {
    if (editContent.trim() && editContent !== message.content) {
      onEdit(message.id, editContent.trim())
    }
    setIsEditing(false)
  }

  const handleCancelEdit = () => {
    setEditContent(message.content)
    setIsEditing(false)
  }

  return (
    <div className={`flex items-start gap-4 ${isUser ? "flex-row-reverse" : ""}`}>
      {/* Avatar with glass effect */}
      <div className={`flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full shadow-lg ${
        isUser 
          ? "bg-gradient-to-br from-blue-500 to-cyan-500" 
          : "bg-gradient-to-br from-purple-500 to-pink-500"
      }`}>
        {isUser ? (
          <User className="h-5 w-5 text-white" />
        ) : (
          <Bot className="h-5 w-5 text-white" />
        )}
      </div>

      {/* Message content with glass effect */}
      <div className={`group relative flex max-w-[80%] flex-col gap-2 ${isUser ? "items-end" : "items-start"}`}>
        {isEditing ? (
          <div className="glass-card glass-shadow w-full space-y-3 p-4">
            <textarea
              value={editContent}
              onChange={(e) => setEditContent(e.target.value)}
              className="glass-input w-full min-h-[100px] px-3 py-2 text-sm text-white placeholder-white/40 resize-none"
              autoFocus
            />
            <div className="flex gap-2 justify-end">
              <button
                onClick={handleCancelEdit}
                className="glass-button px-3 py-1.5 text-xs text-white/70 hover:text-white"
              >
                Cancel
              </button>
              <button
                onClick={handleSaveEdit}
                className="px-3 py-1.5 text-xs bg-gradient-to-r from-purple-500 to-pink-500 text-white rounded-lg hover:shadow-lg transition-all"
              >
                Save
              </button>
            </div>
          </div>
        ) : (
          <>
            <div className={`glass-shine rounded-2xl px-5 py-4 shadow-lg ${
              isUser
                ? "bg-gradient-to-br from-blue-500/90 to-purple-600/90 text-white"
                : "glass-card text-white"
            }`}>
              <p className="text-sm leading-relaxed whitespace-pre-wrap break-words">
                {message.content}
              </p>
              
              {/* Edited indicator */}
              {message.editedAt && (
                <p className="mt-2 text-xs opacity-50">
                  (edited)
                </p>
              )}
            </div>

            {/* Action buttons - show on hover */}
            <div className={`flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity ${
              isUser ? "flex-row-reverse" : ""
            }`}>
              <button
                onClick={handleCopy}
                className="glass-button p-2 text-white/60 hover:text-white"
                title="Copy message"
              >
                {copied ? (
                  <Check className="h-3.5 w-3.5" />
                ) : (
                  <Copy className="h-3.5 w-3.5" />
                )}
              </button>
              
              {isUser && onEdit && (
                <button
                  onClick={() => setIsEditing(true)}
                  className="glass-button p-2 text-white/60 hover:text-white"
                  title="Edit message"
                >
                  <Edit2 className="h-3.5 w-3.5" />
                </button>
              )}
              
              {isUser && onResend && (
                <button
                  onClick={() => onResend(message.id)}
                  className="glass-button p-2 text-white/60 hover:text-white"
                  title="Resend message"
                >
                  <RotateCcw className="h-3.5 w-3.5" />
                </button>
              )}
            </div>
          </>
        )}

        {/* Timestamp */}
        <div className={`text-xs text-white/40 ${isUser ? "text-right" : ""}`}>
          {new Date(message.createdAt).toLocaleTimeString([], { 
            hour: '2-digit', 
            minute: '2-digit' 
          })}
        </div>
      </div>
    </div>
  )
}
