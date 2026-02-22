<script setup lang="ts">
import { ref, watch } from 'vue'
import { useAuth } from '../composables/useAuth'
import { useToast } from '../composables/useToast'

const { user, updateAvatar, updateProfile } = useAuth()
const toast = useToast()

const form = ref({
  first_name: '',
  last_name: '',
  email: '',
})

const saving = ref(false)
const avatarInput = ref<HTMLInputElement>()

watch(
  () => user.value,
  (u) => {
    if (u) {
      form.value = {
        first_name: u.first_name || '',
        last_name: u.last_name || '',
        email: u.email || '',
      }
    }
  },
  { immediate: true },
)

function userInitials(): string {
  if (!user.value) return '?'
  const f = user.value.first_name?.[0] || ''
  const l = user.value.last_name?.[0] || ''
  return (f + l).toUpperCase() || '?'
}

async function save() {
  saving.value = true
  try {
    await updateProfile(form.value)
    toast.success('Profile updated')
  } catch (e) {
    toast.error(String(e))
  } finally {
    saving.value = false
  }
}

async function onAvatarChange(event: Event) {
  const file = (event.target as HTMLInputElement).files?.[0]
  if (!file) return
  try {
    await updateAvatar(file)
    toast.success('Avatar updated')
  } catch (e) {
    toast.error(String(e))
  }
}
</script>

<template>
  <div class="profile-page">
    <h1>Profile</h1>
    <div class="profile-card">
      <div class="avatar-section">
        <div class="avatar-wrapper" @click="avatarInput?.click()">
          <img
            v-if="user?.avatar_url"
            :src="user.avatar_url"
            :alt="userInitials()"
            class="avatar-img"
          />
          <span v-else class="avatar-initials">{{ userInitials() }}</span>
          <div class="avatar-overlay">
            <i class="pi pi-camera" />
          </div>
        </div>
        <input
          ref="avatarInput"
          type="file"
          accept="image/jpeg,image/png,image/gif,image/webp"
          class="hidden"
          @change="onAvatarChange"
        />
        <p class="avatar-hint">Click to change</p>
      </div>
      <div class="form">
        <div class="field-group">
          <div class="field">
            <label>First Name</label>
            <input v-model="form.first_name" type="text" />
          </div>
          <div class="field">
            <label>Last Name</label>
            <input v-model="form.last_name" type="text" />
          </div>
        </div>
        <div class="field">
          <label>Email</label>
          <input v-model="form.email" type="email" />
        </div>
        <div class="actions">
          <button class="btn btn-primary" :disabled="saving" @click="save">
            {{ saving ? 'Saving...' : 'Save Changes' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.profile-page {
  max-width: 480px;
}

.profile-page h1 {
  font-size: 1.5rem;
  font-weight: 600;
  margin-bottom: 1.5rem;
  color: var(--p-text-color);
}

.profile-card {
  background: var(--p-content-background);
  border-radius: 0.5rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  padding: 2rem;
}

.avatar-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  margin-bottom: 2rem;
}

.avatar-wrapper {
  position: relative;
  width: 80px;
  height: 80px;
  border-radius: 50%;
  cursor: pointer;
  overflow: hidden;
}

.avatar-wrapper .avatar-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.avatar-wrapper .avatar-initials {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--p-surface-200);
  color: var(--p-surface-600);
  font-size: 1.5rem;
  font-weight: 600;
}

.avatar-overlay {
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity 0.15s;
  color: #fff;
  font-size: 1.25rem;
}

.avatar-wrapper:hover .avatar-overlay {
  opacity: 1;
}

.avatar-hint {
  margin-top: 0.5rem;
  font-size: 0.75rem;
  color: var(--p-text-muted-color);
}

.hidden {
  display: none;
}

.form {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.field label {
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--p-text-muted-color);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.field input {
  padding: 0.5rem 0.75rem;
  border: 1px solid var(--p-form-field-border-color);
  border-radius: 0.375rem;
  font-size: 0.875rem;
  background: var(--p-form-field-background);
  color: var(--p-text-color);
}

.field-group {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}

.actions {
  margin-top: 0.5rem;
}

.btn {
  padding: 0.5rem 1rem;
  border: 1px solid var(--p-content-border-color);
  border-radius: 0.375rem;
  background: var(--p-content-background);
  cursor: pointer;
  font-size: 0.875rem;
  color: var(--p-text-color);
}

.btn-primary {
  background: var(--p-primary-color);
  color: #fff;
  border-color: var(--p-primary-color);
}

.btn-primary:hover {
  background: var(--p-primary-hover-color);
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
