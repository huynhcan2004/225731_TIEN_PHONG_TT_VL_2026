/// <reference types="vite/client" />
import React from 'react';
import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';

interface ProtectedRouteProps {
  adminOnly?: boolean; // Xác định route yêu cầu quyền quản trị viên
}

const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ adminOnly = false }) => {
  const { user, loading } = useAuth();
  const location = useLocation();

  // 1. Trạng thái Loading: Hiển thị màn hình chờ thẩm định để tránh Redirect Loop
  // và lỗi 401 khi ứng dụng chưa kịp cập nhật trạng thái Auth toàn cục
  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[100dvh] bg-emerald-50/20 overflow-hidden">
        <div className="relative">
          <div className="w-14 h-14 border-4 border-emerald-200 rounded-full animate-pulse"></div>
          <div className="absolute top-0 left-0 w-14 h-14 border-4 border-[#2c4a3e] border-t-transparent rounded-full animate-spin"></div>
        </div>
        <p className="mt-6 text-[#2c4a3e] font-bold tracking-wide animate-pulse uppercase text-xs">
          Đang thẩm định quyền truy cập tri thức...
        </p>
      </div>
    );
  }

  // 2. Kiểm tra đăng nhập: Nếu chưa có User, lưu vị trí hiện tại và đá về trang Login
  if (!user) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  // 3. Kiểm tra quyền Admin: Chặn người dùng thường vào khu vực quản trị
  if (adminOnly && user.role !== 'admin') {
    console.warn(`Cảnh báo: Người dùng ${user.email} cố gắng truy cập trái phép khu vực quản trị.`);
    // Chuyển hướng về trang chủ để đảm bảo an toàn hệ thống
    return <Navigate to="/" replace />;
  }

  // 4. Hợp lệ: Cho phép truy cập vào các tuyến đường con
  return <Outlet />;
};

export default ProtectedRoute;