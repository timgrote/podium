<script setup lang="ts">
import { useRoute } from 'vue-router'
import DashboardLayout from './layouts/DashboardLayout.vue'

const route = useRoute()
</script>

<template>
  <DashboardLayout v-if="route.meta.layout === 'dashboard'">
    <RouterView />
  </DashboardLayout>
  <RouterView v-else />
</template>
