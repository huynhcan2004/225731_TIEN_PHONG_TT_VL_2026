import React, { useState, useEffect } from 'react';
import PublicDocLayout from './PublicDocLayout';
import { useAuth } from '../../context/AuthContext';
import { useSiteSettings } from '../../context/SiteSettingsContext';
import { useLanguageTheme } from '../../context/LanguageThemeContext';
import { defaultDocsEn } from '../../data/defaultDocsEn';
import { Mail, MapPin, Globe, Github, Info, GraduationCap, Edit2, Save, X, RefreshCw, CheckCircle, Send } from 'lucide-react';
import toast from 'react-hot-toast';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface ContactInfo {
  description: string;
  email: string;
  unit: string;
  office: string;
  github: string;
  copyright: string;
}

const Contact: React.FC = () => {
  const { user } = useAuth();
  const { siteTitle } = useSiteSettings();
  const { language, t } = useLanguageTheme();
  const [contact, setContact] = useState<ContactInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [isEditing, setIsEditing] = useState(false);
  const [editFields, setEditFields] = useState<ContactInfo | null>(null);
  const [saving, setSaving] = useState(false);

  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [message, setMessage] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitSuccess, setSubmitSuccess] = useState(false);

  const handleFormSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !email.trim() || !message.trim()) {
      toast.error(language === 'vi' ? "Vui lòng điền đầy đủ các thông tin bắt buộc!" : "Please fill in all required fields!");
      return;
    }

    setIsSubmitting(true);
    try {
      const res = await fetch(`${API_URL}/support/submit`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          name,
          email,
          subject: 'Liên hệ từ trang Contact',
          message
        })
      });

      const data = await res.json();
      if (res.ok) {
        setSubmitSuccess(true);
        toast.success(data.message || (language === 'vi' ? "Đã gửi tin nhắn liên hệ thành công!" : "Contact message sent successfully!"));
        setName('');
        setEmail('');
        setMessage('');
      } else {
        toast.error(data.detail || (language === 'vi' ? "Gửi liên hệ thất bại." : "Failed to send message."));
      }
    } catch (error) {
      console.error("Lỗi gửi liên hệ:", error);
      toast.error(language === 'vi' ? "Không thể kết nối đến máy chủ." : "Could not connect to server.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

  useEffect(() => {
    fetchContact();
  }, []);

  const fetchContact = async () => {
    try {
      const res = await fetch(`${API_URL}/docs/contact`);
      if (res.ok) {
        const data = await res.json();
        setContact(data.content);
      }
    } catch (error) {
      console.error('Lỗi lấy thông tin liên hệ:', error);
      toast.error(language === 'vi' ? 'Không thể lấy thông tin liên hệ' : 'Cannot retrieve contact information');
    } finally {
      setLoading(false);
    }
  };

  const handleStartEdit = () => {
    setEditFields(JSON.parse(JSON.stringify(contact)));
    setIsEditing(true);
  };

  const handleSave = async () => {
    if (!editFields) return;
    
    // Simple validation
    if (!editFields.email.trim() || !editFields.unit.trim() || !editFields.office.trim()) {
      toast.error(language === 'vi' ? 'Vui lòng điền đầy đủ các thông tin bắt buộc (Email, Đơn vị, Văn phòng)!' : 'Please fill in all required fields (Email, Unit, Office)!');
      return;
    }

    setSaving(true);
    const token = localStorage.getItem('access_token');
    try {
      const res = await fetch(`${API_URL}/api/admin/docs/contact`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ content: editFields })
      });

      if (res.ok) {
        setContact(editFields);
        toast.success(language === 'vi' ? 'Lưu thông tin liên hệ thành công!' : 'Contact information saved successfully!');
        setIsEditing(false);
      } else {
        const data = await res.json();
        toast.error(data.detail || (language === 'vi' ? 'Lỗi khi lưu thông tin liên hệ' : 'Error saving contact information'));
      }
    } catch (error) {
      console.error('Lỗi lưu thông tin liên hệ:', error);
      toast.error(language === 'vi' ? 'Lỗi hệ thống khi lưu thông tin liên hệ' : 'System error while saving contact information');
    } finally {
      setSaving(false);
    }
  };

  const handleChange = (field: keyof ContactInfo, value: string) => {
    if (!editFields) return;
    setEditFields({ ...editFields, [field]: value });
  };

  // Fallback to English version if selected and using default content
  const displayContact = (language === 'en' && contact && (!contact.description || contact.description.includes('nhóm nghiên cứu trí tuệ nhân tạo') || contact.description.includes('trực quan hóa đồ thị') || contact.unit?.includes('Trường Đại học Công nghệ Thông tin')))
    ? defaultDocsEn['contact']
    : contact;

  return (
    <PublicDocLayout>
      <div className="prose prose-slate max-w-none flex-1 flex flex-col justify-between">
        <div>
          {/* Title and Edit Button */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between border-b border-slate-100 pb-6 mb-8 gap-4">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-2xl bg-emerald-50 text-[#2c4a3e] flex items-center justify-center shrink-0">
                <Mail className="w-6 h-6" />
              </div>
              <div>
                <h1 className="text-3xl font-extrabold text-slate-800 tracking-tight m-0">
                  {language === 'vi' ? 'Thông tin liên hệ' : 'Contact Information'}
                </h1>
                <p className="text-slate-400 text-sm m-0 mt-1">
                  {language === 'vi' 
                    ? `Kết nối với ban quản lý dự án ${siteTitle}` 
                    : `Connect with the ${siteTitle} project management`}
                </p>
              </div>
            </div>

            {/* Admin Actions */}
            {user?.role === 'admin' && !loading && (
              <div className="no-prose">
                {isEditing ? (
                  <div className="flex gap-2">
                    <button
                      onClick={() => setIsEditing(false)}
                      className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 font-bold rounded-xl text-xs flex items-center gap-1.5 transition-all cursor-pointer"
                    >
                      <X className="w-3.5 h-3.5" />
                      {t('cancel')}
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
                      {language === 'vi' ? 'Lưu thay đổi' : 'Save changes'}
                    </button>
                  </div>
                ) : (
                  <button
                    onClick={handleStartEdit}
                    className="px-4 py-2 border border-slate-200 hover:border-slate-350 bg-white hover:bg-slate-50 text-slate-700 font-bold rounded-xl text-xs flex items-center gap-1.5 shadow-sm transition-all cursor-pointer"
                  >
                    <Edit2 className="w-3.5 h-3.5 text-[#2c4a3e]" />
                    {language === 'vi' ? 'Chỉnh sửa liên hệ' : 'Edit Contact'}
                  </button>
                )}
              </div>
            )}
          </div>

          {loading || !displayContact ? (
            <div className="flex flex-col items-center justify-center py-20 text-[#2c4a3e] no-prose">
              <RefreshCw className="w-8 h-8 animate-spin mb-2" />
              <p className="text-sm font-bold">{t('policyLoading')}</p>
            </div>
          ) : isEditing && editFields ? (
            /* EDITING MODE FORM */
            <div className="space-y-6 no-prose">
              <div className="bg-slate-50 border border-slate-100 rounded-3xl p-6 space-y-4 shadow-inner">
                <h3 className="text-slate-800 font-black text-sm mb-2 flex items-center gap-1.5">
                  <Mail className="w-4 h-4 text-[#2c4a3e]" />
                  Chi tiết thông tin liên hệ
                </h3>
                
                <div>
                  <label className="block text-slate-500 text-[10px] font-bold uppercase mb-1">Mô tả dự án (Hỗ trợ Markdown)</label>
                  <textarea 
                    rows={4}
                    value={editFields.description}
                    onChange={(e) => handleChange('description', e.target.value)}
                    className="w-full px-3 py-2 border border-slate-200 focus:border-[#2c4a3e] rounded-xl focus:outline-none transition-colors text-xs leading-relaxed resize-y font-mono"
                    placeholder="Mô tả dự án..."
                  />
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-slate-500 text-[10px] font-bold uppercase mb-1">Địa chỉ Email</label>
                    <input 
                      type="email"
                      value={editFields.email}
                      onChange={(e) => handleChange('email', e.target.value)}
                      className="w-full px-3 py-2 border border-slate-200 focus:border-[#2c4a3e] rounded-xl focus:outline-none transition-colors text-xs font-semibold text-slate-800"
                      placeholder="support@example.com"
                    />
                  </div>

                  <div>
                    <label className="block text-slate-500 text-[10px] font-bold uppercase mb-1">Đơn vị chủ quản</label>
                    <input 
                      type="text"
                      value={editFields.unit}
                      onChange={(e) => handleChange('unit', e.target.value)}
                      className="w-full px-3 py-2 border border-slate-200 focus:border-[#2c4a3e] rounded-xl focus:outline-none transition-colors text-xs font-semibold text-slate-800"
                      placeholder="Trường Đại học..."
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-slate-500 text-[10px] font-bold uppercase mb-1">Địa chỉ văn phòng</label>
                  <input 
                    type="text"
                    value={editFields.office}
                    onChange={(e) => handleChange('office', e.target.value)}
                    className="w-full px-3 py-2 border border-slate-200 focus:border-[#2c4a3e] rounded-xl focus:outline-none transition-colors text-xs text-slate-800"
                    placeholder="Khu phố..."
                  />
                </div>

                <div>
                  <label className="block text-slate-500 text-[10px] font-bold uppercase mb-1">Đường dẫn repository GitHub</label>
                  <input 
                    type="text"
                    value={editFields.github}
                    onChange={(e) => handleChange('github', e.target.value)}
                    className="w-full px-3 py-2 border border-slate-200 focus:border-[#2c4a3e] rounded-xl focus:outline-none transition-colors text-xs font-mono text-slate-800"
                    placeholder="https://github.com/..."
                  />
                </div>

                <div>
                  <label className="block text-slate-500 text-[10px] font-bold uppercase mb-1">Lưu ý bản quyền (Hỗ trợ Markdown)</label>
                  <textarea 
                    rows={3}
                    value={editFields.copyright}
                    onChange={(e) => handleChange('copyright', e.target.value)}
                    className="w-full px-3 py-2 border border-slate-200 focus:border-[#2c4a3e] rounded-xl focus:outline-none transition-colors text-xs leading-relaxed resize-y font-mono"
                    placeholder="Lưu ý bản quyền..."
                  />
                </div>
              </div>
            </div>
          ) : (
            /* READ-ONLY DISPLAY */
            <div className="grid grid-cols-1 md:grid-cols-2 gap-8 items-start no-prose">
              {/* Left Column: Details & Resources */}
              <div className="space-y-6">
                <div className="space-y-4">
                  <h2 className="text-xl font-bold text-slate-800 m-0">
                    {language === 'vi' ? 'Ban phát triển dự án' : 'Project Development Team'}
                  </h2>
                  <div className="text-slate-650 text-xs leading-relaxed prose prose-sm max-w-none">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                      {displayContact.description}
                    </ReactMarkdown>
                  </div>

                  <div className="bg-emerald-50/30 border border-emerald-100/50 rounded-3xl p-6 space-y-4">
                    <div className="flex gap-4">
                      <div className="w-10 h-10 rounded-xl bg-white border border-slate-100 flex items-center justify-center text-[#2c4a3e] shrink-0 shadow-sm">
                        <Mail className="w-5 h-5" />
                      </div>
                      <div>
                        <h4 className="text-slate-800 font-bold text-xs m-0">
                          {language === 'vi' ? 'Địa chỉ Email' : 'Email Address'}
                        </h4>
                        <p className="text-slate-600 text-xs m-0 mt-0.5">
                          <a href={`mailto:${displayContact.email}`} className="text-[#2c4a3e] hover:underline font-semibold">{displayContact.email}</a>
                        </p>
                        <p className="text-slate-400 text-[10px] m-0">
                          {language === 'vi' 
                            ? 'Hỗ trợ kỹ thuật, bản quyền dữ liệu và đóng góp học thuật.' 
                            : 'Technical support, data copyright, and academic contributions.'}
                        </p>
                      </div>
                    </div>

                    <div className="flex gap-4">
                      <div className="w-10 h-10 rounded-xl bg-white border border-slate-100 flex items-center justify-center text-[#2c4a3e] shrink-0 shadow-sm">
                        <GraduationCap className="w-5 h-5" />
                      </div>
                      <div>
                        <h4 className="text-slate-800 font-bold text-xs m-0">
                          {language === 'vi' ? 'Đơn vị chủ quản' : 'Managing Unit'}
                        </h4>
                        <p className="text-slate-600 text-xs m-0 mt-0.5">{displayContact.unit}</p>
                        <p className="text-slate-400 text-[10px] m-0">
                          {language === 'vi'
                            ? 'Khoa Khoa học Máy tính / Phòng Thí nghiệm AI.'
                            : 'Faculty of Computer Science / AI Laboratory.'}
                        </p>
                      </div>
                    </div>

                    <div className="flex gap-4">
                      <div className="w-10 h-10 rounded-xl bg-white border border-slate-100 flex items-center justify-center text-[#2c4a3e] shrink-0 shadow-sm">
                        <MapPin className="w-5 h-5" />
                      </div>
                      <div>
                        <h4 className="text-slate-800 font-bold text-xs m-0">
                          {language === 'vi' ? 'Địa chỉ văn phòng' : 'Office Address'}
                        </h4>
                        <p className="text-slate-600 text-xs m-0 mt-0.5">{displayContact.office}</p>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="border border-slate-150 rounded-3xl p-6 flex flex-col justify-between h-56 hover:shadow-md transition-all bg-white">
                  <div>
                    <div className="w-10 h-10 rounded-xl bg-slate-900 text-white flex items-center justify-center mb-4">
                      <Github className="w-5 h-5" />
                    </div>
                    <h3 className="text-slate-800 font-bold text-sm m-0 mb-1.5">
                      {language === 'vi' ? 'Mã nguồn mở GitHub' : 'GitHub Open Source'}
                    </h3>
                    <p className="text-slate-500 text-xs leading-relaxed m-0">
                      {language === 'vi'
                        ? 'Dự án cam kết đóng góp cho cộng đồng nghiên cứu AI tại Việt Nam. Bạn có thể xem mã nguồn pipeline trích xuất OCR, Neo4j Loaders và NLU Engine của chúng tôi trên kho lưu trữ Github.'
                        : 'The project is committed to contributing to the AI research community in Vietnam. You can view our OCR extraction pipeline, Neo4j Loaders, and NLU Engine source code on the GitHub repository.'}
                    </p>
                  </div>
                  <a 
                    href={displayContact.github} 
                    target="_blank" 
                    rel="noreferrer"
                    className="mt-6 border-2 border-slate-100 hover:border-slate-350 hover:bg-slate-50 text-slate-700 font-bold text-xs text-center py-2.5 rounded-xl transition-all block flex items-center justify-center gap-1.5"
                  >
                    <Globe className="w-4 h-4" />
                    <span>{language === 'vi' ? 'Xem Repo GitHub' : 'View GitHub Repo'}</span>
                  </a>
                </div>

                <div className="bg-amber-50/30 border border-amber-100/50 rounded-3xl p-6 flex gap-3">
                  <Info className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
                  <div className="text-amber-800 text-xs m-0 leading-relaxed prose prose-sm max-w-none">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                      {displayContact.copyright}
                    </ReactMarkdown>
                  </div>
                </div>
              </div>

              {/* Right Column: Contact Form */}
              <div className="bg-white border border-slate-100 rounded-3xl p-8 shadow-sm space-y-6">
                {submitSuccess ? (
                  <div className="text-center py-12">
                    <CheckCircle className="w-12 h-12 text-emerald-500 mx-auto mb-4" />
                    <h3 className="text-lg font-bold text-slate-800 m-0 mb-2 font-black">
                      {language === 'vi' ? 'Gửi liên hệ thành công' : 'Message Sent Successfully'}
                    </h3>
                    <p className="text-slate-500 text-xs leading-relaxed m-0 mb-6 font-medium">
                      {language === 'vi'
                        ? 'Cảm ơn bạn đã gửi lời nhắn! Chúng tôi sẽ đọc và liên hệ lại với bạn sớm nhất có thể.'
                        : 'Thank you for your message! We will read it and get back to you as soon as possible.'}
                    </p>
                    <button
                      onClick={() => setSubmitSuccess(false)}
                      className="bg-emerald-50 hover:bg-emerald-100 text-[#2c4a3e] font-bold text-xs px-5 py-2.5 rounded-xl transition-all cursor-pointer border border-emerald-100"
                    >
                      {language === 'vi' ? 'Gửi tin nhắn khác' : 'Send another message'}
                    </button>
                  </div>
                ) : (
                  <form onSubmit={handleFormSubmit} className="space-y-4">
                    <h2 className="text-xl font-bold text-slate-800 m-0 mb-2 flex items-center gap-2">
                      <Mail className="w-5 h-5 text-[#2c4a3e]" />
                      {language === 'vi' ? 'Gửi tin nhắn liên hệ' : 'Send a message'}
                    </h2>
                    <p className="text-slate-400 text-xs leading-relaxed m-0 mb-4 font-semibold">
                      {language === 'vi'
                        ? 'Bạn có đóng góp ý kiến hay câu hỏi gì? Hãy điền thông tin bên dưới để gửi thư trực tiếp về ban quản trị.'
                        : 'Do you have any comments or questions? Please fill in the details below to send a message directly to the administrators.'}
                    </p>

                    <div>
                      <label className="block text-slate-700 text-xs font-bold mb-1">
                        {language === 'vi' ? 'Họ và tên *' : 'Full Name *'}
                      </label>
                      <input 
                        type="text" 
                        value={name}
                        onChange={(e) => setName(e.target.value)}
                        placeholder={language === 'vi' ? "Nguyễn Văn A" : "John Doe"}
                        required
                        className="w-full px-4 py-2.5 border border-slate-200 hover:border-slate-350 focus:border-[#2c4a3e] rounded-xl focus:outline-none transition-colors text-xs text-slate-800"
                      />
                    </div>

                    <div>
                      <label className="block text-slate-700 text-xs font-bold mb-1">
                        {language === 'vi' ? 'Email liên hệ *' : 'Contact Email *'}
                      </label>
                      <input 
                        type="email" 
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        placeholder="john.doe@example.com"
                        required
                        className="w-full px-4 py-2.5 border border-slate-200 hover:border-slate-350 focus:border-[#2c4a3e] rounded-xl focus:outline-none transition-colors text-xs text-slate-800"
                      />
                    </div>

                    <div>
                      <label className="block text-slate-700 text-xs font-bold mb-1">
                        {language === 'vi' ? 'Nội dung liên hệ *' : 'Message *'}
                      </label>
                      <textarea 
                        rows={6}
                        value={message}
                        onChange={(e) => setMessage(e.target.value)}
                        placeholder={language === 'vi' ? "Nhập nội dung bạn muốn gửi..." : "Enter the message you want to send..."}
                        required
                        className="w-full px-4 py-2.5 border border-slate-200 hover:border-slate-350 focus:border-[#2c4a3e] rounded-xl focus:outline-none transition-colors text-xs resize-none text-slate-800 leading-relaxed"
                      ></textarea>
                    </div>

                    <button
                      type="submit"
                      disabled={isSubmitting}
                      className="w-full bg-[#2c4a3e] hover:bg-[#1f352c] text-white font-bold py-3 px-4 rounded-xl transition-all duration-200 flex items-center justify-center gap-2 shadow-md shadow-emerald-900/10 text-xs active:scale-[0.98] disabled:opacity-50 cursor-pointer"
                    >
                      {isSubmitting ? (
                        <>
                          <RefreshCw className="w-4 h-4 animate-spin" />
                          {language === 'vi' ? 'Đang gửi...' : 'Sending...'}
                        </>
                      ) : (
                        <>
                          <Send className="w-4 h-4" />
                          {language === 'vi' ? 'Gửi tin nhắn' : 'Send message'}
                        </>
                      )}
                    </button>
                  </form>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </PublicDocLayout>
  );
};

export default Contact;
