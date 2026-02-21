import { ref } from 'vue'
import type { Client } from '../types'
import { getClients } from '../api/clients'

const clients = ref<Client[]>([])
const loading = ref(false)
const error = ref<string | null>(null)

export function useClients() {
  async function load() {
    loading.value = true
    error.value = null
    try {
      clients.value = await getClients()
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to load clients'
      console.error('Failed to load clients:', e)
    } finally {
      loading.value = false
    }
  }

  return { clients, loading, error, load }
}
