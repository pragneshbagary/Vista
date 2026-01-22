/**
 * Frontend environment variable validation utility
 * Validates that all required environment variables are set and properly formatted
 */

/**
 * Validates if a string is a valid URL
 */
function isValidUrl(url: string): boolean {
  try {
    const urlObj = new URL(url);
    return urlObj.protocol === 'http:' || urlObj.protocol === 'https:';
  } catch {
    return false;
  }
}

/**
 * Validates if a string is a valid email address
 */
function isValidEmail(email: string): boolean {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return emailRegex.test(email);
}

/**
 * Validates if a string is a valid GitHub URL
 */
function isValidGitHubUrl(url: string): boolean {
  if (!url) return true; // Optional field
  return isValidUrl(url) && url.includes('github.com');
}

/**
 * Validates if a string is a valid LinkedIn URL
 */
function isValidLinkedInUrl(url: string): boolean {
  if (!url) return true; // Optional field
  return isValidUrl(url) && url.includes('linkedin.com');
}

/**
 * Validates all frontend environment variables
 * Throws an error if validation fails
 */
export function validateEnvironment(): void {
  const errors: string[] = [];

  // Validate API URL (required)
  const apiUrl = process.env.NEXT_PUBLIC_VISTA_API_URL;
  if (!apiUrl) {
    errors.push('NEXT_PUBLIC_VISTA_API_URL is required');
  } else if (!isValidUrl(apiUrl)) {
    errors.push(`NEXT_PUBLIC_VISTA_API_URL must be a valid URL, got: ${apiUrl}`);
  } else if (process.env.NODE_ENV === 'production' && !apiUrl.startsWith('https://')) {
    errors.push(`NEXT_PUBLIC_VISTA_API_URL must use HTTPS in production, got: ${apiUrl}`);
  }

  // Validate GitHub URL (optional)
  const githubUrl = process.env.NEXT_PUBLIC_GITHUB_URL;
  if (githubUrl && !isValidGitHubUrl(githubUrl)) {
    errors.push(`NEXT_PUBLIC_GITHUB_URL must be a valid GitHub URL, got: ${githubUrl}`);
  }

  // Validate LinkedIn URL (optional)
  const linkedInUrl = process.env.NEXT_PUBLIC_LINKEDIN_URL;
  if (linkedInUrl && !isValidLinkedInUrl(linkedInUrl)) {
    errors.push(`NEXT_PUBLIC_LINKEDIN_URL must be a valid LinkedIn URL, got: ${linkedInUrl}`);
  }

  // Validate Email (optional)
  const email = process.env.NEXT_PUBLIC_EMAIL;
  if (email && !isValidEmail(email)) {
    errors.push(`NEXT_PUBLIC_EMAIL must be a valid email address, got: ${email}`);
  }

  if (errors.length > 0) {
    const errorMessage = 'Frontend environment validation failed:\n' + errors.map(e => `  - ${e}`).join('\n');
    throw new Error(errorMessage);
  }
}

/**
 * Gets the API URL with validation
 * Throws an error if API URL is not configured
 */
export function getApiUrl(): string {
  const apiUrl = process.env.NEXT_PUBLIC_VISTA_API_URL;
  if (!apiUrl) {
    throw new Error('NEXT_PUBLIC_VISTA_API_URL environment variable is not set');
  }
  return apiUrl;
}

/**
 * Gets optional social links
 */
export function getSocialLinks(): {
  github?: string;
  linkedin?: string;
  email?: string;
} {
  return {
    github: process.env.NEXT_PUBLIC_GITHUB_URL,
    linkedin: process.env.NEXT_PUBLIC_LINKEDIN_URL,
    email: process.env.NEXT_PUBLIC_EMAIL,
  };
}
