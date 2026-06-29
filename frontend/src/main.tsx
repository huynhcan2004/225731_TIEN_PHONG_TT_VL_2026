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
import { isMobileApp } from './utils/mobile'

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
  let finalInput = input;
  
  if (isMobileApp() && apiBaseUrl && url && url.startsWith(targetApiUrl)) {
    const newUrl = url.replace(targetApiUrl, apiBaseUrl);
    console.log(`[Fetch Proxy] Redirecting request from ${url} to ${newUrl}`);
    url = newUrl;
    if (typeof input === 'string') {
      finalInput = newUrl;
    } else {
      finalInput = new Request(newUrl, input as Request);
    }
  }

  // Inject ngrok bypass header to prevent browser warning page blocking cross-origin API calls
  if (url && (url.includes('ngrok-free.app') || url.includes('ngrok-free.dev'))) {
    init = init || {};
    init.headers = init.headers || {};
    
    if (finalInput instanceof Request) {
      try {
        finalInput.headers.set('ngrok-skip-browser-warning', 'true');
      } catch (e) {
        // Safe fallback
      }
    }
    
    if (init.headers instanceof Headers) {
      init.headers.set('ngrok-skip-browser-warning', 'true');
    } else if (Array.isArray(init.headers)) {
      init.headers.push(['ngrok-skip-browser-warning', 'true']);
    } else {
      init.headers = {
        ...init.headers,
        'ngrok-skip-browser-warning': 'true'
      };
    }
  }
  
  return originalFetch(finalInput, init);
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