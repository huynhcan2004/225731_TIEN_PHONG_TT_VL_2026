import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,         // Khóa cứng cổng 5173 để tránh bị đổi cổng ngẫu nhiên do IDE/Terminal gán biến PORT
    allowedHosts: true, // Cho phép tất cả các host (bao gồm cả Ngrok) truy cập vào Vite Dev Server
  }
})
