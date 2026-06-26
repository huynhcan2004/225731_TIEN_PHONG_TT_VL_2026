import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    allowedHosts: true, // Cho phép tất cả các host (bao gồm cả Ngrok) truy cập vào Vite Dev Server
  }
})
