import React, { useState, useEffect, useRef } from 'react';
import toast from 'react-hot-toast';
import { Save, Globe, AlertCircle, RefreshCcw, Loader2, Upload } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { useSiteSettings } from '../../context/SiteSettingsContext';

const SeoManager: React.FC = () => {
  const { user } = useAuth();
  const { refreshSettings } = useSiteSettings();
  const [isSyncing, setIsSyncing] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleLogoUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (file.size > 5 * 1024 * 1024) {
      toast.error('Kích thước ảnh không được vượt quá 5MB.');
      return;
    }

    const toastId = toast.loading('Đang tải ảnh lên máy chủ...');
    setIsUploading(true);

    try {
      const token = localStorage.getItem('access_token');
      const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

      const formDataPayload = new FormData();
      formDataPayload.append('file', file);

      const res = await fetch(`${API_URL}/admin/upload-logo`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        },
        body: formDataPayload
      });

      const data = await res.json();
      if (res.ok) {
        setFormData(prev => ({ ...prev, site_logo: data.logo_url }));
        toast.success('Tải ảnh logo thành công!', { id: toastId });
      } else {
        toast.error(data.detail || 'Lỗi tải ảnh lên máy chủ.', { id: toastId });
      }
    } catch (error) {
      console.error('Lỗi upload logo:', error);
      toast.error('Không thể kết nối đến máy chủ để tải ảnh.', { id: toastId });
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };
  
  const [formData, setFormData] = useState({
    site_title: 'Chatbot YHCT Diamond',
    description: 'Hệ thống tra cứu vị thuốc và bài thuốc Y học cổ truyền dựa trên Đồ thị tri thức',
    keywords: 'YHCT, chatbot, AI, đồ thị tri thức, đông y',
    site_logo: '',
  });

  useEffect(() => {
    const fetchSeoSettings = async () => {
      try {
        const token = localStorage.getItem('access_token');
        const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
        const res = await fetch(`${API_URL}/admin/settings`, {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        if (res.ok) {
          const data = await res.json();
          setFormData({
            site_title: data.site_title || 'Chatbot YHCT Diamond',
            description: data.site_description || 'Hệ thống tra cứu vị thuốc và bài thuốc Y học cổ truyền dựa trên Đồ thị tri thức',
            keywords: data.site_keywords || 'YHCT, chatbot, AI, đồ thị tri thức, đông y',
            site_logo: data.site_logo || '',
          });
        }
      } catch (error) {
        console.error("Lỗi lấy cấu hình SEO:", error);
      }
    };
    fetchSeoSettings();
  }, []);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSyncSeo = async () => {
    setIsSyncing(true);
    const toastId = toast.loading('Đang khởi động tiến trình đồng bộ tri thức...');
    
    try {
      const token = localStorage.getItem('access_token');
      const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      
      const response = await fetch(`${API_URL}/admin/settings/update`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            seo: formData,
            last_sync_by: user?.email
        })
      });

      const data = await response.json();

      if (response.ok) {
        toast.success(data.message || 'Cập nhật cấu hình hệ thống thành công!', { id: toastId });
        await refreshSettings();
      } else {
        toast.error(data.detail || 'Huynh không có quyền thực hiện hành động này.', { id: toastId });
      }
    } catch (error) {
      toast.error('Máy chủ không phản hồi (Connection Refused)', { id: toastId });
    } finally {
      setIsSyncing(false);
    }
  };

  if (user?.role !== 'admin') {
    return (
      <div className="flex flex-col items-center justify-center min-h-[50vh] p-10 bg-white rounded-3xl border border-rose-100">
        <div className="w-16 h-16 bg-rose-50 rounded-full flex items-center justify-center mb-4">
          <AlertCircle size={32} className="text-rose-500" />
        </div>
        <h2 className="text-xl font-black text-slate-800">Truy cập bị từ chối</h2>
        <p className="text-slate-500 mt-2 text-center max-w-sm">
            Khu vực này chỉ dành cho Sếp tổng. Tài khoản của huynh ({user?.email}) chưa đủ thẩm quyền.
        </p>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto space-y-8 animate-fadeIn">
      {/* Header */}
      <div className="flex items-center gap-4 border-b border-gray-100 pb-6">
        <div className="p-4 bg-emerald-100 text-emerald-600 rounded-2xl shadow-inner">
          <Globe size={28} />
        </div>
        <div>
          <h1 className="text-2xl font-black text-slate-800 tracking-tight">Quản lý SEO & Tri thức</h1>
          <p className="text-slate-500 font-medium">Điều chỉnh Metadata vật lý và tần suất quét Đồ thị.</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Form nhập liệu */}
        <div className="lg:col-span-2 bg-white p-8 rounded-3xl shadow-sm border border-gray-100 space-y-6">
            <div className="space-y-2">
                <label className="text-xs font-bold text-slate-400 uppercase tracking-widest ml-1">Tiêu đề Website (Title Tag)</label>
                <input 
                    type="text" name="site_title" value={formData.site_title} onChange={handleChange}
                    className="w-full p-4 rounded-2xl bg-gray-50 border border-gray-100 focus:border-emerald-500 focus:bg-white outline-none transition-all font-semibold text-slate-700 shadow-inner"
                    placeholder="Ví dụ: Chatbot YHCT Diamond..."
                />
            </div>

            <div className="space-y-2">
                <label className="text-xs font-bold text-slate-400 uppercase tracking-widest ml-1">Đường dẫn ảnh Logo (Logo Image URL)</label>
                <div className="flex gap-3">
                    <input 
                        type="text" name="site_logo" value={formData.site_logo} onChange={handleChange}
                        className="flex-1 p-4 rounded-2xl bg-gray-50 border border-gray-100 focus:border-emerald-500 focus:bg-white outline-none transition-all font-mono text-xs text-slate-650 shadow-inner"
                        placeholder="Ví dụ: https://example.com/logo.png hoặc /assets/logo.svg (để trống sẽ dùng mặc định)"
                    />
                    <input 
                        type="file" 
                        ref={fileInputRef} 
                        accept="image/*" 
                        className="hidden" 
                        onChange={handleLogoUpload} 
                    />
                    <button
                        type="button"
                        onClick={() => fileInputRef.current?.click()}
                        disabled={isUploading}
                        className="flex items-center gap-2 px-5 bg-slate-100 hover:bg-slate-200 disabled:bg-slate-50 text-slate-700 font-bold rounded-2xl transition-all border border-slate-200 hover:border-slate-300 text-xs shrink-0 cursor-pointer"
                    >
                        {isUploading ? (
                            <Loader2 className="w-4 h-4 animate-spin text-slate-500" />
                        ) : (
                            <Upload className="w-4 h-4 text-slate-500" />
                        )}
                        <span>Chọn ảnh</span>
                    </button>
                </div>
                {formData.site_logo && (
                    <div className="mt-2 flex items-center gap-3 p-3 rounded-2xl bg-slate-50 border border-slate-100 max-w-max animate-fadeIn">
                        <div className="w-12 h-12 bg-white rounded-xl border border-gray-100 flex items-center justify-center overflow-hidden p-1 shadow-sm">
                            <img src={formData.site_logo} alt="Site Logo Preview" className="max-w-full max-h-full object-contain" />
                        </div>
                        <div>
                            <p className="text-xs font-bold text-slate-700">Xem trước Logo</p>
                            <button 
                                type="button" 
                                onClick={() => setFormData(prev => ({ ...prev, site_logo: '' }))}
                                className="text-[10px] text-rose-500 font-bold hover:underline mt-0.5 block cursor-pointer"
                            >
                                Xóa logo
                            </button>
                        </div>
                    </div>
                )}
            </div>

            <div className="space-y-2">
                <label className="text-xs font-bold text-slate-400 uppercase tracking-widest ml-1">Mô tả hệ thống (Meta Description)</label>
                <textarea 
                    name="description" value={formData.description} onChange={handleChange} rows={4}
                    className="w-full p-4 rounded-2xl bg-gray-50 border border-gray-100 focus:border-emerald-500 focus:bg-white outline-none transition-all text-sm text-slate-650 shadow-inner leading-relaxed"
                    placeholder="Mô tả hiển thị trên Google..."
                />
            </div>

            <div className="space-y-2">
                <label className="text-xs font-bold text-slate-400 uppercase tracking-widest ml-1">Từ khóa SEO (Keywords)</label>
                <input 
                    type="text" name="keywords" value={formData.keywords} onChange={handleChange}
                    className="w-full p-4 rounded-2xl bg-gray-50 border border-gray-100 focus:border-emerald-500 focus:bg-white outline-none transition-all font-medium text-slate-650 shadow-inner"
                    placeholder="yhct, graphrag, ai..."
                />
            </div>

            <button 
                onClick={handleSyncSeo} disabled={isSyncing}
                className="flex items-center justify-center gap-3 w-full p-4 bg-emerald-600 hover:bg-emerald-700 disabled:bg-slate-300 text-white font-black rounded-2xl transition-all shadow-md shadow-emerald-200 uppercase tracking-widest text-sm cursor-pointer"
            >
                {isSyncing ? <Loader2 className="w-5 h-5 animate-spin" /> : <Save size={20} />}
                <span>{isSyncing ? 'Đang đẩy dữ liệu...' : 'Lưu cấu hình SEO'}</span>
            </button>
        </div>

        {/* Cột thông tin bổ sung */}
        <div className="space-y-6">
            <div className="bg-emerald-900 p-6 rounded-3xl text-white shadow-xl relative overflow-hidden">
                <RefreshCcw className="absolute -right-4 -bottom-4 w-24 h-24 opacity-10" />
                <h3 className="font-bold mb-2 flex items-center gap-2">
                    <RefreshCcw size={16} /> Đồng bộ Graph
                </h3>
                <p className="text-xs text-emerald-100/80 leading-relaxed">
                    Mọi thay đổi về SEO và Logo sẽ được cập nhật trực tiếp vào cơ sở dữ liệu. Tất cả các trang hiển thị sẽ ngay lập tức được cập nhật giao diện mà không cần tải lại trang.
                </p>
            </div>

            <div className="bg-white p-6 rounded-3xl border border-gray-100 shadow-sm flex items-start gap-4">
                <div className="p-2 bg-amber-100 text-amber-600 rounded-lg">
                    <AlertCircle size={20} />
                </div>
                <div>
                    <p className="text-sm font-bold text-slate-800">Cấu hình Logo</p>
                    <p className="text-[11px] text-slate-400 mt-1 leading-relaxed">
                        Đường dẫn ảnh Logo có thể là địa chỉ URL bên ngoài (như CDN/Google Drive) hoặc đường dẫn tương đối trong thư mục public của Frontend.
                    </p>
                </div>
            </div>
        </div>
      </div>
    </div>
  );
};

export default SeoManager;