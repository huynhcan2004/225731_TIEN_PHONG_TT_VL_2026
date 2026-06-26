/// <reference types="vite/client" />
import React from 'react';
import { Navigate, Outlet } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';

/**
 * Component PublicRoute: Bảo vệ các trang công khai (như Login).
 * Nhiệm vụ: Nếu người dùng đã có 'role' và 'user' trong hệ thống, 
 * sẽ không cho phép họ quay lại trang đăng nhập.
 */
const PublicRoute: React.FC = () => {
  const { user, loading } = useAuth();

  // 1. TRẠNG THÁI ĐANG TẢI: Giữ chân người dùng tại chỗ để kiểm tra token
  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[100dvh] bg-white overflow-hidden">
        <div className="w-10 h-10 border-4 border-emerald-500 border-t-transparent rounded-full animate-spin"></div>
        <p className="mt-4 text-slate-500 text-xs font-medium uppercase tracking-widest">
          Đang đồng bộ phiên làm việc...
        </p>
      </div>
    );
  }

  // 2. KIỂM TRA ĐĂNG NHẬP: 
  // Nếu đã có thông tin user, tự động điều hướng về trang chủ
  if (user) {
    return <Navigate to="/chat" replace />;
  }

  // 3. NẾU CHƯA ĐĂNG NHẬP: Cho phép truy cập vào trang Login (Outlet)
  return <Outlet />;
};

export default PublicRoute;