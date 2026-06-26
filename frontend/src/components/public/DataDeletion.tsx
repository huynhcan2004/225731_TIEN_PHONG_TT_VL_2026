import React, { useState, useEffect } from 'react';
import PublicDocLayout from './PublicDocLayout';
import { useAuth } from '../../context/AuthContext';
import { useSiteSettings } from '../../context/SiteSettingsContext';
import { useLanguageTheme } from '../../context/LanguageThemeContext';
import { defaultDocsEn } from '../../data/defaultDocsEn';
import { Trash2, AlertCircle, Mail, LogIn, ShieldAlert, CheckCircle, RefreshCw, Edit2, Save, X } from 'lucide-react';
import toast from 'react-hot-toast';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

const DataDeletion: React.FC = () => {
  const { user, logout } = useAuth();
  const { siteTitle } = useSiteSettings();
  const { language, t } = useLanguageTheme();
  const [content, setContent] = useState('');
  const [loading, setLoading] = useState(true);
  const [isEditing, setIsEditing] = useState(false);
  const [editContent, setEditContent] = useState('');
  const [saving, setSaving] = useState(false);
  const [supportEmail, setSupportEmail] = useState('support@yhct-diamond.vn');

  const [isDeleting, setIsDeleting] = useState(false);
  const [showConfirmModal, setShowConfirmModal] = useState(false);
  const [confirmText, setConfirmText] = useState('');
  const [successDeleted, setSuccessDeleted] = useState(false);
  const [isPendingApproval, setIsPendingApproval] = useState(false);

  const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

  useEffect(() => {
    fetchDoc();
    fetchSupportEmail();
  }, []);

  const fetchSupportEmail = async () => {
    try {
      const res = await fetch(`${API_URL}/docs/contact`);
      if (res.ok) {
        const data = await res.json();
        if (data?.content?.email) {
          setSupportEmail(data.content.email);
        }
      }
    } catch (e) {
      console.error(e);
    }
  };

  const fetchDoc = async () => {
    try {
      const res = await fetch(`${API_URL}/docs/data-deletion`);
      if (res.ok) {
        const data = await res.json();
        setContent(data.content);
      }
    } catch (error) {
      console.error('Lỗi lấy tài liệu:', error);
      toast.error(language === 'vi' ? 'Không thể lấy nội dung chính sách xóa dữ liệu' : 'Cannot retrieve data deletion policy');
    } finally {
      setLoading(false);
    }
  };

  const handleStartEdit = () => {
    setEditContent(content);
    setIsEditing(true);
  };

  const handleSave = async () => {
    setSaving(true);
    const token = localStorage.getItem('access_token');
    try {
      const res = await fetch(`${API_URL}/api/admin/docs/data-deletion`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ content: editContent })
      });

      if (res.ok) {
        setContent(editContent);
        toast.success(language === 'vi' ? 'Lưu chính sách xóa dữ liệu thành công!' : 'Data deletion policy saved successfully!');
        setIsEditing(false);
      } else {
        const data = await res.json();
        toast.error(data.detail || (language === 'vi' ? 'Lỗi khi lưu chính sách' : 'Error saving policy'));
      }
    } catch (error) {
      console.error('Lỗi lưu tài liệu:', error);
      toast.error(language === 'vi' ? 'Lỗi hệ thống khi lưu tài liệu' : 'System error while saving document');
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteAccount = async () => {
    if (confirmText.trim().toUpperCase() !== 'DELETE') {
      toast.error(t('delConfirmError'));
      return;
    }

    setIsDeleting(true);
    const token = localStorage.getItem('access_token');
    
    try {
      const res = await fetch(`${API_URL}/auth/me`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (res.ok) {
        const data = await res.json();
        if (data.status === 'pending') {
          toast.success(language === 'vi' ? "Đã gửi yêu cầu xóa tài khoản tới Admin!" : "Sent account deletion request to Admin!");
          setIsPendingApproval(true);
          setSuccessDeleted(true);
          setShowConfirmModal(false);
          setTimeout(() => {
            logout(false);
          }, 6000);
        } else {
          toast.success(language === 'vi' ? "Xóa tài khoản thành công!" : "Account deleted successfully!");
          setSuccessDeleted(true);
          setShowConfirmModal(false);
          setTimeout(() => {
            logout(false);
          }, 3000);
        }
      } else {
        const errData = await res.json();
        toast.error(errData.detail || (language === 'vi' ? "Đã xảy ra lỗi khi xóa tài khoản." : "An error occurred while deleting account."));
        setIsDeleting(false);
      }
    } catch (error) {
      console.error("Lỗi xóa tài khoản:", error);
      toast.error(language === 'vi' ? "Không thể kết nối đến máy chủ." : "Cannot connect to server.");
      setIsDeleting(false);
    }
  };

  const displayContent = (language === 'en' && (!content || content.trim().startsWith('# Yêu cầu xóa dữ liệu')))
    ? defaultDocsEn['data-deletion']
    : content;

  return (
    <PublicDocLayout>
      <div className="prose prose-slate max-w-none flex-1 flex flex-col justify-between">
        <div>
          {/* Title and Edit Button */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between border-b border-slate-100 pb-6 mb-8 gap-4">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-2xl bg-red-50 text-red-600 flex items-center justify-center shrink-0">
                <Trash2 className="w-6 h-6" />
              </div>
              <div>
                <h1 className="text-3xl font-extrabold text-slate-800 tracking-tight m-0">{t('delTitle')}</h1>
                <p className="text-slate-400 text-sm m-0 mt-1">{t('delSub')}</p>
              </div>
            </div>

            {/* Admin actions */}
            {user?.role === 'admin' && !successDeleted && !loading && (
              <div className="no-prose">
                {isEditing ? (
                  <div className="flex gap-2">
                    <button
                      onClick={() => setIsEditing(false)}
                      className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 font-bold rounded-xl text-xs flex items-center gap-1.5 transition-all cursor-pointer"
                    >
                      <X className="w-3.5 h-3.5" />
                      {t('policyCancelBtn')}
                    </button>
                    <button
                      onClick={handleSave}
                      disabled={saving}
                      className="px-4 py-2 bg-[#2c4a3e] hover:bg-[#1f352c] text-white font-bold rounded-xl text-xs flex items-center gap-1.5 shadow-sm transition-all cursor-pointer disabled:opacity-50"
                    >
                      {saving ? (
                        <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                      ) : (
                        <Save className="w-3.5 h-3.5" />
                      )}
                      {t('delSavePolicyBtn')}
                    </button>
                  </div>
                ) : (
                  <button
                    onClick={handleStartEdit}
                    className="px-4 py-2 border border-slate-200 hover:border-slate-350 bg-white hover:bg-slate-50 text-slate-700 font-bold rounded-xl text-xs flex items-center gap-1.5 shadow-sm transition-all cursor-pointer"
                  >
                    <Edit2 className="w-3.5 h-3.5 text-[#2c4a3e]" />
                    {t('policyEditBtn')}
                  </button>
                )}
              </div>
            )}
          </div>

          {loading ? (
            <div className="flex flex-col items-center justify-center py-20 text-[#2c4a3e] no-prose">
              <RefreshCw className="w-8 h-8 animate-spin mb-2" />
              <p className="text-sm font-bold">{t('delLoading')}</p>
            </div>
          ) : successDeleted ? (
            <div className="text-center py-12 bg-emerald-50/50 border border-emerald-100 rounded-3xl p-8 max-w-lg mx-auto no-prose">
              {isPendingApproval ? (
                <>
                  <CheckCircle className="w-16 h-16 text-amber-500 mx-auto mb-4 animate-pulse" />
                  <h2 className="text-2xl font-black text-slate-800 m-0 mb-2">{t('delSuccessPendingTitle')}</h2>
                  <p className="text-slate-600 text-sm leading-relaxed m-0">
                    {t('delSuccessPendingDesc')}
                  </p>
                </>
              ) : (
                <>
                  <CheckCircle className="w-16 h-16 text-emerald-500 mx-auto mb-4 animate-bounce" />
                  <h2 className="text-2xl font-black text-slate-800 m-0 mb-2">{t('delSuccessTitle')}</h2>
                  <p className="text-slate-600 text-sm leading-relaxed m-0">
                    {t('delSuccessDesc').replace('{siteTitle}', siteTitle)}
                  </p>
                </>
              )}
            </div>
          ) : (
            <>
              {/* Policy Explanation */}
              {isEditing ? (
                <div className="mb-8 no-prose">
                  <div className="flex items-center gap-2 mb-2 text-slate-800 font-bold text-sm">
                    <ShieldAlert className="w-5 h-5 text-red-500" />
                    <span>{t('delEditTitle')}</span>
                  </div>
                  <textarea
                    value={editContent}
                    onChange={(e) => setEditContent(e.target.value)}
                    className="w-full min-h-[300px] p-6 bg-slate-50 border border-slate-200 focus:border-[#2c4a3e] focus:bg-white rounded-2xl outline-none text-sm font-mono text-slate-800 leading-relaxed shadow-inner resize-y"
                    placeholder={t('delEditPlaceholder')}
                  />
                </div>
              ) : (
                <div className="bg-slate-50 border border-slate-100 rounded-3xl p-6 sm:p-8 mb-8 no-prose flex gap-4 items-start shadow-sm border-l-4 border-l-red-500">
                  <ShieldAlert className="w-8 h-8 text-red-500 shrink-0 mt-1" />
                  <div className="flex-1 min-w-0 prose prose-sm prose-slate max-w-none prose-headings:text-slate-800 prose-p:text-slate-650 prose-li:text-slate-650">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                      {displayContent}
                    </ReactMarkdown>
                  </div>
                </div>
              )}

              {/* Action Section based on Auth status */}
              <div className="no-prose">
                {user ? (
                  /* LOGGED IN USER */
                  <div className="border border-red-150 bg-red-50/10 rounded-3xl p-6 sm:p-8 text-center max-w-xl mx-auto">
                    <div className="flex justify-center mb-4">
                      <img 
                        src={user.avatar_url || 'https://www.gravatar.com/avatar?d=mp'} 
                        alt={user.username} 
                        className="w-16 h-16 rounded-full ring-4 ring-red-100 shadow-md"
                      />
                    </div>
                    <h3 className="text-slate-800 font-black text-lg m-0">{user.username || t('delUserTitle')}</h3>
                    <p className="text-slate-500 text-xs m-0 mt-0.5">{user.email}</p>
                    
                    {user.token_balance !== undefined && (
                      <div className="mt-4 inline-block bg-amber-50 text-amber-800 border border-amber-200/50 rounded-xl px-4 py-1.5 text-xs font-bold">
                        {t('delTokenBalanceLabel').replace('{balance}', user.token_balance.toLocaleString())}
                      </div>
                    )}

                    <div className="mt-8 border-t border-red-100/50 pt-6">
                      <p className="text-slate-500 text-xs mb-4">
                        {t('delUserDesc')}
                      </p>
                      <button 
                        onClick={() => setShowConfirmModal(true)}
                        className="bg-red-600 hover:bg-red-700 text-white font-bold px-6 py-3.5 rounded-2xl shadow-md shadow-red-900/10 hover:shadow-lg transition-all duration-200 active:scale-95 text-sm cursor-pointer"
                      >
                        {t('delSubmitBtn')}
                      </button>
                    </div>
                  </div>
                ) : (
                  /* ANONYMOUS USER */
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-8">
                    {/* Option 1: Login to delete self */}
                    <div className="border border-slate-150 rounded-3xl p-6 flex flex-col justify-between hover:shadow-md transition-all">
                      <div>
                        <div className="w-10 h-10 rounded-xl bg-emerald-50 text-[#2c4a3e] flex items-center justify-center mb-4">
                          <LogIn className="w-5 h-5" />
                        </div>
                        <h3 className="text-slate-800 font-bold text-base m-0 mb-2">{t('delLoginTitle')}</h3>
                        <p className="text-slate-500 text-xs leading-relaxed m-0">
                          {t('delLoginDesc')}
                        </p>
                      </div>
                      <a 
                        href="/login" 
                        className="mt-6 bg-[#2c4a3e] hover:bg-[#1f352c] text-white font-bold text-xs text-center py-3 rounded-xl transition-all block"
                      >
                        {t('delLoginBtn')}
                      </a>
                    </div>

                    {/* Option 2: Send Support Email */}
                    <div className="border border-slate-150 rounded-3xl p-6 flex flex-col justify-between hover:shadow-md transition-all">
                      <div>
                        <div className="w-10 h-10 rounded-xl bg-slate-100 text-slate-600 flex items-center justify-center mb-4">
                          <Mail className="w-5 h-5" />
                        </div>
                        <h3 className="text-slate-800 font-bold text-base m-0 mb-2">{t('delMailTitle')}</h3>
                        <p className="text-slate-500 text-xs leading-relaxed m-0">
                          {t('delMailDesc')}
                        </p>
                      </div>
                      <a 
                        href={`mailto:${supportEmail}?subject=Yêu cầu xóa tài khoản tại ${siteTitle}`} 
                        className="mt-6 bg-slate-100 hover:bg-slate-200 text-slate-700 font-bold text-xs text-center py-3 rounded-xl transition-all block"
                      >
                        {t('delMailBtn')}{supportEmail}
                      </a>
                    </div>
                  </div>
                )}
              </div>
            </>
          )}
        </div>

        {/* Confirmation Modal */}
        {showConfirmModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm no-prose">
            <div className="bg-white rounded-[2rem] max-w-md w-full p-8 shadow-2xl border border-slate-100 animate-in fade-in zoom-in-95 duration-200">
              <div className="w-12 h-12 bg-red-50 text-red-600 rounded-full flex items-center justify-center mb-4">
                <AlertCircle className="w-6 h-6" />
              </div>
              <h3 className="text-xl font-black text-slate-800 m-0 mb-2">{t('delConfirmModalTitle')}</h3>
              <p className="text-slate-500 text-xs leading-relaxed m-0 mb-6">
                {t('delConfirmModalDesc').replace('{siteTitle}', siteTitle)}
              </p>
              
              <div className="mb-6">
                <label className="block text-slate-700 text-xs font-bold mb-2">
                  {t('delConfirmInputLabel')}
                </label>
                <input 
                  type="text" 
                  value={confirmText}
                  onChange={(e) => setConfirmText(e.target.value.toUpperCase())}
                  placeholder={t('delConfirmInputPlaceholder')}
                  className="w-full px-4 py-3 border-2 border-slate-100 hover:border-red-100 focus:border-red-500 rounded-xl focus:outline-none transition-colors text-sm font-bold text-center tracking-wider text-red-600 uppercase"
                />
              </div>

              <div className="flex gap-3">
                <button
                  onClick={() => {
                    setShowConfirmModal(false);
                    setConfirmText('');
                  }}
                  className="flex-1 px-4 py-3 bg-slate-100 hover:bg-slate-200 text-slate-700 font-bold rounded-xl text-xs transition-colors cursor-pointer"
                >
                  {t('policyCancelBtn')}
                </button>
                <button
                  onClick={handleDeleteAccount}
                  disabled={isDeleting}
                  className="flex-1 px-4 py-3 bg-red-600 hover:bg-red-700 text-white font-bold rounded-xl text-xs transition-colors flex items-center justify-center gap-1.5 shadow-md shadow-red-900/10 cursor-pointer"
                >
                  {isDeleting ? (
                    <>
                      <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                      {t('delProcessingBtn')}
                    </>
                  ) : (
                    t('delConfirmBtn')
                  )}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </PublicDocLayout>
  );
};

export default DataDeletion;
