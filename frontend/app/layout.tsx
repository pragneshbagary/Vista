import type { Metadata } from 'next'
import { Geist, Geist_Mono } from 'next/font/google'
import { Analytics } from '@vercel/analytics/next'
import { validateEnvironment } from '@/lib/env-validation'
import { ErrorBoundary } from '@/components/ErrorBoundary'
import './globals.css'

// Validate environment variables at build time
if (typeof window === 'undefined') {
  try {
    validateEnvironment();
  } catch (error) {
    console.error('Environment validation failed:', error);
    if (process.env.NODE_ENV === 'production') {
      throw error;
    }
  }
}

const _geist = Geist({ subsets: ["latin"] });
const _geistMono = Geist_Mono({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: 'VISTA',
  description: 'Vector-Integrated Semantic Text Assistant',
  icons: {
    icon: [
      {
        url: '/frontend/public/vista_logo.svg',
        media: '(prefers-color-scheme: light)',
      },
      {
        url: '/icon-dark-32x32.png',
        media: '(prefers-color-scheme: dark)',
      },
      {
        url: '/icon.svg',
        type: 'image/svg+xml',
      },
    ],
    apple: '/apple-icon.png',
  },
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`font-sans antialiased bg-gradient-to-br from-background via-background to-background`}>
        <ErrorBoundary>
          {children}
          <Analytics />
        </ErrorBoundary>
      </body>
    </html>
  )
}
