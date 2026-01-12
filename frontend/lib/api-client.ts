/**
 * API client with retry logic, exponential backoff, and request debouncing
 * Handles network failures gracefully and provides user-friendly error messages
 */

interface RetryConfig {
  maxRetries: number
  initialDelayMs: number
  maxDelayMs: number
  backoffMultiplier: number
  timeoutMs: number
}

interface RequestOptions extends RequestInit {
  timeout?: number
  retries?: number
}

const DEFAULT_RETRY_CONFIG: RetryConfig = {
  maxRetries: 3,
  initialDelayMs: 1000,
  maxDelayMs: 10000,
  backoffMultiplier: 2,
  timeoutMs: 30000,
}

/**
 * Calculates delay for exponential backoff
 */
function calculateBackoffDelay(
  attempt: number,
  config: RetryConfig
): number {
  const delay = config.initialDelayMs * Math.pow(config.backoffMultiplier, attempt - 1)
  return Math.min(delay, config.maxDelayMs)
}

/**
 * Determines if an error is retryable
 */
function isRetryableError(error: unknown): boolean {
  if (error instanceof TypeError) {
    // Network errors are retryable
    return error.message.includes('fetch') || error.message.includes('network')
  }

  if (error instanceof Error) {
    const message = error.message.toLowerCase()
    return (
      message.includes('timeout') ||
      message.includes('network') ||
      message.includes('connection') ||
      message.includes('econnrefused') ||
      message.includes('enotfound')
    )
  }

  return false
}

/**
 * Determines if an HTTP status code is retryable
 */
function isRetryableStatus(status: number): boolean {
  // Retry on server errors (5xx) and specific client errors
  return (
    status >= 500 || // Server errors
    status === 408 || // Request timeout
    status === 429    // Too many requests
  )
}

/**
 * Fetches with retry logic and exponential backoff
 */
export async function fetchWithRetry(
  url: string,
  options: RequestOptions = {},
  config: Partial<RetryConfig> = {}
): Promise<Response> {
  const finalConfig = { ...DEFAULT_RETRY_CONFIG, ...config }
  const maxRetries = options.retries ?? finalConfig.maxRetries
  const timeout = options.timeout ?? finalConfig.timeoutMs

  let lastError: Error | null = null

  for (let attempt = 1; attempt <= maxRetries + 1; attempt++) {
    try {
      const controller = new AbortController()
      const timeoutId = setTimeout(() => controller.abort(), timeout)

      try {
        const response = await fetch(url, {
          ...options,
          signal: controller.signal,
        })

        clearTimeout(timeoutId)

        // If response is successful, return it
        if (response.ok) {
          return response
        }

        // If status is not retryable, throw error
        if (!isRetryableStatus(response.status)) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`)
        }

        // If this is the last attempt, throw error
        if (attempt > maxRetries) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`)
        }

        // Otherwise, retry
        lastError = new Error(`HTTP ${response.status}: ${response.statusText}`)
      } finally {
        clearTimeout(timeoutId)
      }
    } catch (error) {
      lastError = error instanceof Error ? error : new Error(String(error))

      // If not retryable or last attempt, throw
      if (!isRetryableError(lastError) || attempt > maxRetries) {
        throw lastError
      }
    }

    // Wait before retrying (except on last attempt)
    if (attempt <= maxRetries) {
      const delay = calculateBackoffDelay(attempt, finalConfig)
      await new Promise(resolve => setTimeout(resolve, delay))
    }
  }

  throw lastError || new Error('Request failed after retries')
}

/**
 * Debounce utility for request functions
 */
export function createDebouncedRequest<T extends (...args: any[]) => Promise<any>>(
  fn: T,
  delayMs: number = 300
): T {
  let timeoutId: NodeJS.Timeout | null = null
  let lastArgs: any[] | null = null

  return ((...args: any[]) => {
    lastArgs = args

    return new Promise((resolve, reject) => {
      if (timeoutId) {
        clearTimeout(timeoutId)
      }

      timeoutId = setTimeout(async () => {
        try {
          const result = await fn(...(lastArgs || args))
          resolve(result)
        } catch (error) {
          reject(error)
        }
      }, delayMs)
    })
  }) as T
}

