'use client'

import { useEffect, useState, useCallback, useRef } from 'react'
import { ApiClient } from './api-client'
import { useApiUrl } from './use-environment'
import { sanitizeErrorMessage } from '@/components/ErrorBoundary'

interface UseApiState<T> {
  data: T | null
  loading: boolean
  error: string | null
}

/**
 * Hook for making API requests with retry logic and error handling
 */
export function useApi<T>(
  path: string,
  options: { skip?: boolean; cache?: boolean } = {}
): UseApiState<T> & { refetch: () => Promise<void> } {
  const apiUrl = useApiUrl()
  const [state, setState] = useState<UseApiState<T>>({
    data: null,
    loading: true,
    error: null,
  })

  const clientRef = useRef<ApiClient | null>(null)

  // Initialize API client
  useEffect(() => {
    if (apiUrl) {
      clientRef.current = new ApiClient(apiUrl)
    }
  }, [apiUrl])

  const refetch = useCallback(async () => {
    if (!clientRef.current || !path) {
      setState(prev => ({ ...prev, error: 'API client not initialized' }))
      return
    }

    setState(prev => ({ ...prev, loading: true, error: null }))

    try {
      const data = await clientRef.current.get<T>(path, {}, options.cache !== false)
      setState({ data, loading: false, error: null })
    } catch (err) {
      const errorMessage = sanitizeErrorMessage(
        err instanceof Error ? err.message : 'Failed to fetch data'
      )
      setState({ data: null, loading: false, error: errorMessage })
    }
  }, [path, options.cache])

  // Fetch on mount
  useEffect(() => {
    if (!options.skip && apiUrl && path) {
      refetch()
    }
  }, [apiUrl, path, options.skip, refetch])

  return { ...state, refetch }
}

/**
 * Hook for making POST requests
 */
export function useApiMutation<T, D = any>(
  path: string
): {
  mutate: (data?: D) => Promise<T>
  loading: boolean
  error: string | null
  reset: () => void
} {
  const apiUrl = useApiUrl()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const clientRef = useRef<ApiClient | null>(null)

  useEffect(() => {
    if (apiUrl) {
      clientRef.current = new ApiClient(apiUrl)
    }
  }, [apiUrl])

  const mutate = useCallback(
    async (data?: D): Promise<T> => {
      if (!clientRef.current) {
        throw new Error('API client not initialized')
      }

      setLoading(true)
      setError(null)

      try {
        const result = await clientRef.current.post<T>(path, data)
        setLoading(false)
        return result
      } catch (err) {
        const errorMessage = sanitizeErrorMessage(
          err instanceof Error ? err.message : 'Request failed'
        )
        setError(errorMessage)
        setLoading(false)
        throw err
      }
    },
    [path]
  )

  const reset = useCallback(() => {
    setLoading(false)
    setError(null)
  }, [])

  return { mutate, loading, error, reset }
}

/**
 * Hook for debounced API requests (e.g., search)
 */
export function useDebouncedApi<T>(
  path: string,
  debounceMs: number = 300,
  options: { skip?: boolean } = {}
): UseApiState<T> & { refetch: () => Promise<void> } {
  const apiUrl = useApiUrl()
  const [state, setState] = useState<UseApiState<T>>({
    data: null,
    loading: false,
    error: null,
  })

  const clientRef = useRef<ApiClient | null>(null)
  const timeoutRef = useRef<NodeJS.Timeout | null>(null)

  useEffect(() => {
    if (apiUrl) {
      clientRef.current = new ApiClient(apiUrl, {}, debounceMs)
    }
  }, [apiUrl, debounceMs])

  const refetch = useCallback(async () => {
    if (!clientRef.current || !path) {
      setState(prev => ({ ...prev, error: 'API client not initialized' }))
      return
    }

    // Clear previous timeout
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current)
    }

    setState(prev => ({ ...prev, loading: true, error: null }))

    // Set new timeout for debounce
    timeoutRef.current = setTimeout(async () => {
      try {
        const data = await clientRef.current!.get<T>(path, {}, true)
        setState({ data, loading: false, error: null })
      } catch (err) {
        const errorMessage = sanitizeErrorMessage(
          err instanceof Error ? err.message : 'Failed to fetch data'
        )
        setState({ data: null, loading: false, error: errorMessage })
      }
    }, debounceMs)
  }, [path, debounceMs])

  useEffect(() => {
    if (!options.skip && apiUrl && path) {
      refetch()
    }

    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current)
      }
    }
  }, [apiUrl, path, options.skip, refetch])

  return { ...state, refetch }
}
