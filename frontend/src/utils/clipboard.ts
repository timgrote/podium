import { useToast } from '../composables/useToast'

export async function copyLink(path: string) {
  const toast = useToast()
  const url = window.location.origin + path
  try {
    await navigator.clipboard.writeText(url)
    toast.success('Link copied')
  } catch {
    toast.error('Failed to copy link')
  }
}