/**
 * Request cache for deduplication
 */
class RequestCache {
  private cache: Map<string, Promise<any>> = new Map()
  private timeouts: Map<string, NodeJS.Timeout> = new Map()

  async get<T>(
    key: string,
    fetcher: () => Promise<T>,
    ttlMs: number = 60000
  ): Promise<T> {
    // Return cached promise if available
    if (this.cache.has(key)) {
      return this.cache.get(key)!
    }

    // Create new promise
    const promise = fetcher()
    this.cache.set(key, promise)

    // Set expiration
    if (this.timeouts.has(key)) {
      clearTimeout(this.timeouts.get(key)!)
    }

    const timeout = setTimeout(() => {
      this.cache.delete(key)
      this.timeouts.delete(key)
    }, ttlMs)

    this.timeouts.set(key, timeout)

    return promise
  }

  clear(key?: string) {
    if (key) {
      this.cache.delete(key)
      if (this.timeouts.has(key)) {
        clearTimeout(this.timeouts.get(key)!)
        this.timeouts.delete(key)
      }
    } else {
      this.cache.clear()
      this.timeouts.forEach(timeout => clearTimeout(timeout))
      this.timeouts.clear()
    }
  }
}

export const requestCache = new RequestCache()

/**
 * API client with built-in retry, debounce, and caching
 */
export class ApiClient {
  private baseUrl: string
  private retryConfig: RetryConfig
  private debounceDelayMs: number
  private cache: RequestCache

  constructor(
    baseUrl: string,
    retryConfig: Partial<RetryConfig> = {},
    debounceDelayMs: number = 300
  ) {
    this.baseUrl = baseUrl
    this.retryConfig = { ...DEFAULT_RETRY_CONFIG, ...retryConfig }
    this.debounceDelayMs = debounceDelayMs
    this.cache = new RequestCache()
  }

  async get<T>(
    path: string,
    options: RequestOptions = {},
    useCache: boolean = true
  ): Promise<T> {
    const url = `${this.baseUrl}${path}`
    const cacheKey = `GET:${url}`

    if (useCache) {
      return this.cache.get(cacheKey, () => this.fetchJson<T>(url, options))
    }

    return this.fetchJson<T>(url, options)
  }

  async post<T>(
    path: string,
    body?: any,
    options: RequestOptions = {}
  ): Promise<T> {
    const url = `${this.baseUrl}${path}`
    return this.fetchJson<T>(url, {
      ...options,
      method: 'POST',
      body: body ? JSON.stringify(body) : undefined,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    })
  }

  async put<T>(
    path: string,
    body?: any,
    options: RequestOptions = {}
  ): Promise<T> {
    const url = `${this.baseUrl}${path}`
    return this.fetchJson<T>(url, {
      ...options,
      method: 'PUT',
      body: body ? JSON.stringify(body) : undefined,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    })
  }

  async delete<T>(
    path: string,
    options: RequestOptions = {}
  ): Promise<T> {
    const url = `${this.baseUrl}${path}`
    return this.fetchJson<T>(url, {
      ...options,
      method: 'DELETE',
    })
  }

  private async fetchJson<T>(
    url: string,
    options: RequestOptions = {}
  ): Promise<T> {
    const response = await fetchWithRetry(url, options, this.retryConfig)

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`)
    }

    const contentType = response.headers.get('content-type')
    if (!contentType?.includes('application/json')) {
      throw new Error('Response is not JSON')
    }

    return response.json() as Promise<T>
  }

  clearCache(path?: string) {
    if (path) {
      this.cache.clear(`GET:${this.baseUrl}${path}`)
    } else {
      this.cache.clear()
    }
  }
}
