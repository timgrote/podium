import { ref, computed } from 'vue'
import type { Employee } from '../types'
import * as authApi from '../api/auth'
import { updateEmployee } from '../api/employees'
import router from '../router'

const user = ref<Employee | null>(null)
const loading = ref(true)

let sessionChecked = false
let sessionPromise: Promise<void> | null = null

export function useAuth() {
  const isAuthenticated = computed(() => user.value !== null)

  function checkSession(): Promise<void> {
    if (sessionChecked) return Promise.resolve()
    if (sessionPromise) return sessionPromise

    sessionPromise = authApi
      .fetchMe()
      .then((me) => {
        user.value = me
      })
      .catch(() => {
        user.value = null
      })
      .finally(() => {
        loading.value = false
        sessionChecked = true
      })

    return sessionPromise
  }

  async function login(email: string, password: string) {
    const me = await authApi.login(email, password)
    user.value = me
    sessionChecked = true
    loading.value = false
  }

  async function signup(email: string, password: string) {
    const me = await authApi.signup(email, password)
    user.value = me
    sessionChecked = true
    loading.value = false
  }

  async function logout() {
    try {
      await authApi.logout()
    } catch {
      // Clear client state even if server-side cleanup fails
    }
    user.value = null
    sessionChecked = false
    sessionPromise = null
    router.push('/login')
  }

  async function updateAvatar(file: File) {
    const me = await authApi.uploadAvatar(file)
    if (user.value) {
      user.value = { ...user.value, avatar_url: me.avatar_url }
    }
  }

  async function updateProfile(data: { first_name?: string; last_name?: string; email?: string }) {
    if (!user.value) return
    const updated = await updateEmployee(user.value.id, data)
    user.value = { ...user.value, ...updated }
  }

  function clearUser() {
    user.value = null
    sessionChecked = false
    sessionPromise = null
    loading.value = false
  }

  return {
    user,
    loading,
    isAuthenticated,
    checkSession,
    login,
    signup,
    logout,
    updateAvatar,
    updateProfile,
    clearUser,
  }
}
