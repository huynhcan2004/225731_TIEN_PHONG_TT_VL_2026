import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 51582,        // Khóa cứng cổng 51582 theo yêu cầu
    allowedHosts: true, // Cho phép tất cả các host (bao gồm cả Ngrok) truy cập vào Vite Dev Server
  }
})
