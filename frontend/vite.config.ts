import { defineConfig } from 'vitest/config'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    host: '0.0.0.0',
    port: 3001,
    proxy: {
      '/api': {
        target: 'http://100.86.206.66:3001',
        changeOrigin: true,
      },
      '/uploads': {
        target: 'http://100.86.206.66:3001',
        changeOrigin: true,
      },
    },
  },
  test: {
    environment: 'node',
  },
})
