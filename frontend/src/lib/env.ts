/**
 * Environment configuration for the application
 */

export const ENV = {
  // Check if we're in development mode
  isDevelopment: import.meta.env.MODE === 'development',
  
  // Check if mock data should be enabled (can be overridden with env var)
  enableMockFallbacks: 
    import.meta.env.VITE_ENABLE_MOCK_FALLBACKS === 'true' || 
    import.meta.env.MODE === 'development',
  
  // API configuration
  apiUrl: import.meta.env.VITE_API_URL || '/api',
  
  // Feature flags
  features: {
    analyticsRealTime: import.meta.env.VITE_ENABLE_REALTIME_ANALYTICS === 'true',
    aiGeneration: import.meta.env.VITE_ENABLE_AI_GENERATION !== 'false', // Default true
  }
} as const

export type EnvConfig = typeof ENV