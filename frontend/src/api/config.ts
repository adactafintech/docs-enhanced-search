// API configuration for URL prefix support
// The URL prefix is injected by the backend into window.__URL_PREFIX__
let urlPrefix = (window as any).__URL_PREFIX__ || ''
let initialized = false

export const initializeApiConfig = async () => {
  if (initialized) return
  
  // URL prefix is already set from the HTML page
  // But we can still fetch frontend_settings for other configuration
  try {
    const response = await fetch(getApiUrl('/frontend_settings'))
    if (response.ok) {
      const settings = await response.json()
      // Verify the prefix matches what we already have
      if (settings?.ui?.url_prefix !== urlPrefix) {
        console.warn('URL prefix mismatch between injected and fetched values')
      }
      console.log('API URL prefix configured:', urlPrefix || '(none - root path)')
    }
  } catch (error) {
    console.error('Failed to fetch frontend settings:', error)
    // We already have the prefix from the HTML, so this is not critical
  } finally {
    initialized = true
  }
}

export const getApiUrl = (path: string): string => {
  // Ensure path starts with /
  const normalizedPath = path.startsWith('/') ? path : `/${path}`
  
  // If no prefix, return path as is
  if (!urlPrefix) {
    return normalizedPath
  }
  
  // Combine prefix with path
  const prefix = urlPrefix.endsWith('/') ? urlPrefix.slice(0, -1) : urlPrefix
  return `${prefix}${normalizedPath}`
}

export const getUrlPrefix = (): string => {
  return urlPrefix
}
