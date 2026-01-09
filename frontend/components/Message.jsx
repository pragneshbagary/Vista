import React, { useState } from "react"
import { User, Bot, Copy, Check, RotateCcw, Edit2 } from "lucide-react"

export default function Message({ message, onEdit, onResend, userAvatar }) {
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
    <div className={`flex items-start gap-3 ${isUser ? "flex-row-reverse" : ""}`}>
      {/* Avatar */}
      <div className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-xl overflow-hidden">
        {isUser && userAvatar ? (
          <img 
            src={`/avatars/${userAvatar}`} 
            alt="User avatar" 
            className="h-full w-full object-cover"
          />
        ) : !isUser ? (
          <img 
            src="/avatars/ai.png" 
            alt="VISTA avatar" 
            className="h-full w-full object-cover"
          />
        ) : (
          <User className="h-4 w-4 text-primary" />
        )}
      </div>

      {/* Message content */}
      <div className={`group relative flex max-w-[75%] flex-col gap-2 ${isUser ? "items-end" : "items-start"}`}>
        {isEditing ? (
          <div className="glass-card glass-shadow w-full space-y-2 p-3">
            <textarea
              value={editContent}
              onChange={(e) => setEditContent(e.target.value)}
              className="glass-input w-full min-h-[80px] text-sm resize-none"
              autoFocus
            />
            <div className="flex gap-2 justify-end">
              <button
                onClick={handleCancelEdit}
                className="glass-button px-3 py-1 text-xs"
              >
                Cancel
              </button>
              <button
                onClick={handleSaveEdit}
                className="glass-button-primary px-3 py-1 text-xs"
              >
                Save
              </button>
            </div>
          </div>
        ) : (
          <>
            <div className={`glass-card glass-shadow px-3 py-1.5 rounded-lg ${
              isUser
                ? "bg-primary/20 border-primary/30"
                : ""
            }`}>
              <p className="text-sm leading-relaxed whitespace-pre-wrap break-words text-foreground">
                {message.content}
              </p>
              
              {/* Edited indicator */}
              {message.editedAt && (
                <p className="mt-2 text-xs text-muted-foreground">
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
                className="glass-button p-1.5 text-muted-foreground hover:text-foreground"
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
                  className="glass-button p-1.5 text-muted-foreground hover:text-foreground"
                  title="Edit message"
                >
                  <Edit2 className="h-3.5 w-3.5" />
                </button>
              )}
              
              {isUser && onResend && (
                <button
                  onClick={() => onResend(message.id)}
                  className="glass-button p-1.5 text-muted-foreground hover:text-foreground"
                  title="Resend message"
                >
                  <RotateCcw className="h-3.5 w-3.5" />
                </button>
              )}
            </div>
          </>
        )}

        {/* Timestamp */}
        <div className={`text-xs text-muted-foreground/70 ${isUser ? "text-right" : ""}`}>
          {new Date(message.createdAt).toLocaleTimeString([], { 
            hour: '2-digit', 
            minute: '2-digit' 
          })}
        </div>
      </div>
    </div>
  )
}
