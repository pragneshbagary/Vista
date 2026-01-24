'use client'

import React, { ReactNode, ReactElement } from 'react'
import { AlertCircle } from 'lucide-react'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'

interface Props {
  children: ReactNode
  fallback?: ReactElement
}

interface State {
  hasError: boolean
  error: Error | null
}

/**
 * Error Boundary component for catching and handling React errors
 * Displays user-friendly error messages without exposing sensitive data
 */
export class ErrorBoundary extends React.Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    // Log error without sensitive data
    const sanitizedError = sanitizeErrorMessage(error.message)
    console.error('Error caught by boundary:', sanitizedError)
    console.error('Error info:', errorInfo.componentStack)

    // Send error to monitoring service (if configured)
    logErrorToMonitoring({
      message: sanitizedError,
      stack: errorInfo.componentStack || '',
      timestamp: new Date().toISOString(),
    })
  }

  render() {
    if (this.state.hasError) {
      return (
        this.props.fallback || (
          <div className="flex items-center justify-center min-h-screen bg-background p-4">
            <Alert variant="destructive" className="max-w-md">
              <AlertCircle className="h-4 w-4" />
              <AlertTitle>Something went wrong</AlertTitle>
              <AlertDescription>
                We encountered an unexpected error. Please try refreshing the page or contact support if the problem persists.
              </AlertDescription>
            </Alert>
          </div>
        )
      )
    }

    return this.props.children
  }
}

/**
 * Sanitizes error messages to remove sensitive data
 * Removes API keys, tokens, URLs, and other sensitive information
 */
export function sanitizeErrorMessage(message: string): string {
  if (!message) return 'An unknown error occurred'

  let sanitized = message

  // Remove API keys and tokens
  sanitized = sanitized.replace(/api[_-]?key[=:]\s*['"]?[^'"\s]+['"]?/gi, 'api_key=***')
  sanitized = sanitized.replace(/token[=:]\s*['"]?[^'"\s]+['"]?/gi, 'token=***')
  sanitized = sanitized.replace(/authorization[=:]\s*['"]?[^'"\s]+['"]?/gi, 'authorization=***')
  sanitized = sanitized.replace(/bearer\s+[^\s]+/gi, 'bearer ***')

  // Remove URLs with credentials
  sanitized = sanitized.replace(/https?:\/\/[^:]+:[^@]+@[^\s]+/g, 'https://***:***@***')

  // Remove email addresses
  sanitized = sanitized.replace(/[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/g, '***@***.***')

  // Remove file paths that might contain sensitive info
  sanitized = sanitized.replace(/\/home\/[^\s]+/g, '/home/***')
  sanitized = sanitized.replace(/\/Users\/[^\s]+/g, '/Users/***')

  return sanitized
}

/**
 * Logs errors to monitoring service without sensitive data
 * This is a placeholder that can be connected to services like Sentry, LogRocket, etc.
 */
function logErrorToMonitoring(errorData: {
  message: string
  stack: string
  timestamp: string
}) {
  // Only log in production
  if (process.env.NODE_ENV !== 'production') {
    return
  }

  try {
    // Placeholder for error monitoring integration
    // Example: Sentry.captureException(errorData)
    // Example: fetch('/api/errors', { method: 'POST', body: JSON.stringify(errorData) })
    console.debug('Error logged to monitoring:', errorData.message)
  } catch (err) {
    // Silently fail if monitoring is unavailable
    console.debug('Failed to log error to monitoring service')
  }
}

/**
 * Hook for handling errors in async operations
 */
export function useErrorHandler() {
  const handleError = (error: unknown, context?: string) => {
    const message = error instanceof Error ? error.message : String(error)
    const sanitized = sanitizeErrorMessage(message)

    console.error(`Error${context ? ` in ${context}` : ''}:`, sanitized)

    logErrorToMonitoring({
      message: sanitized,
      stack: error instanceof Error ? error.stack || '' : '',
      timestamp: new Date().toISOString(),
    })

    return sanitized
  }

  return { handleError }
}
