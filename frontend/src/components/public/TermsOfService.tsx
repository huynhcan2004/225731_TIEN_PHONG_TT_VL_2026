import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import PublicDocLayout from './PublicDocLayout';
import { useAuth } from '../../context/AuthContext';
import { useLanguageTheme } from '../../context/LanguageThemeContext';
import { defaultDocsEn } from '../../data/defaultDocsEn';
import { FileText, Edit2, X, Save, Loader2 } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import toast from 'react-hot-toast';

const TermsOfService: React.FC = () => {
  const { user } = useAuth();
  const [content, setContent] = useState('');
  const [loading, setLoading] = useState(true);
  const [isEditing, setIsEditing] = useState(false);
  const [editContent, setEditContent] = useState('');
  const [saving, setSaving] = useState(false);

  const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

  useEffect(() => {
    fetchDoc();
  }, []);

  const { language, t } = useLanguageTheme();

  const fetchDoc = async () => {
    try {
      const res = await fetch(`${API_URL}/docs/terms-of-service`);
      if (res.ok) {
        const data = await res.json();
        setContent(data.content);
      }
    } catch (error) {
      console.error('Lỗi lấy tài liệu:', error);
      toast.error(language === 'vi' ? 'Không thể lấy nội dung điều khoản sử dụng' : 'Cannot retrieve terms of service content');
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
      const res = await fetch(`${API_URL}/api/admin/docs/terms-of-service`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ content: editContent })
      });

      if (res.ok) {
        setContent(editContent);
        toast.success(language === 'vi' ? 'Lưu điều khoản sử dụng thành công!' : 'Terms of service saved successfully!');
        setIsEditing(false);
      } else {
        const data = await res.json();
        toast.error(data.detail || (language === 'vi' ? 'Lỗi khi lưu điều khoản' : 'Error saving terms of service'));
      }
    } catch (error) {
      console.error('Lỗi lưu tài liệu:', error);
      toast.error(language === 'vi' ? 'Lỗi hệ thống khi lưu tài liệu' : 'System error while saving document');
    } finally {
      setSaving(false);
    }
  };

  const markdownComponents = {
    a: ({ href, children, ...props }: any) => {
      const isInternal = href?.startsWith('/');
      if (isInternal) {
        return (
          <Link to={href} className="text-[#2c4a3e] hover:text-[#1f352c] font-semibold underline" {...props}>
            {children}
          </Link>
        );
      }
      return (
        <a href={href} target="_blank" rel="noopener noreferrer" className="text-[#2c4a3e] hover:text-[#1f352c] font-semibold underline" {...props}>
          {children}
        </a>
      );
    }
  };

  const displayContent = (language === 'en' && (!content || content.trim().startsWith('# Điều khoản sử dụng')))
    ? defaultDocsEn['terms-of-service']
    : content;

  return (
    <PublicDocLayout>
      <div className="prose prose-slate max-w-none flex-1 flex flex-col">
        {loading ? (
          <div className="flex-1 flex flex-col items-center justify-center py-20 text-[#2c4a3e]">
            <Loader2 className="w-8 h-8 animate-spin mb-2" />
            <p className="text-sm font-bold">{t('policyLoading')}</p>
          </div>
        ) : (
          <>
            {/* Control Bar (Only for Admin) */}
            {user?.role === 'admin' && (
              <div className="flex justify-end mb-4 no-prose">
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
                        <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      ) : (
                        <Save className="w-3.5 h-3.5" />
                      )}
                      {t('policySaveBtn')}
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

            {isEditing ? (
              <div className="flex-1 flex flex-col gap-4 no-prose">
                <div className="flex items-center gap-2 mb-1">
                  <FileText className="w-5 h-5 text-[#2c4a3e]" />
                  <span className="text-slate-800 font-black text-sm">{t('policyEditingTitle')}</span>
                </div>
                <textarea
                  value={editContent}
                  onChange={(e) => setEditContent(e.target.value)}
                  className="flex-1 min-h-[500px] w-full p-6 bg-slate-50 border border-slate-200 focus:border-[#2c4a3e] focus:bg-white rounded-2xl outline-none text-sm font-mono text-slate-800 leading-relaxed shadow-inner resize-y"
                  placeholder="# Title..."
                />
              </div>
            ) : (
              <div className="prose prose-slate max-w-none prose-headings:text-slate-800 prose-p:text-slate-650 prose-li:text-slate-650 prose-strong:text-slate-800">
                <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
                  {displayContent}
                </ReactMarkdown>
              </div>
            )}
          </>
        )}
      </div>
    </PublicDocLayout>
  );
};

export default TermsOfService;
