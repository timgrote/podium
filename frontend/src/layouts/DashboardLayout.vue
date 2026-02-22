<script setup lang="ts">
import { ref } from 'vue'
import Toast from 'primevue/toast'
import { useColorMode } from '../composables/useColorMode'
import { useAuth } from '../composables/useAuth'

const sidebarCollapsed = ref(false)
const { isDark, toggleColorMode } = useColorMode()
const { user, logout } = useAuth()
const showUserMenu = ref(false)

const navItems = [
  { label: 'Dashboard', icon: 'pi pi-home', route: '/dashboard' },
]

function userInitials(): string {
  if (!user.value) return '?'
  const f = user.value.first_name?.[0] || ''
  const l = user.value.last_name?.[0] || ''
  return (f + l).toUpperCase() || '?'
}

function handleLogout() {
  showUserMenu.value = false
  logout()
}
</script>

<template>
  <Toast />
  <div class="layout">
    <aside class="sidebar" :class="{ collapsed: sidebarCollapsed }">
      <div class="sidebar-header">
        <h2 v-if="!sidebarCollapsed">Conductor</h2>
        <button class="toggle-btn" @click="sidebarCollapsed = !sidebarCollapsed">
          <i :class="sidebarCollapsed ? 'pi pi-angle-right' : 'pi pi-angle-left'" />
        </button>
      </div>
      <nav class="sidebar-nav">
        <router-link
          v-for="item in navItems"
          :key="item.route"
          :to="item.route"
          class="nav-item"
        >
          <i :class="item.icon" />
          <span v-if="!sidebarCollapsed">{{ item.label }}</span>
        </router-link>
      </nav>
      <div class="sidebar-footer">
        <div v-if="user" class="user-section">
          <button class="user-btn" @click="showUserMenu = !showUserMenu">
            <img
              v-if="user.avatar_url"
              :src="user.avatar_url"
              :alt="userInitials()"
              class="avatar-img"
            />
            <span v-else class="avatar-initials">{{ userInitials() }}</span>
            <span v-if="!sidebarCollapsed" class="user-name">
              {{ user.first_name }} {{ user.last_name }}
            </span>
          </button>
          <div v-if="showUserMenu" class="user-menu">
            <router-link class="menu-item" to="/profile" @click="showUserMenu = false">
              <i class="pi pi-user" />
              Profile
            </router-link>
            <button class="menu-item" @click="handleLogout">
              <i class="pi pi-sign-out" />
              Logout
            </button>
          </div>
        </div>
        <button class="toggle-btn theme-btn" @click="toggleColorMode">
          <i :class="isDark ? 'pi pi-sun' : 'pi pi-moon'" />
          <span v-if="!sidebarCollapsed">{{ isDark ? 'Light' : 'Dark' }}</span>
        </button>
      </div>
    </aside>
    <main class="main-content">
      <slot />
    </main>
  </div>
</template>

<style scoped>
.layout {
  display: flex;
  min-height: 100vh;
}

.sidebar {
  width: 240px;
  height: 100vh;
  position: fixed;
  top: 0;
  left: 0;
  background: var(--p-surface-900);
  color: var(--p-surface-200);
  display: flex;
  flex-direction: column;
  transition: width 0.2s;
  z-index: 10;
}

.sidebar.collapsed {
  width: 60px;
}

.sidebar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1rem;
  border-bottom: 1px solid var(--p-surface-800);
}

.sidebar-header h2 {
  font-size: 1.25rem;
  font-weight: 600;
  margin: 0;
  white-space: nowrap;
}

.toggle-btn {
  background: none;
  border: none;
  color: var(--p-surface-400);
  cursor: pointer;
  padding: 0.25rem;
  font-size: 1rem;
}

.toggle-btn:hover {
  color: var(--p-surface-200);
}

.sidebar-nav {
  display: flex;
  flex-direction: column;
  padding: 0.5rem;
  gap: 0.25rem;
  flex: 1;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem;
  border-radius: 0.375rem;
  color: var(--p-surface-300);
  text-decoration: none;
  font-size: 0.875rem;
  transition: background 0.15s;
}

.nav-item:hover {
  background: var(--p-surface-800);
}

.nav-item.router-link-active {
  background: var(--p-surface-800);
  color: #fff;
}

.sidebar-footer {
  padding: 0.5rem;
  border-top: 1px solid var(--p-surface-800);
}

.user-section {
  position: relative;
  margin-bottom: 0.25rem;
}

.user-btn {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  width: 100%;
  padding: 0.625rem 0.75rem;
  background: none;
  border: none;
  border-radius: 0.375rem;
  color: var(--p-surface-300);
  cursor: pointer;
  font-size: 0.875rem;
  text-align: left;
}

.user-btn:hover {
  background: var(--p-surface-800);
}

.avatar-img {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  object-fit: cover;
  flex-shrink: 0;
}

.avatar-initials {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: var(--p-surface-700);
  color: var(--p-surface-200);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.7rem;
  font-weight: 600;
  flex-shrink: 0;
}

.user-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.user-menu {
  position: absolute;
  bottom: 100%;
  left: 0.5rem;
  right: 0.5rem;
  margin-bottom: 0.25rem;
  background: var(--p-surface-800);
  border: 1px solid var(--p-surface-700);
  border-radius: 0.375rem;
  padding: 0.25rem;
  z-index: 20;
}

.menu-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  width: 100%;
  padding: 0.5rem 0.75rem;
  background: none;
  border: none;
  border-radius: 0.25rem;
  color: var(--p-surface-300);
  font-size: 0.8125rem;
  cursor: pointer;
  text-decoration: none;
}

.menu-item:hover {
  background: var(--p-surface-700);
  color: var(--p-surface-100);
}

.theme-btn {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  width: 100%;
  padding: 0.75rem;
  border-radius: 0.375rem;
  font-size: 0.875rem;
}

.theme-btn:hover {
  background: var(--p-surface-800);
}

.main-content {
  flex: 1;
  padding: 1.5rem;
  margin-left: 240px;
  overflow-y: auto;
  transition: margin-left 0.2s;
}

.sidebar.collapsed + .main-content {
  margin-left: 60px;
}
</style>
