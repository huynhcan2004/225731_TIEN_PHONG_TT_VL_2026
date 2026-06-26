/// <reference types="vite/client" />
import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { Leaf, Activity } from 'lucide-react'; 
import { useLanguageTheme } from '../../context/LanguageThemeContext';
import { useSiteSettings } from '../../context/SiteSettingsContext';
import toast from 'react-hot-toast';
import { useAuth } from '../../context/AuthContext';
import { isMobileApp } from '../../utils/mobile';


const LoginView: React.FC = () => {
  const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
  const [isRedirecting, setIsRedirecting] = useState(false);
  const { language, setLanguage, currentBg, t } = useLanguageTheme();
  const { siteTitle, siteLogo } = useSiteSettings();
  const { login } = useAuth();

  React.useEffect(() => {
    window.scrollTo(0, 0);
  }, []);

  const handleGoogleLogin = async () => {
    setIsRedirecting(true);
    try {
      if (isMobileApp()) {
        console.log("[Flutter WebView] Bắt đầu đăng nhập Google Hybrid...");
        
        // 1. Sinh ngẫu nhiên session_id
        const sessionId = Math.random().toString(36).substring(2, 15) + Math.random().toString(36).substring(2, 15);
        
        // 2. Đăng ký session với FastAPI backend qua Form data
        const formData = new FormData();
        formData.append('session_id', sessionId);
        
        const registerResponse = await fetch(`${API_URL}/auth/login-session`, {
          method: 'POST',
          body: formData,
        });

        if (!registerResponse.ok) {
          throw new Error("Không thể đăng ký phiên đăng nhập trên hệ thống.");
        }

        // 3. Gửi thông điệp cho Flutter mở Chrome Custom Tab (CCT) qua Bridge
        if ((window as any).FlutterBridge) {
          (window as any).FlutterBridge.postMessage(`GOOGLE_LOGIN:${sessionId}`);
        } else {
          // Fallback nếu chạy trên điện thoại nhưng không tìm thấy bridge (ví dụ: mở link trực tiếp)
          window.location.href = `${API_URL}/auth/google/login?state=${sessionId}`;
          return;
        }

        // 4. Polling kiểm tra trạng thái login của session hàng giây
        let checkAttempts = 0;
        const maxAttempts = 150; // 5 phút (2 giây mỗi lần)
        const pollInterval = setInterval(async () => {
          checkAttempts++;
          if (checkAttempts > maxAttempts) {
            clearInterval(pollInterval);
            setIsRedirecting(false);
            toast.error(language === 'vi' ? 'Hết hạn phiên đăng nhập. Vui lòng thử lại.' : 'Login session expired. Please try again.');
            return;
          }

          try {
            const checkResponse = await fetch(`${API_URL}/auth/login-session/${sessionId}`);
            if (checkResponse.ok) {
              const data = await checkResponse.json();
              if (data && data.status === 'completed' && data.access_token) {
                clearInterval(pollInterval);
                console.log("[Flutter WebView] Đăng nhập thành công, nhận token:", data.access_token);
                await login(data.access_token);
                toast.success(language === 'vi' ? 'Đăng nhập thành công!' : 'Logged in successfully!');
                window.location.href = '/chat';
              }
            }
          } catch (err) {
            console.error("Lỗi khi kiểm tra phiên đăng nhập di động:", err);
          }
        }, 2000);

      } else {
        // Luồng chuẩn trên Web Browser bình thường
        window.location.href = `${API_URL}/auth/google/login`;
      }
    } catch (error) {
      console.error("Lỗi chuyển hướng/xử lý đăng nhập Google:", error);
      setIsRedirecting(false);
      toast.error(language === 'vi' ? 'Không thể kết nối đến máy chủ đăng nhập.' : 'Unable to connect to the authentication server.');
    }
  };


  return (
    <div className="flex items-center justify-center min-h-screen p-4 font-sans overflow-x-hidden relative text-slate-100" style={{ backgroundColor: currentBg.bodyBg }}>
      
      {/* Floating Language Switcher at top right */}
      <div className="absolute top-4 right-4 z-20">
        <button 
          onClick={() => setLanguage(language === 'vi' ? 'en' : 'vi')} 
          className="flex items-center gap-1.5 bg-emerald-950/40 hover:bg-[#08150f] py-1.5 px-3 rounded-full border border-emerald-500/25 text-xs font-bold text-emerald-300 transition-all cursor-pointer shadow-md"
        >
          <span>{language === 'vi' ? '🇻🇳 VI' : '🇬🇧 EN'}</span>
        </button>
      </div>

      {/* Cyber Grid Background */}
      <div className="absolute inset-0 opacity-[0.04] pointer-events-none z-0" 
           style={{ backgroundImage: 'radial-gradient(#1b8961 1px, transparent 1px)', backgroundSize: '32px 32px' }}>
      </div>
      
      {/* Ambient glowing pools of light */}
      <div className="absolute top-[-20%] left-[-20%] w-[60%] h-[60%] rounded-full bg-emerald-500/5 blur-[130px] pointer-events-none z-0 animate-pulse" style={{ animationDuration: '9s' }}></div>
      <div className="absolute bottom-[-20%] right-[-20%] w-[60%] h-[60%] rounded-full bg-amber-500/3 blur-[130px] pointer-events-none z-0 animate-pulse" style={{ animationDuration: '13s' }}></div>

      <div className="relative p-10 shadow-[0_20px_60px_rgba(0,0,0,0.6)] rounded-[2.5rem] w-full max-w-md text-center border border-emerald-500/20 backdrop-blur-md z-10" style={{ backgroundColor: currentBg.panelBg + 'cc' }}>
        
        {/* Logo hình tròn nổi bật với vòng tròn HUD xoay nhẹ */}
        <Link to="/" className="absolute -top-12 left-1/2 -translate-x-1/2 w-24 h-24 rounded-full p-2 shadow-xl border border-emerald-500/20 animate-reverseSpin hover:scale-105 transition-transform block" style={{ backgroundColor: currentBg.panelBg }}>
          <div className="w-full h-full bg-gradient-to-tr from-emerald-600 via-teal-600 to-amber-500 rounded-full flex items-center justify-center shadow-inner relative overflow-hidden">
            {siteLogo ? (
              <img src={siteLogo} alt="Logo" className="w-11 h-11 object-contain rounded-full" />
            ) : (
              <Leaf className="text-emerald-50 w-11 h-11 animate-pulse" />
            )}
            <div className="absolute -inset-1 rounded-full border border-emerald-400/20 animate-spin" style={{ animationDuration: '10s' }}></div>
          </div>
        </Link>

        <div className="mt-10">
          <h2 className="text-2xl font-black text-white mb-2 tracking-tight">
            {siteTitle}
          </h2>
          <p className="text-slate-400 text-xs mb-10 font-bold uppercase tracking-widest leading-relaxed px-4">
            "{t('loginSubtitle')}"
          </p>
          
          <button 
            onClick={handleGoogleLogin}
            disabled={isRedirecting}
            className={`group flex items-center justify-center w-full px-6 py-4 mb-8 text-slate-200 bg-[#08150f] border-2 border-emerald-500/20 rounded-2xl transition-all duration-300 shadow-sm cursor-pointer
              ${isRedirecting ? 'opacity-50 cursor-not-allowed' : 'hover:border-amber-400 hover:bg-emerald-950/40 hover:shadow-[0_0_15px_rgba(193,160,89,0.1)] active:scale-95'}`}
          >
            {isRedirecting ? (
              <div className="w-6 h-6 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin mr-3"></div>
            ) : (
              <img 
                src="https://www.gstatic.com/firebasejs/ui/2.0.0/images/auth/google.svg" 
                alt="Google" 
                className="w-6 h-6 mr-4 group-hover:scale-110 transition-transform" 
              />
            )}
            <span className="font-bold text-base">
              {isRedirecting ? t('redirecting') : t('continueWithGoogle')}
            </span>
          </button>

          {/* Trạng thái hệ thống */}
          <div className="flex flex-col items-center gap-3">
            <div className="flex items-center gap-2 text-emerald-400 bg-emerald-950/45 py-2.5 px-5 rounded-full text-xs font-bold border border-emerald-500/25 shadow-sm shadow-emerald-950/50">
              <Activity className="w-4 h-4 animate-pulse text-emerald-400" />
              {t('systemOnline')}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="mt-12 pt-6 border-t border-emerald-500/10 flex flex-col gap-4">
          <div className="flex flex-wrap justify-center gap-x-4 gap-y-2 text-[11px] font-bold text-slate-400">
            <Link to="/privacy-policy" className="hover:text-emerald-400 transition-colors">{t('privacy')}</Link>
            <span className="text-emerald-950">•</span>
            <Link to="/terms-of-service" className="hover:text-emerald-400 transition-colors">{t('terms')}</Link>
            <span className="text-emerald-950">•</span>
            <Link to="/data-deletion" className="hover:text-emerald-400 transition-colors">{t('dataDeletion')}</Link>
            <span className="text-emerald-950">•</span>
            <Link to="/support" className="hover:text-emerald-400 transition-colors">{t('support')}</Link>
            <span className="text-emerald-950">•</span>
            <Link to="/contact" className="hover:text-emerald-400 transition-colors">{t('contact')}</Link>
          </div>
          <p className="text-[9px] uppercase tracking-[0.2em] text-slate-500 font-black">
            Final Project 2026 • Computer Science
          </p>
        </div>
      </div>

    </div>
  );
};

export default LoginView;