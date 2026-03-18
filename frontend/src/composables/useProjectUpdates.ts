import { watch, type Ref } from 'vue'

export function useProjectUpdates(
  projectId: Ref<string | null>,
  onUpdate: (eventType: string, entityId: string) => void
) {
  let source: EventSource | null = null

  function connect(id: string) {
    disconnect()
    source = new EventSource(`/api/updates/projects/${id}/stream`)

    const eventTypes = [
      'task_created', 'task_updated', 'task_deleted',
      'note_added', 'note_deleted', 'project_updated',
      'contract_updated', 'invoice_updated', 'proposal_updated',
    ]

    for (const type of eventTypes) {
      source.addEventListener(type, (ev: MessageEvent) => {
        const data = JSON.parse(ev.data)
        onUpdate(data.type, data.entity_id)
      })
    }
  }

  function disconnect() {
    if (source) {
      source.close()
      source = null
    }
  }

  watch(projectId, (id) => {
    if (id) {
      connect(id)
    } else {
      disconnect()
    }
  }, { immediate: true })

  return { disconnect }
}
