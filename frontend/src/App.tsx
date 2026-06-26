/// <reference types="vite/client" />
import { Routes, Route, Navigate } from 'react-router-dom';

// 1. Import các thành phần xác thực (Auth)
import LoginView from './components/auth/LoginView';
import AuthCallback from './components/auth/AuthCallback';
import ProtectedRoute from './components/auth/ProtectedRoute';
import PublicRoute from './components/auth/PublicRoute';

// 2. Import các thành phần giao diện người dùng (User)
import ChatView from './components/auth/ChatView';
import KnowledgeGraphView from './components/chat/KnowledgeGraphView';

// 3. Import các thành phần quản trị (Admin)
import SeoManager from './components/admin/SeoManager';
import { AdminLayout } from './components/admin/AdminLayout';
import { AdminDashboard } from './components/admin/AdminDashboard';
import { UserList } from './components/admin/UserList';
import { FinanceManager } from './components/admin/FinanceManager';
import { AiSettings } from './components/admin/AiSettings';

// 4. Import các trang thông tin công khai (Chính sách & Hỗ trợ & Landing Page)
import LandingPage from './components/public/LandingPage';
import PrivacyPolicy from './components/public/PrivacyPolicy';
import TermsOfService from './components/public/TermsOfService';
import DataDeletion from './components/public/DataDeletion';
import Support from './components/public/Support';
import Contact from './components/public/Contact';

/**
 * Component App: Điều phối toàn bộ tuyến đường (Routes) của hệ thống YHCT Diamond.
 */
function App() {
  return (
    <Routes>
      {/* ------------------------------------------------------------------
          A. CÁC TUYẾN ĐƯỜNG CÔNG KHAI (PUBLIC ROUTES)
      ------------------------------------------------------------------- */}
      {/* Landing page công khai */}
      <Route path="/" element={<LandingPage />} />

      {/* Sử dụng PublicRoute để chặn người dùng đã login quay lại trang đăng nhập. */}
      <Route element={<PublicRoute />}>
        <Route path="/login" element={<LoginView />} />
      </Route>

      {/* Trang trung gian xử lý token từ Google OAuth - Không cần bảo vệ */}
      <Route path="/auth/callback" element={<AuthCallback />} />


      {/* ------------------------------------------------------------------
          B. KHU VỰC NGƯỜI DÙNG (USER ROUTES)
          Yêu cầu: Đã đăng nhập thành công.
      ------------------------------------------------------------------- */}
      <Route element={<ProtectedRoute />}>
        <Route path="/chat" element={<ChatView />} />
        
        {/* ✨ TUYẾN ĐƯỜNG MỚI: BẢN ĐỒ TRI THỨC TOÀN MÀN HÌNH */}
        <Route path="/graph-explorer" element={<KnowledgeGraphView />} />
      </Route>


      {/* ------------------------------------------------------------------
          C. KHU VỰC QUẢN TRỊ VIÊN (ADMIN ROUTES)
          Yêu cầu: Đã đăng nhập VÀ có role === 'admin'.
      ------------------------------------------------------------------- */}
      <Route element={<ProtectedRoute adminOnly={true} />}>
        <Route path="/admin" element={<AdminLayout />}>
          {/* Trang tổng quan Admin */}
          <Route index element={<AdminDashboard />} />
          
          {/* Các trang quản lý chuyên sâu */}
          <Route path="seo" element={<SeoManager />} />
          <Route path="users" element={<UserList />} />
          <Route path="finance" element={<FinanceManager />} />
          <Route path="settings" element={<AiSettings />} />
        </Route>
      </Route>


      {/* ------------------------------------------------------------------
          D. CÁC TUYẾN ĐƯỜNG CHÍNH SÁCH VÀ HỖ TRỢ CÔNG KHAI
          Không cần đăng nhập vẫn xem được.
      ------------------------------------------------------------------- */}
      <Route path="/privacy-policy" element={<PrivacyPolicy />} />
      <Route path="/terms-of-service" element={<TermsOfService />} />
      <Route path="/data-deletion" element={<DataDeletion />} />
      <Route path="/support" element={<Support />} />
      <Route path="/contact" element={<Contact />} />


      {/* ------------------------------------------------------------------
          E. XỬ LÝ LỖI ĐƯỜNG DẪN (404 NOT FOUND)
          Tự động đẩy về trang chủ nếu gõ sai URL hoặc truy cập trái phép.
      ------------------------------------------------------------------- */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default App;