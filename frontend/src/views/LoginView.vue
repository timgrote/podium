<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuth } from '../composables/useAuth'
import { ApiError } from '../api/client'

const { login, signup } = useAuth()
const route = useRoute()
const router = useRouter()

const mode = ref<'login' | 'signup'>('login')
const email = ref('')
const password = ref('')
const error = ref('')
const submitting = ref(false)

async function handleSubmit() {
  error.value = ''
  submitting.value = true
  try {
    if (mode.value === 'login') {
      await login(email.value, password.value)
    } else {
      await signup(email.value, password.value)
    }
    const raw = (route.query.redirect as string) || '/dashboard'
    const redirect = raw.startsWith('/') && !raw.startsWith('//') ? raw : '/dashboard'
    router.push(redirect)
  } catch (e) {
    if (e instanceof ApiError) {
      error.value = e.detail
    } else {
      error.value = 'Something went wrong. Try again.'
    }
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="login-page">
    <div class="login-card">
      <h1>Conductor</h1>
      <p class="subtitle">{{ mode === 'login' ? 'Sign in to your account' : 'Create an account' }}</p>

      <form @submit.prevent="handleSubmit">
        <div class="field">
          <label for="email">Email</label>
          <input
            id="email"
            v-model="email"
            type="email"
            autocomplete="email"
            required
          />
        </div>
        <div class="field">
          <label for="password">Password</label>
          <input
            id="password"
            v-model="password"
            type="password"
            autocomplete="current-password"
            required
          />
        </div>

        <div v-if="error" class="error-msg">{{ error }}</div>

        <button type="submit" class="submit-btn" :disabled="submitting">
          {{ submitting ? 'Please wait...' : mode === 'login' ? 'Sign In' : 'Sign Up' }}
        </button>
      </form>

      <p class="toggle-mode">
        {{ mode === 'login' ? "Don't have an account?" : 'Already have an account?' }}
        <button class="link-btn" @click="mode = mode === 'login' ? 'signup' : 'login'; error = ''">
          {{ mode === 'login' ? 'Sign Up' : 'Sign In' }}
        </button>
      </p>
    </div>
  </div>
</template>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--p-surface-950, #0a0a0f);
}

.login-card {
  width: 100%;
  max-width: 400px;
  padding: 2.5rem;
  background: var(--p-surface-900, #111827);
  border: 1px solid var(--p-surface-800, #1f2937);
  border-radius: 0.75rem;
}

.login-card h1 {
  margin: 0 0 0.25rem;
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--p-surface-50, #f9fafb);
}

.subtitle {
  margin: 0 0 1.5rem;
  font-size: 0.875rem;
  color: var(--p-surface-400, #9ca3af);
}

.field {
  margin-bottom: 1rem;
}

.field label {
  display: block;
  margin-bottom: 0.375rem;
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--p-surface-300, #d1d5db);
}

.field input {
  width: 100%;
  padding: 0.625rem 0.75rem;
  font-size: 0.875rem;
  color: var(--p-surface-50, #f9fafb);
  background: var(--p-surface-800, #1f2937);
  border: 1px solid var(--p-surface-700, #374151);
  border-radius: 0.375rem;
  outline: none;
  box-sizing: border-box;
}

.field input:focus {
  border-color: var(--p-primary-500, #6366f1);
  box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.2);
}

.error-msg {
  margin-bottom: 1rem;
  padding: 0.625rem 0.75rem;
  font-size: 0.8125rem;
  color: #fca5a5;
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.2);
  border-radius: 0.375rem;
}

.submit-btn {
  width: 100%;
  padding: 0.625rem;
  font-size: 0.875rem;
  font-weight: 600;
  color: #fff;
  background: var(--p-primary-500, #6366f1);
  border: none;
  border-radius: 0.375rem;
  cursor: pointer;
}

.submit-btn:hover:not(:disabled) {
  background: var(--p-primary-400, #818cf8);
}

.submit-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.toggle-mode {
  margin-top: 1.25rem;
  text-align: center;
  font-size: 0.8125rem;
  color: var(--p-surface-400, #9ca3af);
}

.link-btn {
  background: none;
  border: none;
  color: var(--p-primary-400, #818cf8);
  cursor: pointer;
  font-size: 0.8125rem;
  padding: 0;
}

.link-btn:hover {
  text-decoration: underline;
}
</style>
