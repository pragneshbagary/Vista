'use client'

import { useEffect, useState } from 'react'
import { getApiUrl, getSocialLinks } from './env-validation'

/**
 * Hook to safely access environment variables on the client side
 * Handles errors gracefully and provides fallback values
 */
export function useEnvironment() {
  const [apiUrl, setApiUrl] = useState<string | null>(null)
  const [socialLinks, setSocialLinks] = useState<{
    github?: string
    linkedin?: string
    email?: string
  } | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isLoaded, setIsLoaded] = useState(false)

  useEffect(() => {
    try {
      const url = getApiUrl()
      const links = getSocialLinks()
      setApiUrl(url)
      setSocialLinks(links)
      setError(null)
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to load environment variables'
      setError(errorMessage)
      console.error('Environment loading error:', errorMessage)
    } finally {
      setIsLoaded(true)
    }
  }, [])

  return {
    apiUrl,
    socialLinks,
    error,
    isLoaded,
  }
}

/**
 * Hook to get just the API URL
 */
export function useApiUrl(): string | null {
  const { apiUrl } = useEnvironment()
  return apiUrl
}

/**
 * Hook to get social links
 */
export function useSocialLinks(): {
  github?: string
  linkedin?: string
  email?: string
} | null {
  const { socialLinks } = useEnvironment()
  return socialLinks
}
