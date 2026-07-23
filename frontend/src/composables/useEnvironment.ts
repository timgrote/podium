import { computed } from 'vue'

/**
 * Detects whether the app is running on the test server.
 * Test server runs on port 3001 (Thorin), production behind Caddy on port 80.
 */
const isTestServer = computed(() => {
  if (typeof window === 'undefined') return false
  return window.location.port === '3001'
})

export function useEnvironment() {
  return { isTestServer }
}
