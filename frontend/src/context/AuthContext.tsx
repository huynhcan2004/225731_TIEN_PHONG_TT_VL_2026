/// <reference types="vite/client" />
import React, { createContext, useContext, useState, useEffect } from 'react';
import toast from 'react-hot-toast';
import { isMobileApp } from '../utils/mobile';


// Thêm định nghĩa User (Nếu huynh có file types riêng thì import vào)
interface User {
  id: string;
  email: string;
  username?: string;
  avatar_url?: string;
  role?: string; // Thêm thuộc tính role
  token_balance?: number;
  is_root_admin?: boolean; // Thêm thuộc tính is_root_admin
}

interface AuthContextType {
  user: User | null;
  loading: boolean;
  login: (token: string) => Promise<void>; // CHÚ Ý: Đổi thành Promise
  logout: (showToast?: boolean) => void;
  refreshUser: () => Promise<void>; 
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const refreshUser = async () => {
    // ✨ ĐỒNG BỘ: Sử dụng 'access_token' thay vì 'token'
    const token = localStorage.getItem('access_token');
    if (!token) {
      setLoading(false);
      return;
    }

    try {
      const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      
      const res = await fetch(`${API_URL}/auth/me`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (res.ok) {
        const data = await res.json();
        setUser(data);
      } else {
        if (res.status === 401 || res.status === 403) {
          logout(false);
        }
      }
    } catch (error) {
      console.error("Lỗi đồng bộ user (AuthContext):", error);
    } finally {
      setLoading(false); 
    }
  };

  // CHÚ Ý: Đã chuyển thành async function
  const login = async (token: string) => {
    // ✨ ĐỒNG BỘ: Lưu bằng khóa 'access_token' để ChatView có thể tìm thấy
    localStorage.setItem('access_token', token);
    setLoading(true); 
    await refreshUser(); // ĐỢI LẤY XONG THÔNG TIN USER MỚI ĐI TIẾP
  };

  const logout = (showToast: boolean = true) => {
    // ✨ ĐỒNG BỘ: Xóa đúng khóa 'access_token'
    localStorage.removeItem('access_token');
    setUser(null);
    if (showToast) {
      toast.success('Hẹn gặp lại bạn!');
    }

    // Gửi tín hiệu LOGOUT sang Flutter nếu ở trong WebView
    if (isMobileApp() && (window as any).FlutterBridge) {
      try {
        (window as any).FlutterBridge.postMessage('LOGOUT');
      } catch (e) {
        console.error('Error posting LOGOUT to Flutter:', e);
      }
    }

    window.location.href = '/login'; 
  };

  useEffect(() => {
    refreshUser();

    // Lắng nghe sự kiện token từ Flutter để tự đăng nhập
    const handleFlutterToken = async (e: Event) => {
      const customEvent = e as CustomEvent;
      const token = customEvent.detail?.token;
      if (token) {
        console.log("Token received from Flutter event:", token);
        await login(token);
      }
    };

    window.addEventListener('flutter_token_ready', handleFlutterToken);
    return () => {
      window.removeEventListener('flutter_token_ready', handleFlutterToken);
    };
  }, []);


  return (
    <AuthContext.Provider value={{ user, loading, login, logout, refreshUser }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used within AuthProvider');
  return context;
};