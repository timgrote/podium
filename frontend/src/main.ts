import { createApp } from 'vue'
import PrimeVue from 'primevue/config'
import Aura from '@primevue/themes/aura'
import { definePreset } from '@primevue/themes'
import ToastService from 'primevue/toastservice'
import ConfirmationService from 'primevue/confirmationservice'
import 'primeicons/primeicons.css'
import './style.css'
import App from './App.vue'
import router from './router'
import customBluePreset from './theme-preset-blue'

const MyPreset = definePreset(Aura, customBluePreset)

const app = createApp(App)

app.use(router)
app.use(PrimeVue, {
  theme: {
    preset: MyPreset,
    options: {
      darkModeSelector: '.app-dark',
    },
  },
})
app.use(ToastService)
app.use(ConfirmationService)

app.config.errorHandler = (err, _instance, info) => {
  console.error('Unhandled app error:', err, info)
}

app.mount('#app')
