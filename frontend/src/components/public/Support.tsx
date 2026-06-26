import React, { useState, useEffect } from 'react';
import PublicDocLayout from './PublicDocLayout';
import { useAuth } from '../../context/AuthContext';
import { useLanguageTheme } from '../../context/LanguageThemeContext';
import { defaultDocsEn } from '../../data/defaultDocsEn';
import { HelpCircle, ChevronDown, ChevronUp, Mail, Send, CheckCircle, RefreshCw, Edit2, Save, X, Trash2, Plus } from 'lucide-react';
import toast from 'react-hot-toast';

interface FAQItem {
  question: string;
  answer: string;
}

const Support: React.FC = () => {
  const { user } = useAuth();
  const { language, t } = useLanguageTheme();
  const [faqs, setFaqs] = useState<FAQItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [isEditing, setIsEditing] = useState(false);
  const [editFaqs, setEditFaqs] = useState<FAQItem[]>([]);
  const [saving, setSaving] = useState(false);

  const [openIndex, setOpenIndex] = useState<number | null>(0);
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [subject, setSubject] = useState('Hỏi đáp sử dụng hệ thống');
  const [message, setMessage] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitSuccess, setSubmitSuccess] = useState(false);

  const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

  useEffect(() => {
    fetchFaqs();
  }, []);

  useEffect(() => {
    if (language === 'en') {
      setSubject('Q&A System Usage');
    } else {
      setSubject('Hỏi đáp sử dụng hệ thống');
    }
  }, [language]);

  const fetchFaqs = async () => {
    try {
      const res = await fetch(`${API_URL}/docs/support`);
      if (res.ok) {
        const data = await res.json();
        setFaqs(data.content);
      }
    } catch (error) {
      console.error('Lỗi lấy FAQs:', error);
      toast.error(language === 'vi' ? 'Không thể lấy danh sách câu hỏi FAQ' : 'Cannot retrieve FAQ list');
    } finally {
      setLoading(false);
    }
  };

  const handleStartEdit = () => {
    setEditFaqs(JSON.parse(JSON.stringify(faqs)));
    setIsEditing(true);
  };

  const handleSave = async () => {
    // Validate
    for (const faq of editFaqs) {
      if (!faq.question.trim() || !faq.answer.trim()) {
        toast.error(language === 'vi' ? 'Vui lòng điền đầy đủ câu hỏi và câu trả lời!' : 'Please fill in all questions and answers!');
        return;
      }
    }

    setSaving(true);
    const token = localStorage.getItem('access_token');
    try {
      const res = await fetch(`${API_URL}/api/admin/docs/support`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ content: editFaqs })
      });

      if (res.ok) {
        setFaqs(editFaqs);
        toast.success(language === 'vi' ? 'Lưu danh sách FAQ thành công!' : 'FAQ list saved successfully!');
        setIsEditing(false);
      } else {
        const data = await res.json();
        toast.error(data.detail || (language === 'vi' ? 'Lỗi khi lưu danh sách FAQ' : 'Error saving FAQ list'));
      }
    } catch (error) {
      console.error('Lỗi lưu FAQs:', error);
      toast.error(language === 'vi' ? 'Lỗi hệ thống khi lưu FAQs' : 'System error while saving FAQs');
    } finally {
      setSaving(false);
    }
  };

  const handleAddFaq = () => {
    setEditFaqs([...editFaqs, { question: '', answer: '' }]);
  };

  const handleRemoveFaq = (index: number) => {
    const updated = editFaqs.filter((_, i) => i !== index);
    setEditFaqs(updated);
  };

  const handleFaqChange = (index: number, field: 'question' | 'answer', value: string) => {
    const updated = [...editFaqs];
    updated[index][field] = value;
    setEditFaqs(updated);
  };

  const toggleFaq = (index: number) => {
    setOpenIndex(openIndex === index ? null : index);
  };

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
          subject,
          message
        })
      });
      const data = await res.json();
      if (res.ok) {
        setSubmitSuccess(true);
        toast.success(data.message || (language === 'vi' ? "Đã gửi yêu cầu hỗ trợ thành công!" : "Support request submitted successfully!"));
        setName('');
        setEmail('');
        setMessage('');
      } else {
        toast.error(data.detail || (language === 'vi' ? "Không thể gửi yêu cầu hỗ trợ." : "Failed to submit support request."));
      }
    } catch (error) {
      console.error("Lỗi gửi yêu cầu hỗ trợ:", error);
      toast.error(language === 'vi' ? "Không thể kết nối đến máy chủ." : "Cannot connect to server.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const displayFaqs = (language === 'en' && faqs.length > 0 && faqs[0].question.startsWith('Hệ thống YHCT Diamond'))
    ? defaultDocsEn['support']
    : faqs;

  return (
    <PublicDocLayout>
      <div className="prose prose-slate max-w-none flex-1 flex flex-col justify-between">
        <div>
          {/* Title and Edit Button */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between border-b border-slate-100 pb-6 mb-8 gap-4">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-2xl bg-emerald-50 text-[#2c4a3e] flex items-center justify-center shrink-0">
                <HelpCircle className="w-6 h-6" />
              </div>
              <div>
                <h1 className="text-3xl font-extrabold text-slate-800 tracking-tight m-0">
                  {language === 'vi' ? 'Trang hỗ trợ & FAQ' : 'Support & FAQ'}
                </h1>
                <p className="text-slate-400 text-sm m-0 mt-1">
                  {language === 'vi' ? 'Giải đáp thắc mắc và gửi yêu cầu trợ giúp kỹ thuật' : 'Resolve questions and send technical support tickets'}
                </p>
              </div>
            </div>

            {/* Admin actions */}
            {user?.role === 'admin' && !loading && (
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
                      {t('policySaveBtn')}
                    </button>
                  </div>
                ) : (
                  <button
                    onClick={handleStartEdit}
                    className="px-4 py-2 border border-slate-200 hover:border-slate-350 bg-white hover:bg-slate-50 text-slate-700 font-bold rounded-xl text-xs flex items-center gap-1.5 shadow-sm transition-all cursor-pointer"
                  >
                    <Edit2 className="w-3.5 h-3.5 text-[#2c4a3e]" />
                    {language === 'vi' ? 'Chỉnh sửa FAQ' : 'Edit FAQ'}
                  </button>
                )}
              </div>
            )}
          </div>

          {loading ? (
            <div className="flex flex-col items-center justify-center py-20 text-[#2c4a3e] no-prose">
              <RefreshCw className="w-8 h-8 animate-spin mb-2" />
              <p className="text-sm font-bold">{t('policyLoading')}</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
              {/* FAQ Accordion Section */}
              <div className="lg:col-span-7 space-y-4 no-prose">
                <h2 className="text-lg font-bold text-slate-800 m-0 mb-4">
                  {language === 'vi' ? 'Câu hỏi thường gặp (FAQ)' : 'Frequently Asked Questions (FAQ)'}
                </h2>
                
                {isEditing ? (
                  /* EDITING MODE FAQ LIST */
                  <div className="space-y-4">
                    {editFaqs.map((faq, index) => (
                      <div key={index} className="p-4 bg-slate-50 border border-slate-200 rounded-2xl relative space-y-3">
                        <button
                          type="button"
                          onClick={() => handleRemoveFaq(index)}
                          className="absolute top-4 right-4 p-1.5 bg-red-50 hover:bg-red-100 text-red-600 rounded-lg transition-colors cursor-pointer"
                          title={language === 'vi' ? 'Xóa câu hỏi này' : 'Delete this question'}
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                        
                        <div className="pr-10">
                          <label className="block text-slate-500 text-[10px] font-bold uppercase mb-1">
                            {language === 'vi' ? `Câu hỏi #${index + 1}` : `Question #${index + 1}`}
                          </label>
                          <input 
                            type="text"
                            value={faq.question}
                            onChange={(e) => handleFaqChange(index, 'question', e.target.value)}
                            className="w-full px-3 py-2 border border-slate-200 focus:border-[#2c4a3e] rounded-xl focus:outline-none transition-colors text-xs font-bold text-slate-850"
                            placeholder={language === 'vi' ? 'Nhập câu hỏi...' : 'Enter question...'}
                          />
                        </div>

                        <div>
                          <label className="block text-slate-500 text-[10px] font-bold uppercase mb-1">
                            {language === 'vi' ? 'Câu trả lời' : 'Answer'}
                          </label>
                          <textarea 
                            rows={3}
                            value={faq.answer}
                            onChange={(e) => handleFaqChange(index, 'answer', e.target.value)}
                            className="w-full px-3 py-2 border border-slate-200 focus:border-[#2c4a3e] rounded-xl focus:outline-none transition-colors text-xs text-slate-700 leading-relaxed resize-y"
                            placeholder={language === 'vi' ? 'Nhập câu trả lời chi tiết...' : 'Enter detailed answer...'}
                          />
                        </div>
                      </div>
                    ))}

                    <button
                      type="button"
                      onClick={handleAddFaq}
                      className="w-full py-3 border-2 border-dashed border-slate-200 hover:border-[#2c4a3e] text-slate-500 hover:text-[#2c4a3e] font-bold rounded-2xl flex items-center justify-center gap-1.5 transition-all text-xs cursor-pointer bg-white"
                    >
                      <Plus className="w-4 h-4" />
                      {language === 'vi' ? 'Thêm câu hỏi FAQ mới' : 'Add new FAQ question'}
                    </button>
                  </div>
                ) : (
                  /* READ-ONLY FAQS */
                  displayFaqs.map((faq: FAQItem, index: number) => {
                    const isOpen = openIndex === index;
                    return (
                      <div 
                        key={index}
                        className={`border border-slate-100 rounded-2xl overflow-hidden transition-all duration-200 ${
                          isOpen ? 'bg-slate-50/50 shadow-sm border-emerald-100' : 'bg-white'
                        }`}
                      >
                        <button
                          onClick={() => toggleFaq(index)}
                          className="w-full px-5 py-4 flex items-center justify-between text-left font-bold text-slate-800 text-sm focus:outline-none cursor-pointer"
                        >
                          <span>{faq.question}</span>
                          {isOpen ? (
                            <ChevronUp className="w-4 h-4 text-[#2c4a3e]" />
                          ) : (
                            <ChevronDown className="w-4 h-4 text-slate-400" />
                          )}
                        </button>
                        {isOpen && (
                          <div className="px-5 pb-5 pt-1 text-xs text-slate-600 leading-relaxed border-t border-slate-50">
                            {faq.answer}
                          </div>
                        )}
                      </div>
                    );
                  })
                )}
              </div>

              {/* Support Ticket Form Section */}
              <div className="lg:col-span-5 bg-white border border-slate-100 rounded-3xl p-6 shadow-sm no-prose">
                {submitSuccess ? (
                  <div className="text-center py-8">
                    <CheckCircle className="w-12 h-12 text-emerald-500 mx-auto mb-4" />
                    <h3 className="text-lg font-bold text-slate-800 m-0 mb-2">
                      {language === 'vi' ? 'Đã nhận thông tin hỗ trợ' : 'Support Ticket Received'}
                    </h3>
                    <p className="text-slate-500 text-xs leading-relaxed m-0 mb-6">
                      {language === 'vi' 
                        ? 'Cảm ơn bạn đã liên hệ! Chúng tôi đã tiếp nhận yêu cầu hỗ trợ và sẽ gửi phản hồi giải quyết qua địa chỉ Email của bạn sớm nhất trong vòng 24 giờ.' 
                        : 'Thank you for contacting us! We have received your support request and will send a response to your Email address within 24 hours.'}
                    </p>
                    <button
                      onClick={() => setSubmitSuccess(false)}
                      className="bg-emerald-50 hover:bg-emerald-100 text-[#2c4a3e] font-bold text-xs px-5 py-2.5 rounded-xl transition-all cursor-pointer"
                    >
                      {language === 'vi' ? 'Gửi yêu cầu khác' : 'Send another request'}
                    </button>
                  </div>
                ) : (
                  <form onSubmit={handleFormSubmit} className="space-y-4">
                    <h2 className="text-lg font-bold text-slate-800 m-0 mb-4 flex items-center gap-2">
                      <Mail className="w-5 h-5 text-[#2c4a3e]" />
                      {language === 'vi' ? 'Gửi yêu cầu trợ giúp' : 'Submit Support Ticket'}
                    </h2>

                    <div>
                      <label className="block text-slate-700 text-xs font-bold mb-1">
                        {language === 'vi' ? 'Họ và tên *' : 'Full Name *'}
                      </label>
                      <input 
                        type="text" 
                        value={name}
                        onChange={(e) => setName(e.target.value)}
                        placeholder={language === 'vi' ? 'Nguyễn Văn A' : 'John Doe'}
                        required
                        className="w-full px-4 py-2.5 border border-slate-200 hover:border-slate-300 focus:border-[#2c4a3e] rounded-xl focus:outline-none transition-colors text-xs"
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
                        placeholder="yourname@gmail.com"
                        required
                        className="w-full px-4 py-2.5 border border-slate-200 hover:border-slate-350 focus:border-[#2c4a3e] rounded-xl focus:outline-none transition-colors text-xs"
                      />
                    </div>

                    <div>
                      <label className="block text-slate-700 text-xs font-bold mb-1">
                        {language === 'vi' ? 'Chủ đề cần hỗ trợ' : 'Support Topic'}
                      </label>
                      <select 
                        value={subject}
                        onChange={(e) => setSubject(e.target.value)}
                        className="w-full px-4 py-2.5 border border-slate-200 hover:border-slate-300 focus:border-[#2c4a3e] rounded-xl focus:outline-none bg-white transition-colors text-xs cursor-pointer"
                      >
                        {language === 'vi' ? (
                          <>
                            <option value="Hỏi đáp sử dụng hệ thống">Hỏi đáp sử dụng hệ thống</option>
                            <option value="Lỗi đăng nhập/Tài khoản">Lỗi đăng nhập/Tài khoản</option>
                            <option value="Sự cố nạp Token/Thanh toán">Sự cố nạp Token/Thanh toán</option>
                            <option value="Đóng góp ý kiến vị thuốc">Đóng góp ý kiến vị thuốc</option>
                            <option value="Báo cáo lỗi kỹ thuật khác">Báo cáo lỗi kỹ thuật khác</option>
                          </>
                        ) : (
                          <>
                            <option value="Q&A System Usage">Q&A System Usage</option>
                            <option value="Login/Account Issues">Login/Account Issues</option>
                            <option value="Token Recharge/Payment Issues">Token Recharge/Payment Issues</option>
                            <option value="Herb/Remedy Feedback">Herb/Remedy Feedback</option>
                            <option value="Report Other Technical Bugs">Report Other Technical Bugs</option>
                          </>
                        )}
                      </select>
                    </div>

                    <div>
                      <label className="block text-slate-700 text-xs font-bold mb-1">
                        {language === 'vi' ? 'Nội dung chi tiết *' : 'Detailed Message *'}
                      </label>
                      <textarea 
                        rows={4}
                        value={message}
                        onChange={(e) => setMessage(e.target.value)}
                        placeholder={language === 'vi' 
                          ? 'Mô tả chi tiết vấn đề bạn đang gặp phải hoặc đóng góp ý kiến cho hệ thống...' 
                          : 'Describe in detail the problem you are experiencing or share system feedback...'}
                        required
                        className="w-full px-4 py-2.5 border border-slate-200 hover:border-slate-350 focus:border-[#2c4a3e] rounded-xl focus:outline-none transition-colors text-xs resize-none"
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
                          {t('delProcessingBtn')}
                        </>
                      ) : (
                        <>
                          <Send className="w-4 h-4" />
                          {language === 'vi' ? 'Gửi tin nhắn hỗ trợ' : 'Send Support Message'}
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

export default Support;
