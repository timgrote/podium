import { ref } from 'vue'
import type { Client } from '../types'
import { getClients } from '../api/clients'

const clients = ref<Client[]>([])
const loading = ref(false)

export function useClients() {
  async function load() {
    loading.value = true
    try {
      clients.value = await getClients()
    } finally {
      loading.value = false
    }
  }

  return { clients, loading, load }
}
