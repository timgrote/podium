import { useToast } from '../composables/useToast'

export async function copyLink(path: string) {
  const toast = useToast()
  const url = window.location.origin + path
  try {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(url)
    } else {
      const ta = document.createElement('textarea')
      ta.value = url
      ta.style.position = 'fixed'
      ta.style.opacity = '0'
      document.body.appendChild(ta)
      ta.select()
      const ok = document.execCommand('copy')
      document.body.removeChild(ta)
      if (!ok) throw new Error('execCommand failed')
    }
    toast.success('Link copied')
  } catch {
    toast.error('Failed to copy link')
  }
}
