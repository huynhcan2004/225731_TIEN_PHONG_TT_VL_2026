// frontend/src/main.tsx
import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.tsx'
import './index.css' // Phải có file index.css (đã cấu hình Tailwind)
import { BrowserRouter } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import { AuthProvider } from './context/AuthContext'
import { LanguageThemeProvider } from './context/LanguageThemeContext'
import { SiteSettingsProvider } from './context/SiteSettingsContext'

// Parse api_base_url from query parameters if present, and save to localStorage
const urlParams = new URLSearchParams(window.location.search);
const urlApiUrl = urlParams.get('api_base_url');
if (urlApiUrl) {
  localStorage.setItem('api_base_url', urlApiUrl);
}

// Hook fetch to redirect api calls to the injected base url on mobile
const originalFetch = window.fetch;
const targetApiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';

window.fetch = function(input, init) {
  const apiBaseUrl = localStorage.getItem('api_base_url');
  let url = typeof input === 'string' ? input : (input as Request).url;
  
  if (apiBaseUrl && url && url.startsWith(targetApiUrl)) {
    const newUrl = url.replace(targetApiUrl, apiBaseUrl);
    console.log(`[Fetch Proxy] Redirecting request from ${url} to ${newUrl}`);
    
    if (typeof input === 'string') {
      return originalFetch(newUrl, init);
    } else {
      const newRequest = new Request(newUrl, input as Request);
      return originalFetch(newRequest, init);
    }
  }
  return originalFetch(input, init);
};

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <LanguageThemeProvider>
          <SiteSettingsProvider>
            <App />
          </SiteSettingsProvider>
          {/* Đặt Toaster ở đây 1 lần duy nhất để dùng chung cho toàn App */}
          <Toaster position="top-right" />
        </LanguageThemeProvider>
      </AuthProvider>
    </BrowserRouter>
  </React.StrictMode>,
);