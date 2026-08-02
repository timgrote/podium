import { computed } from 'vue'

const isTestServer = computed(() => {
  if (typeof window === 'undefined') return false
  return window.location.port === '3001'
})

export function useEnvironment() {
  return { isTestServer }
}
