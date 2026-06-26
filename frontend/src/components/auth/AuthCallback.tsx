import React, { useEffect, useRef } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import toast from 'react-hot-toast';
import { useAuth } from '../../context/AuthContext';

const AuthCallback: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { login } = useAuth();
  const hasProcessed = useRef(false);

  useEffect(() => {
    const processAuth = async () => {
      if (hasProcessed.current) return;
      
      const token = searchParams.get('access_token');

      if (token) {
        hasProcessed.current = true;
        try {
          // 1. Chạy hàm login từ Context (Hàm này trả về void nên không gán vào biến)
          await login(token);
          
          toast.success('Xác thực thành công! Chào mừng bạn quay lại.');
          
          // 2. Tự gọi API để lấy thông tin User và quyết định chuyển hướng
          const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
          const response = await fetch(`${API_URL}/auth/me`, {
            headers: {
              'Authorization': `Bearer ${token}`
            }
          });

          if (response.ok) {
            const userData = await response.json();
            // Điều hướng thông minh theo Role
            if (userData.role === 'admin') {
              navigate('/admin');
            } else {
              navigate('/chat');
            }
          } else {
            // Nếu không gọi được profile, mặc định về trang chủ
            navigate('/');
          }

        } catch (error) {
          console.error("Lỗi đồng bộ hóa phiên làm việc:", error);
          toast.error('Có lỗi xảy ra trong quá trình đồng bộ dữ liệu.');
          navigate('/login');
        }
      } else {
        hasProcessed.current = true;
        toast.error('Không tìm thấy mã xác thực. Vui lòng đăng nhập lại.');
        navigate('/login');
      }
    };

    processAuth();
  }, [searchParams, navigate, login]);

  return (
    <div className="flex flex-col items-center justify-center min-h-[100dvh] bg-emerald-50 overflow-hidden">
      <div className="w-12 h-12 border-4 border-[#2c4a3e] border-t-transparent rounded-full animate-spin"></div>
      <p className="mt-4 text-[#2c4a3e] font-medium animate-pulse">
        Đang đồng bộ hóa tri thức YHCT...
      </p>
    </div>
  );
};

export default AuthCallback;