/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_URL: string;
  // Khai báo thêm các biến môi trường VITE_ khác tại đây nếu có
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}