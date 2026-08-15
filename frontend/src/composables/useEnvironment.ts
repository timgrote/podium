import { computed } from 'vue'

/**
 * Environment detection for the Podium/Conductor frontend.
 *
 * The test-server indicator shows whenever the app is served on a non-standard
 * port. Production runs through Caddy on port 80 (window.location.port === ''),
 * so it never shows. Local/staging servers on ports like 3001 or 3100 are
 * treated as test servers.
 */
const IS_TEST =
  typeof window !== 'undefined' &&
  window.location.port !== '' &&
  window.location.port !== '80'

export function useEnvironment() {
  const isTestServer = computed(() => IS_TEST)
  return { isTestServer }
}
