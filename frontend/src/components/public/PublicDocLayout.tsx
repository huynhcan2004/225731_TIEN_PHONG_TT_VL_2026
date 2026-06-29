import React, { useState, useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { useSiteSettings } from '../../context/SiteSettingsContext';
import { useLanguageTheme } from '../../context/LanguageThemeContext';
import { 
  Shield, 
  FileText, 
  Trash2, 
  HelpCircle, 
  Mail, 
  ArrowLeft, 
  Leaf, 
  ChevronRight,
  Edit,
  X,
  Save,
  Loader2
} from 'lucide-react';
import toast from 'react-hot-toast';

interface NavItem {
  path: string;
  label: string;
  icon: string;
  description: string;
}

interface PublicDocLayoutProps {
  children: React.ReactNode;
}

const iconMap: Record<string, React.ComponentType<any>> = {
  Shield: Shield,
  FileText: FileText,
  Trash2: Trash2,
  HelpCircle: HelpCircle,
  Mail: Mail
};

const defaultNavItems: NavItem[] = [
  {
    path: '/privacy-policy',
    label: 'Chính sách bảo mật',
    icon: 'Shield',
    description: 'Quyền riêng tư & Thu thập dữ liệu'
  },
  {
    path: '/terms-of-service',
    label: 'Điều khoản sử dụng',
    icon: 'FileText',
    description: 'Quy định sử dụng & Chính sách AI'
  },
  {
    path: '/data-deletion',
    label: 'Yêu cầu xóa dữ liệu',
    icon: 'Trash2',
    description: 'Xóa tài khoản & Dữ liệu cá nhân'
  },
  {
    path: '/support',
    label: 'Hỗ trợ & FAQ',
    icon: 'HelpCircle',
    description: 'Câu hỏi thường gặp & Trợ giúp'
  },
  {
    path: '/contact',
    label: 'Liên hệ',
    icon: 'Mail',
    description: 'Thông tin liên hệ nhà phát triển'
  }
];

const PublicDocLayout: React.FC<PublicDocLayoutProps> = ({ children }) => {
  const { user } = useAuth();
  const { siteTitle, siteLogo } = useSiteSettings();
  const location = useLocation();
  const [navItems, setNavItems] = useState<NavItem[]>(defaultNavItems);
  const [loading, setLoading] = useState(true);
  const [isEditing, setIsEditing] = useState(false);
  const [editItems, setEditItems] = useState<NavItem[]>([]);
  const [saving, setSaving] = useState(false);

  const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

  useEffect(() => {
    fetchSidebar();
  }, []);

  useEffect(() => {
    window.scrollTo(0, 0);
  }, [location.pathname]);

  const fetchSidebar = async () => {
    try {
      const res = await fetch(`${API_URL}/docs/sidebar`);
      if (res.ok) {
        const data = await res.json();
        if (data && data.content) {
          setNavItems(data.content);
        }
      }
    } catch (error) {
      console.error('Lỗi lấy sidebar:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleOpenEdit = () => {
    setEditItems(JSON.parse(JSON.stringify(navItems)));
    setIsEditing(true);
  };

  const handleItemChange = (index: number, field: 'label' | 'description', value: string) => {
    const updated = [...editItems];
    updated[index][field] = value;
    setEditItems(updated);
  };

  const handleSaveSidebar = async () => {
    setSaving(true);
    const token = localStorage.getItem('access_token');
    try {
      const res = await fetch(`${API_URL}/admin/docs/sidebar`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ content: editItems })
      });

      if (res.ok) {
        setNavItems(editItems);
        toast.success('Cập nhật danh mục tài liệu thành công!');
        setIsEditing(false);
      } else {
        const data = await res.json();
        toast.error(data.detail || 'Lỗi khi cập nhật danh mục tài liệu');
      }
    } catch (error) {
      console.error('Lỗi lưu sidebar:', error);
      toast.error('Lỗi hệ thống khi cập nhật danh mục');
    } finally {
      setSaving(false);
    }
  };

  const { language, setLanguage, t } = useLanguageTheme();

  const getTranslatedItem = (item: NavItem) => {
    if (language === 'vi') return item;
    const translationsMap: Record<string, { label: string, description: string }> = {
      '/privacy-policy': { label: 'Privacy Policy', description: 'Privacy & Data Collection' },
      '/terms-of-service': { label: 'Terms of Service', description: 'Rules & AI Policies' },
      '/data-deletion': { label: 'Data Deletion Request', description: 'Account & Data Removal' },
      '/support': { label: 'Support & FAQ', description: 'FAQs & Help' },
      '/contact': { label: 'Contact Us', description: 'Developer Contact' }
    };
    const mapped = translationsMap[item.path];
    return mapped ? { ...item, label: mapped.label, description: mapped.description } : item;
  };

  const renderLogo = (className = "w-5.5 h-5.5") => {
    if (siteLogo) {
      return <img src={siteLogo} alt="Logo" className={className} />;
    }
    return <Leaf className={`text-[#a3c9a8] ${className}`} />;
  };

  return (
    <div className="min-h-screen bg-slate-50 text-slate-800 font-sans flex flex-col">
      {/* Premium Header */}
      <header className="sticky top-0 z-40 bg-white/80 backdrop-blur-md border-b border-slate-100 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-3 hover:opacity-90 transition-opacity">
            <div className="w-10 h-10 bg-[#2c4a3e] rounded-xl flex items-center justify-center shadow-md shadow-emerald-900/10">
              {renderLogo("w-5.5 h-5.5")}
            </div>
            <div>
              <span className="font-black text-lg text-slate-800 tracking-tight">
                {siteTitle}
              </span>
              <span className="hidden sm:inline-block ml-2 px-2 py-0.5 bg-emerald-50 text-emerald-700 text-[10px] font-bold rounded-full border border-emerald-100">
                {t('policyBadge')}
              </span>
            </div>
          </Link>
          
          <div className="flex items-center gap-3">
            {/* Language Toggle Button */}
            <button
              onClick={() => setLanguage(language === 'vi' ? 'en' : 'vi')}
              className="flex items-center gap-1.5 px-3 py-2 text-xs font-bold text-slate-600 hover:text-[#2c4a3e] bg-slate-100 hover:bg-emerald-50 rounded-xl transition-all cursor-pointer"
            >
              <span>{language === 'vi' ? '🇻🇳 VI' : '🇬🇧 EN'}</span>
            </button>
            
            <Link 
              to={user ? "/chat" : "/"} 
              className="flex items-center gap-2 px-4 py-2 text-sm font-semibold text-slate-600 hover:text-[#2c4a3e] bg-slate-100 hover:bg-emerald-50 rounded-xl transition-all duration-200"
            >
              <ArrowLeft className="w-4 h-4" />
              <span>{t('policyBackBtn')}{user ? t('policyChatText') : t('policyHomeText')}</span>
            </Link>
          </div>
        </div>
      </header>

      {/* Main Content Area with sidebar layout */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 flex flex-col lg:flex-row gap-8">
        {/* Navigation Sidebar */}
        <aside className="w-full lg:w-80 shrink-0">
          <div className="sticky top-24 bg-white rounded-3xl p-4 border border-slate-100 shadow-sm flex flex-col gap-1.5">
            <div className="flex items-center justify-between px-3 py-2">
              <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider">{t('policySidebarTitle')}</h3>
              {user?.role === 'admin' && (
                <button 
                  onClick={handleOpenEdit}
                  className="text-xs font-bold text-[#2c4a3e] hover:text-[#1f352c] transition-colors flex items-center gap-1 cursor-pointer"
                >
                  <Edit className="w-3.5 h-3.5" />
                  {t('policySidebarEdit')}
                </button>
              )}
            </div>

            {loading ? (
              <div className="flex items-center justify-center py-8 text-[#2c4a3e]">
                <Loader2 className="w-6 h-6 animate-spin" />
              </div>
            ) : (
              navItems.map((item) => {
                const Icon = iconMap[item.icon] || FileText;
                const isActive = location.pathname === item.path;
                const displayItem = getTranslatedItem(item);
                return (
                  <Link
                    key={item.path}
                    to={item.path}
                    className={`group flex items-center gap-3 p-3 rounded-2xl transition-all duration-200 border ${
                      isActive 
                        ? 'bg-[#2c4a3e]/5 border-emerald-100 text-[#2c4a3e]' 
                        : 'bg-transparent border-transparent text-slate-600 hover:bg-slate-50 hover:text-slate-900'
                    }`}
                  >
                    <div className={`p-2 rounded-xl transition-all duration-200 ${
                      isActive ? 'bg-[#2c4a3e] text-[#a3c9a8]' : 'bg-slate-100 text-slate-400 group-hover:bg-slate-200 group-hover:text-slate-600'
                    }`}>
                      <Icon className="w-5 h-5" />
                    </div>
                    <div className="flex-1 text-left">
                      <p className="font-bold text-sm leading-tight">{displayItem.label}</p>
                      <p className="text-[11px] text-slate-400 mt-0.5 font-medium leading-none">{displayItem.description}</p>
                    </div>
                    <ChevronRight className={`w-4 h-4 transition-transform duration-200 ${
                      isActive ? 'translate-x-0.5 text-[#2c4a3e]' : 'opacity-0 -translate-x-1 group-hover:opacity-100 group-hover:translate-x-0 text-slate-400'
                    }`} />
                  </Link>
                );
              })
            )}
          </div>
        </aside>

        {/* Content Box */}
        <section className="flex-1 bg-white rounded-[2rem] border border-slate-100 shadow-sm p-6 sm:p-10 min-h-[60vh] flex flex-col relative">
          {children}
        </section>
      </main>

      {/* Sidebar Edit Modal */}
      {isEditing && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm">
          <div className="bg-white rounded-[2rem] max-w-lg w-full p-8 shadow-2xl border border-slate-100 animate-in fade-in zoom-in-95 duration-200 max-h-[85vh] overflow-y-auto">
            <div className="flex items-center justify-between border-b border-slate-100 pb-4 mb-6">
              <h3 className="text-lg font-black text-slate-800">{t('policySidebarEditModalTitle')}</h3>
              <button 
                onClick={() => setIsEditing(false)}
                className="p-1 rounded-lg hover:bg-slate-100 text-slate-400 hover:text-slate-650 transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-5">
              {editItems.map((item, index) => {
                const Icon = iconMap[item.icon] || FileText;
                return (
                  <div key={item.path} className="p-4 bg-slate-50 border border-slate-100 rounded-2xl space-y-3">
                    <div className="flex items-center gap-2 text-slate-700 font-bold text-xs">
                      <Icon className="w-4 h-4 text-[#2c4a3e]" />
                      <span>{item.path}</span>
                    </div>

                    <div>
                      <label className="block text-slate-500 text-[10px] font-bold uppercase mb-1">{t('policySidebarLabelPlaceholder')}</label>
                      <input 
                        type="text"
                        value={item.label}
                        onChange={(e) => handleItemChange(index, 'label', e.target.value)}
                        className="w-full px-3 py-2 border border-slate-200 focus:border-[#2c4a3e] rounded-xl focus:outline-none transition-colors text-xs font-semibold"
                      />
                    </div>

                    <div>
                      <label className="block text-slate-500 text-[10px] font-bold uppercase mb-1">{t('policySidebarDescPlaceholder')}</label>
                      <input 
                        type="text"
                        value={item.description}
                        onChange={(e) => handleItemChange(index, 'description', e.target.value)}
                        className="w-full px-3 py-2 border border-slate-200 focus:border-[#2c4a3e] rounded-xl focus:outline-none transition-colors text-xs"
                      />
                    </div>
                  </div>
                );
              })}
            </div>

            <div className="flex gap-3 mt-8 border-t border-slate-100 pt-6">
              <button
                onClick={() => setIsEditing(false)}
                className="flex-1 px-4 py-2.5 bg-slate-100 hover:bg-slate-200 text-slate-700 font-bold rounded-xl text-xs transition-colors cursor-pointer"
              >
                {t('policyCancelBtn')}
              </button>
              <button
                onClick={handleSaveSidebar}
                disabled={saving}
                className="flex-1 px-4 py-2.5 bg-[#2c4a3e] hover:bg-[#1f352c] text-white font-bold rounded-xl text-xs transition-colors flex items-center justify-center gap-1.5 shadow-md shadow-emerald-900/10 cursor-pointer disabled:opacity-50"
              >
                {saving ? (
                  <>
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    {t('policySavingBtn')}
                  </>
                ) : (
                  <>
                    <Save className="w-3.5 h-3.5" />
                    {t('policySaveBtn')}
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Elegant Footer */}
      <footer className="bg-slate-900 text-slate-400 py-8 border-t border-slate-800 mt-auto">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-4 text-center sm:text-left">
          <div>
            <p className="font-bold text-white text-sm">{siteTitle} {t('policyFooterTitle')}</p>
            <p className="text-xs text-slate-500 mt-1">{t('policyFooterSub')}</p>
          </div>
          <div className="text-xs text-slate-500">
            &copy; {new Date().getFullYear()} {siteTitle}. All rights reserved.
          </div>
        </div>
      </footer>
    </div>
  );
};

export default PublicDocLayout;
