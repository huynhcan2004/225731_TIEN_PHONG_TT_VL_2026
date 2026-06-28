import React, { useState, useEffect, useRef } from 'react';
import { useAuth } from '../../context/AuthContext';
import { useNavigate, Link } from 'react-router-dom';
import toast from 'react-hot-toast';
import TopupModal from '../payment/TopupModal'; 
import MessageItem from '../chat/MessageItem';
import { Network, Settings, Trash2, BookOpen, X, LayoutDashboard, Menu, Plus, MessageSquare, LogOut, Sparkles, Send, Coins, Compass, Leaf, ChevronRight, Camera } from 'lucide-react';
import { 
  YHCT_HEROES, 
  YHCT_THEORIES, 
  YHCT_PHARMACOLOGY, 
  YHCT_DIAGNOSTICS 
} from '../../data/yhctKnowledge';
import { useLanguageTheme, BG_THEMES, BgColor } from '../../context/LanguageThemeContext';
import { useSiteSettings } from '../../context/SiteSettingsContext';
import { isMobileApp } from '../../utils/mobile';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  metadata?: any;
}

interface ChatSession {
  id: number;
  content: string;
  timestamp: string;
}

interface WikiData {
  title: string;
  extract: string;
}

const ChatView: React.FC = () => {
  const { user, logout, refreshUser } = useAuth();
  const navigate = useNavigate();
  const { language, bgColor, currentBg, t, setLanguage, setBgColor } = useLanguageTheme(); 
  const { siteTitle, siteLogo } = useSiteSettings(); 
  
  const [messages, setMessages] = useState<Message[]>(() => {
    const savedMessages = localStorage.getItem('current_chat_messages');
    return savedMessages ? JSON.parse(savedMessages) : [];
  });
  
  const [currentSessionId, setCurrentSessionId] = useState<number | null>(() => {
    const savedId = localStorage.getItem('current_session_id');
    return savedId ? parseInt(savedId) : null;
  });
  
  const [history, setHistory] = useState<ChatSession[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [selectedModel, setSelectedModel] = useState('gemini-2.5-flash');
  const [isBillingModalOpen, setIsBillingModalOpen] = useState(false);

  const [currentGraph, setCurrentGraph] = useState({ nodes: [], links: [] });

  // ✨ STATE QUẢN LÝ GIAO DIỆN
  const [showSettingsMenu, setShowSettingsMenu] = useState(false);
  const [showWikiModal, setShowWikiModal] = useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false); // Sidebar trượt trên Mobile
  const [wikiData, setWikiData] = useState<WikiData[]>([]);

  const scrollRef = useRef<HTMLDivElement>(null);
  const messagesContainerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

  const handleAvatarChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (file.size > 5 * 1024 * 1024) {
      toast.error(language === 'vi' ? 'Dung lượng ảnh không được vượt quá 5MB' : 'Image size must not exceed 5MB');
      return;
    }

    const toastId = toast.loading(language === 'vi' ? 'Đang tải ảnh đại diện lên...' : 'Uploading avatar...');

    try {
      const token = localStorage.getItem('access_token');
      const formDataPayload = new FormData();
      formDataPayload.append('file', file);

      const res = await fetch(`${API_URL}/auth/avatar`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        },
        body: formDataPayload
      });

      if (res.ok) {
        toast.success(language === 'vi' ? 'Đổi ảnh đại diện thành công!' : 'Avatar updated successfully!', { id: toastId });
        await refreshUser();
      } else {
        const errorData = await res.json().catch(() => ({}));
        toast.error(errorData.detail || (language === 'vi' ? 'Đã có lỗi xảy ra' : 'An error occurred'), { id: toastId });
      }
    } catch (error) {
      console.error('Lỗi khi tải avatar:', error);
      toast.error(language === 'vi' ? 'Không thể kết nối đến máy chủ' : 'Cannot connect to server', { id: toastId });
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('current_chat_messages');
    localStorage.removeItem('current_session_id'); 
    setCurrentSessionId(null);
    setCurrentGraph({ nodes: [], links: [] });
    setMessages([]);
    logout();
  };

  const getValidToken = () => {
    const token = localStorage.getItem('access_token');
    return token;
  };

  const fetchHistory = async () => {
    try {
      const token = getValidToken();
      if (!token) return; 
      
      const response = await fetch(`${API_URL}/chatbot/history`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (response.status === 401) {
        toast.error("Phiên đăng nhập đã hết hạn, vui lòng đăng nhập lại.");
        handleLogout();
        return;
      }

      const data = await response.json();
      if (response.ok) {
        setHistory(data.history);
      }
    } catch (error) {
      console.error("Không thể lấy lịch sử chat:", error);
    }
  };

  const handleSelectHistory = async (chatId: number) => {
    setIsLoading(true);
    setCurrentSessionId(chatId);
    localStorage.setItem('current_session_id', chatId.toString());
    setIsMobileMenuOpen(false); // Ẩn menu mobile khi chọn xong

    try {
      const token = getValidToken();
      if (!token) return;

      const response = await fetch(`${API_URL}/chatbot/history/session/${chatId}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (response.status === 401) {
        handleLogout();
        return;
      }

      const data = await response.json();
      if (response.ok && data.messages) {
        setMessages(data.messages);
        localStorage.setItem('current_chat_messages', JSON.stringify(data.messages));
      }
    } catch (error) {
      console.error("Lỗi kết nối lịch sử:", error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleDeleteHistory = async (e: React.MouseEvent, chatId: number) => {
    e.stopPropagation(); 
    if (!window.confirm("Bạn có chắc chắn muốn xóa lịch sử này?")) return;

    try {
      const token = getValidToken();
      if (!token) return;

      const response = await fetch(`${API_URL}/chatbot/history/${chatId}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (response.ok) {
        setHistory(prev => prev.filter(item => item.id !== chatId));
        if (currentSessionId === chatId) {
          setMessages([]);
          setCurrentSessionId(null);
          setCurrentGraph({ nodes: [], links: [] });
          localStorage.removeItem('current_chat_messages');
          localStorage.removeItem('current_session_id');
        }
      }
    } catch (error) {
      console.error("Lỗi xóa lịch sử:", error);
    }
  };

  const handleDeleteAllHistory = async () => {
    if (!window.confirm("⚠️ BẠN CÓ CHẮC CHẮN MUỐN XÓA TOÀN BỘ LỊCH SỬ?")) return;
    
    setShowSettingsMenu(false);
    setIsLoading(true);
    const toastId = toast.loading("Đang dọn dẹp toàn bộ dữ liệu...");

    try {
      const token = getValidToken();
      if (!token) return;

      for (const item of history) {
        await fetch(`${API_URL}/chatbot/history/${item.id}`, {
          method: 'DELETE',
          headers: { 'Authorization': `Bearer ${token}` }
        });
      }

      setHistory([]);
      setMessages([]);
      setCurrentSessionId(null);
      setCurrentGraph({ nodes: [], links: [] });
      localStorage.removeItem('current_chat_messages');
      localStorage.removeItem('current_session_id');
      
      toast.success("Đã xóa sạch toàn bộ lịch sử!", { id: toastId });
    } catch (error) {
      toast.error("Có lỗi xảy ra trong quá trình xóa.", { id: toastId });
    } finally {
      setIsLoading(false);
    }
  };

  const openWikiModal = () => {
    setShowSettingsMenu(false);
    const combinedKnowledge = [
      ...YHCT_HEROES,
      ...YHCT_THEORIES,
      ...YHCT_PHARMACOLOGY,
      ...YHCT_DIAGNOSTICS
    ];
    setWikiData(combinedKnowledge); 
    setShowWikiModal(true);
  };

  useEffect(() => {
    window.scrollTo(0, 0);
    fetchHistory();
    
    // Tự động đồng bộ mô hình AI hoạt động được cấu hình từ Admin
    const fetchActiveModel = async () => {
      try {
        const response = await fetch(`${API_URL}/chatbot/config`);
        if (response.ok) {
          const data = await response.json();
          if (data.active_model) {
            setSelectedModel(data.active_model);
          }
        }
      } catch (error) {
        console.error("Không thể lấy cấu hình mô hình hoạt động:", error);
      }
    };
    fetchActiveModel();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (messagesContainerRef.current) {
      messagesContainerRef.current.scrollTo({
        top: messagesContainerRef.current.scrollHeight,
        behavior: 'smooth'
      });
    }
  }, [messages, isLoading]);

  useEffect(() => {
    localStorage.setItem('current_chat_messages', JSON.stringify(messages));
  }, [messages]);

  const handleSendMessage = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!input.trim() || isLoading) return;

    const currentInput = input;
    const userMsg: Message = { role: 'user', content: currentInput };
    
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setIsLoading(true);

    try {
      const token = getValidToken();
      if (!token) throw new Error(language === 'vi' ? "Mất kết nối mã xác thực." : "Authentication token lost.");
      
      const response = await fetch(`${API_URL}/chatbot/query`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}` 
        },
        body: JSON.stringify({ 
          message: currentInput,
          model: selectedModel,
          session_id: currentSessionId,
          lang: language
        }),
      });

      if (response.status === 401) {
        handleLogout();
        throw new Error(language === 'vi' ? "Phiên làm việc kết thúc do lỗi bảo mật." : "Session ended due to security error.");
      }

      const data = await response.json();

      if (response.ok) {
        if (data.session_id && !currentSessionId) {
          setCurrentSessionId(data.session_id);
          localStorage.setItem('current_session_id', data.session_id.toString());
        }

        const aiResponse: Message = { 
          role: 'assistant', 
          content: data.answer || (language === 'vi' ? "Xin lỗi, tôi không có câu trả lời cho vấn đề này." : "Sorry, I don't have an answer for this query."),
          metadata: data.metadata 
        };
        setMessages(prev => [...prev, aiResponse]);
        
        if (data.graph_data && data.graph_data.nodes.length > 0) {
            setCurrentGraph(data.graph_data);
        } else {
            setCurrentGraph({ nodes: [], links: [] });
        }

        fetchHistory(); 
        if (refreshUser) await refreshUser();

      } else {
        if (response.status === 402) {
            toast.error(language === 'vi' ? "Bạn đã hết Token rồi! Vui lòng nạp thêm để tiếp tục." : "You have run out of Tokens! Please top up to continue.");
            setIsBillingModalOpen(true);
            throw new Error(language === 'vi' ? "Số dư Token không đủ." : "Insufficient Token balance.");
        }
        throw new Error(data.detail || (language === 'vi' ? "Lỗi xử lý từ máy chủ AI." : "AI server processing error."));
      }
    } catch (error: any) {
      setMessages(prev => [...prev, { role: 'assistant', content: `❌ ${error.message}` }]);
    } finally {
      setIsLoading(false);
      inputRef.current?.focus();
    }
  };

  const handleSuggestionClick = (suggestion: string) => {
    setInput(suggestion);
    inputRef.current?.focus();
  };  const openGraphExplorer = () => {
    navigate('/graph-explorer', { state: { graphData: currentGraph } });
  };

  return (
    <div className="flex h-screen w-full text-slate-100 overflow-hidden font-sans relative" style={{ backgroundColor: currentBg.bodyBg }}>
      
      {/* Cyber Grid Background */}
      <div className="absolute inset-0 opacity-[0.04] pointer-events-none z-0" 
           style={{ backgroundImage: 'radial-gradient(#1b8961 1px, transparent 1px)', backgroundSize: '32px 32px' }}>
      </div>
      
      {/* Cyber Ambient glows */}
      <div className="absolute top-[-20%] left-[-20%] w-[60%] h-[60%] rounded-full bg-emerald-500/5 blur-[150px] pointer-events-none z-0 animate-pulse" style={{ animationDuration: '8s' }}></div>
      <div className="absolute bottom-[-20%] right-[-20%] w-[60%] h-[60%] rounded-full bg-amber-500/3 blur-[150px] pointer-events-none z-0 animate-pulse" style={{ animationDuration: '12s' }}></div>
      
      {/* ✨ OVERLAY CHO MOBILE SIDEBAR */}
      {isMobileMenuOpen && (
        <div 
          className="fixed inset-0 bg-black/60 z-40 md:hidden backdrop-blur-sm transition-all duration-300" 
          onClick={() => setIsMobileMenuOpen(false)}
        />
      )}

      {/* --- CỘT 1: SIDEBAR LỊCH SỬ (DẠNG TRƯỢT TRÊN MOBILE) --- */}
      <div 
        className={`
          fixed inset-y-0 left-0 transform ${isMobileMenuOpen ? 'translate-x-0' : '-translate-x-full'}
          md:relative md:translate-x-0 transition-transform duration-300 ease-in-out z-50
          w-72 backdrop-blur-md border-r border-emerald-500/10 flex flex-col shrink-0 shadow-2xl md:shadow-none
        `}
        style={{ backgroundColor: currentBg.panelBg + 'f2' }}
      >
        <div className="p-5 border-b border-emerald-500/10 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-3 hover:opacity-90 transition-opacity">
            <div className="w-10 h-10 bg-gradient-to-tr from-emerald-600 via-teal-600 to-amber-500 rounded-xl flex items-center justify-center text-white font-black shadow-md shadow-emerald-500/20 relative overflow-hidden group border border-emerald-400/20 shrink-0">
              {siteLogo ? (
                <img src={siteLogo} alt="Logo" className="w-full h-full object-contain" />
              ) : (
                <span className="relative z-10 text-emerald-50">
                  {siteTitle ? siteTitle.charAt(0).toUpperCase() : 'D'}
                </span>
              )}
              <div className="absolute inset-0 bg-white/10 translate-y-full group-hover:translate-y-0 transition-transform duration-300"></div>
            </div>
            <div>
              <span className="font-black text-emerald-50 text-base block leading-tight tracking-tight text-left">
                {siteTitle}
              </span>
              <span className="text-[9px] uppercase tracking-widest text-emerald-500/60 font-black block text-left">{t('graphRAGNode')}</span>
            </div>
          </Link>
          {/* Nút đóng Sidebar trên Mobile */}
          <button className="md:hidden p-2 text-slate-500 hover:text-emerald-400 hover:bg-emerald-950/20 rounded-lg transition-colors" onClick={() => setIsMobileMenuOpen(false)}>
            <X size={18} />
          </button>
        </div>
        
        <div className="flex-1 overflow-y-auto p-4 space-y-4 custom-scrollbar">
          <button 
            onClick={() => {
              setMessages([]);
              setCurrentGraph({ nodes: [], links: [] });
              setCurrentSessionId(null);
              localStorage.removeItem('current_chat_messages');
              localStorage.removeItem('current_session_id');
              setIsMobileMenuOpen(false); // Ẩn sidebar trên mobile sau khi tạo mới
            }}
            className="w-full flex items-center justify-center gap-2 p-3 rounded-xl bg-gradient-to-r from-emerald-600 via-teal-600 to-amber-600 hover:from-emerald-700 hover:to-amber-500 text-white font-bold text-sm shadow-[0_0_15px_rgba(16,185,129,0.15)] active:scale-98 transition-all duration-200 border border-emerald-400/20"
          >
            <Plus size={16} />
            <span>{t('newChat')}</span>
          </button>
          
          <div className="pt-2 px-1 text-[9px] font-black text-emerald-500/50 uppercase tracking-widest">{t('queryHistory')}</div>
          
          <div className="space-y-1">
            {history.length > 0 ? (
              history.map((item) => (
                <div 
                  key={item.id}
                  onClick={() => handleSelectHistory(item.id)}
                  className={`group p-3 text-sm rounded-xl cursor-pointer transition-all duration-200 flex items-center justify-between hover:translate-x-0.5 ${
                    currentSessionId === item.id 
                      ? 'bg-emerald-950/30 border-l-4 border-emerald-500 text-emerald-300 font-bold rounded-r-xl rounded-l-none pl-3 shadow-[0_0_15px_rgba(16,185,129,0.03)] border-y border-r border-emerald-500/10' 
                      : 'text-slate-400 hover:bg-emerald-950/15 hover:text-emerald-300'
                  }`}
                >
                  <div className="flex items-center gap-2.5 truncate flex-1">
                    <MessageSquare size={14} className={currentSessionId === item.id ? 'text-emerald-400' : 'text-emerald-500/40'} />
                    <span className="truncate">{item.content}</span>
                  </div>
                  <button 
                    onClick={(e) => handleDeleteHistory(e, item.id)}
                    className="opacity-0 group-hover:opacity-100 p-1 hover:bg-red-950/30 hover:text-red-400 rounded-md transition-all duration-200"
                  >
                    <Trash2 size={13} />
                  </button>
                </div>
              ))
            ) : (
              <p className="text-center text-xs text-slate-500 py-6 italic bg-emerald-950/5 rounded-xl border border-dashed border-emerald-950/20">{t('noHistory')}</p>
            )}
          </div>
        </div>

        {/* Thông tin tài khoản & Cài đặt nhanh ở đáy Sidebar */}
        <div className="p-4 border-t border-emerald-500/10 bg-[#08150f]/20 flex flex-col gap-3">
          <div className="flex items-center gap-3">
            <div className="relative group cursor-pointer shrink-0" onClick={() => fileInputRef.current?.click()} title={language === 'vi' ? 'Đổi ảnh đại diện' : 'Change avatar'}>
              <img 
                src={user?.avatar_url || 'https://via.placeholder.com/40'} 
                className="w-9 h-9 rounded-full border border-emerald-500/20 object-cover hover:border-emerald-400/40 transition-colors" 
                alt="Avatar" 
              />
              <div className="absolute inset-0 bg-black/40 rounded-full flex items-center justify-center opacity-0 hover:opacity-100 transition-opacity">
                <Camera size={10} className="text-white animate-pulse" />
              </div>
            </div>
            <div className="flex-1 min-w-0 text-left">
              <p className="text-xs font-black text-slate-200 truncate">{user?.username || user?.email?.split('@')[0]}</p>
              <p className="text-[9px] text-slate-500 truncate">{user?.email}</p>
            </div>
          </div>
          <div className="flex items-center justify-between mt-1">
            <button 
              onClick={() => setLanguage(language === 'vi' ? 'en' : 'vi')} 
              className="text-xs font-bold text-emerald-400 bg-emerald-950/45 border border-emerald-500/25 py-1.5 px-3 rounded-xl hover:bg-emerald-900/35 transition-colors cursor-pointer"
            >
              {language === 'vi' ? '🇻🇳 VI / EN' : '🇬🇧 EN / VI'}
            </button>
            <button 
              onClick={handleLogout} 
              className="text-xs font-bold text-rose-400 bg-rose-950/20 border border-rose-500/15 py-1.5 px-3 rounded-xl hover:bg-rose-900/35 transition-all cursor-pointer flex items-center gap-1.5"
            >
              <LogOut size={12} />
              <span>{t('logout')}</span>
            </button>
          </div>
        </div>

        {/* Chân thanh bên chứa các liên kết chính sách dịch thuật */}
        <div className="p-4 border-t border-emerald-500/10 bg-[#08150f]/30 flex flex-wrap gap-x-2 gap-y-1.5 justify-center text-[10px] text-slate-400 font-bold">
          <a href="/privacy-policy" className="hover:text-emerald-400 transition-colors">{t('privacy')}</a>
          <span className="text-emerald-950">•</span>
          <a href="/terms-of-service" className="hover:text-emerald-400 transition-colors">{t('terms')}</a>
          <span className="text-emerald-950">•</span>
          <a href="/data-deletion" className="hover:text-emerald-400 transition-colors">{t('dataDeletion')}</a>
          <span className="text-emerald-950">•</span>
          <a href="/support" className="hover:text-emerald-400 transition-colors">{t('support')}</a>
          <span className="text-emerald-950">•</span>
          <a href="/contact" className="hover:text-emerald-400 transition-colors">{t('contact')}</a>
        </div>
      </div>

      {/* --- CỘT 2: KHUNG CHAT CHÍNH --- */}
      <div className="flex-1 flex flex-col h-full overflow-hidden relative w-full max-w-full z-10 bg-transparent">
        <header className="h-16 border-b border-emerald-500/10 flex items-center justify-between px-4 sm:px-6 z-10 shrink-0 shadow-lg shadow-black/10 sticky top-0" style={{ backgroundColor: currentBg.panelBg + 'cc' }}>
          <div className="flex items-center gap-3">
            {/* Nút Hamburger mở Sidebar trên Mobile */}
            <button onClick={() => setIsMobileMenuOpen(true)} className="md:hidden p-2 text-slate-400 hover:text-emerald-400 rounded-lg bg-emerald-950/20 border border-emerald-500/10 transition-colors">
               <Menu size={20} />
            </button>
            
            <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-emerald-950/35 border border-emerald-500/25 text-xs font-bold text-emerald-300 shadow-sm">
              <Sparkles size={12} className="text-emerald-400" />
              <span>
                {selectedModel === 'gemini-2.5-flash' ? 'Gemini 2.5 Flash' :
                 selectedModel === 'gpt-4o-mini' ? 'GPT-4o Mini' :
                 selectedModel === 'gpt-4o' ? 'GPT-4o' :
                 selectedModel === 'qwen2.5-coder:7b' ? 'Qwen 2.5' :
                 selectedModel}
              </span>
            </div>
          </div>
          
          <div className="flex items-center gap-3 sm:gap-4">
            {/* Nút chuyển đổi ngôn ngữ - Ẩn trên Mobile App */}
            {!isMobileApp() && (
              <button 
                onClick={() => setLanguage(language === 'vi' ? 'en' : 'vi')} 
                className="flex items-center gap-1.5 bg-emerald-950/20 hover:bg-[#08150f] py-1.5 px-3 rounded-full border border-emerald-500/10 hover:border-emerald-500/30 text-xs font-bold text-emerald-300 transition-all cursor-pointer shadow-sm hover:shadow-md"
              >
                <span>{language === 'vi' ? '🇻🇳 VI' : '🇬🇧 EN'}</span>
              </button>
            )}

            <div 
              onClick={() => setIsBillingModalOpen(true)}
              className="flex items-center gap-2 bg-[#08150f] border border-emerald-500/20 hover:border-emerald-400/40 py-1.5 px-3 rounded-full cursor-pointer hover:bg-emerald-950/40 hover:shadow-md hover:shadow-emerald-500/5 transition-all duration-300 shadow-sm"
            >
              <div className="w-5 h-5 rounded-full bg-emerald-500/10 flex items-center justify-center">
                <Coins size={12} className="text-emerald-400 animate-pulse" />
              </div>
              <div className="text-left">
                <p className="text-[9px] font-bold text-emerald-500/50 leading-none uppercase hidden sm:block">{t('walletSub')}</p>
                <p className="text-xs sm:text-sm font-black text-emerald-300 leading-none">
                  {user?.token_balance != null ? Number(user.token_balance).toLocaleString() : 0} 💎
                </p>
              </div>
            </div>
            
            {/* Ảnh đại diện & Nút đăng xuất - Ẩn trên Mobile App (được hiển thị đầy đủ trong Sidebar) */}
            {!isMobileApp() && (
              <>
                <div className="relative group cursor-pointer" onClick={() => fileInputRef.current?.click()} title={language === 'vi' ? 'Đổi ảnh đại diện' : 'Change avatar'}>
                  <img 
                    src={user?.avatar_url || 'https://via.placeholder.com/40'} 
                    className="w-8 h-8 sm:w-9 sm:h-9 rounded-full border-2 border-emerald-500/20 shadow-md object-cover ring-2 ring-emerald-500/10 group-hover:ring-emerald-400/40 transition-all duration-300" 
                    alt="Avatar" 
                  />
                  <div className="absolute inset-0 bg-black/40 rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity duration-300">
                    <Camera size={12} className="text-white animate-pulse" />
                  </div>
                </div>
                
                <button onClick={handleLogout} className="text-xs font-bold text-slate-400 hover:text-rose-400 transition-colors flex items-center gap-1.5 bg-emerald-950/20 hover:bg-rose-950/30 py-1.5 px-3 rounded-full border border-emerald-500/10 hover:border-rose-500/20">
                  <LogOut size={12} />
                  <span className="hidden sm:inline">{t('logout')}</span>
                </button>
              </>
            )}
            
            {/* Input file ẩn luôn luôn render để có thể kích hoạt upload avatar từ sidebar trên mobile */}
            <input 
              type="file" 
              ref={fileInputRef} 
              className="hidden" 
              accept="image/*" 
              onChange={handleAvatarChange} 
            />
          </div>
        </header>

        <div ref={messagesContainerRef} className="flex-1 overflow-y-auto bg-transparent relative custom-scrollbar">
          {messages.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-center p-6 sm:p-8 max-w-4xl mx-auto z-10 relative">
              
              {/* Glowing leaf node HUD */}
              <div className="relative w-24 h-24 bg-gradient-to-tr from-emerald-600 via-teal-600 to-amber-500 rounded-3xl flex items-center justify-center text-white text-4xl shadow-xl shadow-emerald-500/10 mb-6 animate-bounce" style={{ animationDuration: '6s' }}>
                {siteLogo ? (
                  <img src={siteLogo} alt="Logo" className="w-16 h-16 object-contain rounded-2xl animate-pulse" />
                ) : (
                  <Leaf size={40} className="animate-pulse text-emerald-100" />
                )}
                <div className="absolute inset-0 rounded-3xl bg-gradient-to-tr from-emerald-500 to-amber-500 blur-lg opacity-30 -z-10 scale-95"></div>
                {/* HUD rotating circle */}
                <div className="absolute -inset-1.5 rounded-[22px] border border-emerald-500/20 pointer-events-none animate-spin-slow" style={{ animationDuration: '12s' }}></div>
              </div>

              <h3 className="text-3xl sm:text-4xl font-black text-slate-100 mb-2 tracking-tight">
                {siteTitle}
              </h3>
              <p className="text-sm sm:text-base text-slate-400 max-w-md mx-auto mb-4 font-medium">{t('loginSubtitle')}</p>
              
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 w-full max-w-2xl mt-8 px-4 z-10">
                {(language === 'vi' 
                  ? [
                      { text: "Ích mẫu có bài thuốc nào?", icon: "🌿" },
                      { text: "Thuốc nào tính hàn chữa sưng đau?", icon: "❄️" },
                      { text: "Vị thuốc Chỉ thiên có tính hàn không?", icon: "🧪" },
                      { text: "Chó đẻ răng cưa chữa bệnh gì?", icon: "📖" }
                    ]
                  : [
                      { text: "What remedies contain Motherwort?", icon: "🌿" },
                      { text: "Which herbs are cold properties for swelling and pain?", icon: "❄️" },
                      { text: "Does Chi thien have cold property?", icon: "🧪" },
                      { text: "What diseases does Cho de rang cua cure?", icon: "📖" }
                    ]
                ).map((suggestion, idx) => (
                  <button 
                    key={idx}
                    onClick={() => handleSuggestionClick(suggestion.text)}
                    className="p-4 bg-[#08150f]/60 hover:bg-[#0c2017]/80 border border-emerald-500/10 hover:border-emerald-400 rounded-2xl text-sm font-semibold text-slate-300 hover:text-emerald-100 shadow-sm hover:shadow-[0_0_15px_rgba(16,185,129,0.08)] hover:-translate-y-0.5 active:translate-y-0 transition-all duration-300 text-left flex items-start gap-3 group"
                  >
                    <span className="text-xl shrink-0 group-hover:scale-110 transition-transform duration-300">{suggestion.icon}</span>
                    <span className="flex-1">"{suggestion.text}"</span>
                    <ChevronRight size={16} className="text-emerald-600/40 group-hover:text-emerald-400 group-hover:translate-x-0.5 transition-all self-center shrink-0" />
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="pb-8 max-w-5xl mx-auto z-10 relative">
              {messages.map((msg, index) => (
                <MessageItem 
                  key={index}
                  role={msg.role} 
                  content={msg.content} 
                  metadata={msg.metadata}
                  intent={msg.metadata?.intent}
                  modelUsed={selectedModel}
                  execTime={msg.metadata?.exec_time}
                />
              ))}
              {isLoading && (
                <div className="p-5 sm:p-6 bg-emerald-950/5 border-y border-emerald-500/5 flex gap-4 animate-pulse">
                   <div className="w-9 h-9 rounded-xl bg-emerald-950/40 border border-emerald-500/10 shrink-0"></div>
                   <div className="flex-1 space-y-2.5 mt-2">
                     <div className="h-4 bg-emerald-950/40 rounded w-1/3"></div>
                     <div className="h-3 bg-emerald-950/30 rounded w-3/4"></div>
                   </div>
                </div>
              )}
              <div ref={scrollRef} className="h-4" />
            </div>
          )}

        </div>

        {/* ✨ WIDGET CÀI ĐẶT FLOATING (GÓC DƯỚI PHẢI) */}
        <div className="absolute bottom-[72px] sm:bottom-24 right-4 md:absolute md:bottom-24 md:right-6 z-40 flex flex-col items-end">
          {showSettingsMenu && (
            <div className="mb-3 w-56 backdrop-blur-md rounded-2xl shadow-[0_10px_40px_rgba(0,0,0,0.5)] border border-emerald-500/15 overflow-hidden animate-slideUp origin-bottom-right" style={{ backgroundColor: currentBg.panelBg + 'f2' }}>
              <div className="p-3 border-b border-emerald-500/10 bg-[#08150f]/80 flex justify-between items-center">
                <span className="text-[9px] font-black text-slate-500 uppercase tracking-widest">{t('options')}</span>
              </div>
              
              <div className="p-3 border-b border-emerald-500/10 bg-[#08150f]/30">
                <span className="text-[9px] font-black text-slate-500 uppercase tracking-widest">{t('changeBg')}</span>
                <div className="grid grid-cols-2 gap-1.5 mt-2">
                  {(Object.keys(BG_THEMES) as BgColor[]).map((themeKey) => {
                    const theme = BG_THEMES[themeKey];
                    return (
                      <button
                        key={themeKey}
                        onClick={() => setBgColor(themeKey)}
                        className={`py-1.5 px-2 text-[10px] font-bold rounded-lg border transition-all text-center cursor-pointer ${
                          bgColor === themeKey 
                            ? 'bg-emerald-600 text-white border-emerald-400 shadow-[0_0_10px_rgba(27,137,97,0.3)]' 
                            : 'bg-emerald-950/20 text-slate-300 border-emerald-500/10 hover:border-emerald-500/35 hover:text-emerald-300'
                        }`}
                      >
                        {language === 'vi' ? theme.nameVi : theme.nameEn}
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* ✨ NÚT ADMIN: Chỉ hiện khi user là admin */}
              {user?.role === 'admin' && (
                <button 
                  onClick={() => navigate('/admin')}
                  className="w-full flex items-center gap-3 p-3 text-sm font-bold text-blue-400 hover:bg-emerald-950/30 transition-colors border-b border-emerald-500/10 cursor-pointer"
                >
                  <LayoutDashboard size={15} /> <span>{t('adminDashboard')}</span>
                </button>
              )}

              <button 
                onClick={openWikiModal}
                className="w-full flex items-center gap-3 p-3 text-sm font-semibold text-slate-300 hover:bg-emerald-950/30 hover:text-emerald-300 transition-colors border-b border-emerald-500/10 cursor-pointer"
              >
                <BookOpen size={15} className="text-emerald-500/60" /> <span>{t('encyclopedia')}</span>
              </button>
              
              <button 
                onClick={handleDeleteAllHistory}
                className="w-full flex items-center gap-3 p-3 text-sm font-semibold text-rose-400 hover:bg-rose-950/30 transition-colors cursor-pointer"
              >
                <Trash2 size={15} className="text-rose-500/60" /> <span>{t('clearHistory')}</span>
              </button>
            </div>
          )}
          
          <button 
            onClick={() => setShowSettingsMenu(!showSettingsMenu)}
            className={`p-3.5 rounded-full shadow-lg transition-all duration-300 border active:scale-95 cursor-pointer ${
              showSettingsMenu 
                ? 'bg-slate-800 text-white border-slate-700 shadow-black/20' 
                : 'bg-[#060e0a] text-emerald-400 hover:text-emerald-300 border-emerald-500/20 hover:border-emerald-400/50 shadow-emerald-950/50'
            }`}
            style={{ backgroundColor: currentBg.panelBg }}
          >
            {showSettingsMenu ? <X size={20} /> : <Settings size={20} className="animate-spin-slow" style={{ animationDuration: '8s' }} />}
          </button>
        </div>

        {/* Nút bật Graph Explorer cho cả Mobile và Desktop */}
        {currentGraph.nodes.length > 0 && (
           <button 
              onClick={openGraphExplorer}
              className="absolute bottom-[76px] sm:bottom-24 right-20 md:bottom-24 md:right-24 z-20 p-3.5 bg-gradient-to-r from-emerald-600 via-teal-600 to-amber-500 text-white rounded-full shadow-lg hover:from-emerald-700 hover:to-amber-600 active:scale-95 transition-all border border-emerald-400/20 cursor-pointer"
              title={t('graphTitle') || "Xem bản đồ tri thức"}
            >
              <Network size={20} />
           </button>
        )}

        <div className="w-full shrink-0 box-border m-0 p-2.5 sm:p-4 border-t border-emerald-500/10 z-20 backdrop-blur-sm" style={{ backgroundColor: currentBg.panelBg + 'd9' }}>
          <form onSubmit={handleSendMessage} className="max-w-4xl mx-auto relative flex items-center border border-emerald-500/15 focus-within:border-emerald-400 focus-within:ring-2 focus-within:ring-emerald-400/10 focus-within:bg-[#08150f]/80 rounded-2xl shadow-xl transition-all duration-300 p-1 sm:p-1.5 pl-3 pr-1.5 sm:pr-2" style={{ backgroundColor: currentBg.panelBg + 'cc' }}>
            <input
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={t('placeholderChat')}
              className="flex-1 py-2.5 sm:py-3 bg-transparent outline-none text-sm sm:text-base text-emerald-50 placeholder-emerald-700/60 pl-1"
              disabled={isLoading}
            />
            <button 
              type="submit"
              disabled={isLoading || !input.trim()}
              className="px-4 py-2 sm:px-5 sm:py-2.5 bg-gradient-to-r from-emerald-600 to-teal-500 hover:from-emerald-500 hover:to-teal-400 text-white rounded-xl font-bold text-sm shadow-md shadow-emerald-500/10 hover:shadow-[0_0_15px_rgba(16,185,129,0.25)] hover:-translate-y-0.5 active:translate-y-0 disabled:bg-slate-900 disabled:text-slate-600 disabled:shadow-none disabled:-translate-y-0 transition-all duration-200 flex items-center gap-1.5 border border-emerald-400/15 cursor-pointer"
            >
              <span>{t('send')}</span>
              <Send size={14} />
            </button>
          </form>
        </div>
      </div>

      <TopupModal isOpen={isBillingModalOpen} onClose={() => { setIsBillingModalOpen(false); refreshUser(); }} />
      
      {showWikiModal && (
        <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4 backdrop-blur-sm animate-fadeIn">
          <div className="rounded-3xl w-full max-w-3xl max-h-[85vh] overflow-hidden flex flex-col shadow-2xl border border-emerald-500/20" style={{ backgroundColor: currentBg.panelBg }}>
            <div className="flex items-center justify-between p-4 sm:p-5 border-b border-emerald-500/10 bg-gradient-to-r from-emerald-800 to-teal-800 text-white">
              <h2 className="text-lg sm:text-xl font-bold flex items-center gap-2">
                <BookOpen size={20} className="text-emerald-300" /> {t('encyclopedia')}
              </h2>
              <button onClick={() => setShowWikiModal(false)} className="text-slate-300 hover:text-white bg-white/5 hover:bg-white/10 transition-colors rounded-full p-1.5 cursor-pointer">
                <X size={18} />
              </button>
            </div>
            
            <div className="p-4 sm:p-6 overflow-y-auto custom-scrollbar flex-1 bg-[#030705]/50">
                <div className="space-y-4 sm:space-y-6">
                  {wikiData.map((data, index) => (
                    <div key={index} className="bg-[#08150f]/80 p-5 rounded-2xl shadow-sm border border-emerald-500/10 hover:border-emerald-400 transition-colors duration-300">
                      <h3 className="text-base sm:text-lg font-black text-emerald-300 mb-2 pb-2 border-b border-emerald-500/5 flex items-center gap-1.5">
                        <span className="w-1.5 h-4 bg-emerald-500 rounded-full"></span>
                        {data.title}
                      </h3>
                      <p className="text-slate-300 leading-relaxed text-xs sm:text-sm text-justify whitespace-pre-line">
                        {data.extract}
                      </p>
                    </div>
                  ))}
                </div>
            </div>
          </div>
        </div>
      )}

      <style>{`
        @keyframes slideUp { from { opacity: 0; transform: translateY(20px) scale(0.95); } to { opacity: 1; transform: translateY(0) scale(1); } }
        @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
        .animate-slideUp { animation: slideUp 0.2s cubic-bezier(0.16, 1, 0.3, 1) forwards; }
        .animate-fadeIn { animation: fadeIn 0.3s ease-out forwards; }
        .custom-scrollbar::-webkit-scrollbar { width: 6px; }
        .custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
        .custom-scrollbar::-webkit-scrollbar-thumb { background-color: #0c2017; border-radius: 20px; }
        .pb-safe { padding-bottom: env(safe-area-inset-bottom, 16px); } /* Hỗ trợ tai thỏ/thanh điều hướng Mobile */
      `}</style>
    </div>
  );
};

export default ChatView;