import { ref, computed, watch } from 'vue'

type ColorMode = 'light' | 'dark' | 'system'

const colorMode = ref<ColorMode>((localStorage.getItem('theme') as ColorMode) || 'system')

const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')

function applyTheme() {
  const shouldBeDark =
    colorMode.value === 'dark' ||
    (colorMode.value === 'system' && mediaQuery.matches)

  document.documentElement.classList.toggle('app-dark', shouldBeDark)
}

// Apply on load
applyTheme()

// React to changes
watch(colorMode, (val) => {
  localStorage.setItem('theme', val)
  applyTheme()
})

// Listen for OS theme changes
mediaQuery.addEventListener('change', applyTheme)

const isDark = computed(
  () =>
    colorMode.value === 'dark' ||
    (colorMode.value === 'system' && mediaQuery.matches),
)

function toggleColorMode() {
  colorMode.value = isDark.value ? 'light' : 'dark'
}

function setColorMode(mode: ColorMode) {
  colorMode.value = mode
}

export function useColorMode() {
  return { colorMode, isDark, toggleColorMode, setColorMode }
}
