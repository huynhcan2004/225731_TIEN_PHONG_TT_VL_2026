import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Bot, User, Leaf, Sparkles, Globe, RefreshCw } from 'lucide-react';
import { useLanguageTheme } from '../../context/LanguageThemeContext';
import toast from 'react-hot-toast';

interface Props {
  role: 'user' | 'assistant'; 
  content: string;
  metadata?: any;
  intent?: string;
  modelUsed?: string;
  execTime?: number;
}

const isVietnamese = (text: string): boolean => {
  const vnRegex = /[àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ]/i;
  return vnRegex.test(text);
};

const MessageItem: React.FC<Props> = ({ role, content, metadata }) => {
  const isBot = role === 'assistant';
  const { language } = useLanguageTheme();
  
  const [translatedContent, setTranslatedContent] = useState<string>('');
  const [isTranslating, setIsTranslating] = useState<boolean>(false);
  const [showTranslation, setShowTranslation] = useState<boolean>(false);

  const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

  const msgIsVn = isVietnamese(content);
  const targetLang = msgIsVn ? 'en' : 'vi';

  const handleTranslate = async () => {
    if (showTranslation) {
      setShowTranslation(false);
      return;
    }

    if (translatedContent) {
      setShowTranslation(true);
      return;
    }

    setIsTranslating(true);
    const token = localStorage.getItem('access_token');
    try {
      const response = await fetch(`${API_URL}/chatbot/translate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          text: content,
          target_lang: targetLang
        })
      });

      const data = await response.json();
      if (response.ok) {
        setTranslatedContent(data.translated_text);
        setShowTranslation(true);
      } else {
        toast.error(data.detail || (language === 'vi' ? 'Dịch thuật thất bại.' : 'Translation failed.'));
      }
    } catch (error) {
      console.error("Lỗi dịch tin nhắn:", error);
      toast.error(language === 'vi' ? 'Không thể kết nối đến máy chủ để dịch.' : 'Could not connect to translation server.');
    } finally {
      setIsTranslating(false);
    }
  };

  return (
    <div className={`flex gap-4 p-5 sm:p-6 transition-all duration-300 ${
      isBot 
        ? 'bg-emerald-950/10 border-y border-emerald-500/10 shadow-[0_4px_25px_rgba(27,137,97,0.03)] hover:bg-emerald-950/15' 
        : 'bg-transparent'
    }`}>
      {/* Avatar dạng Cybernetic-Node với tông màu YHCT */}
      <div className={`w-9 h-9 rounded-xl flex items-center justify-center shrink-0 transition-all duration-300 hover:scale-105 ${
        isBot 
          ? 'bg-gradient-to-br from-emerald-600 via-teal-600 to-amber-500 text-white shadow-[0_0_15px_rgba(27,137,97,0.3)] border border-emerald-400/20' 
          : 'bg-emerald-950/30 text-emerald-400 border border-emerald-500/20 shadow-[0_0_8px_rgba(27,137,97,0.05)]'
      }`}>
        {isBot ? <Sparkles size={16} className="animate-pulse" /> : <User size={16} />}
      </div>

      <div className="flex-1 min-w-0 space-y-3">
        {/* Render nội dung y khoa bằng Markdown với prose-invert */}
        <div className="prose prose-emerald prose-invert max-w-none text-emerald-50/90 text-sm sm:text-base leading-relaxed tracking-wide">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {showTranslation ? translatedContent : content}
          </ReactMarkdown>
        </div>

        {/* Action Bar (Translate Button) */}
        {isBot && (
          <div className="flex items-center gap-3 mt-2 no-prose">
            <button
              onClick={handleTranslate}
              disabled={isTranslating}
              className="flex items-center gap-1.5 text-emerald-500/60 hover:text-emerald-400 text-xs font-semibold transition-colors disabled:opacity-50 cursor-pointer"
              title={language === 'vi' ? 'Dịch tin nhắn' : 'Translate message'}
            >
              {isTranslating ? (
                <RefreshCw className="w-3.5 h-3.5 animate-spin text-emerald-400" />
              ) : (
                <Globe className={`w-3.5 h-3.5 ${showTranslation ? 'text-emerald-400' : 'text-emerald-500/60'}`} />
              )}
              <span>
                {isTranslating 
                  ? (language === 'vi' ? 'Đang dịch...' : 'Translating...') 
                  : (showTranslation 
                      ? (language === 'vi' ? 'Xem bản gốc' : 'Show original') 
                      : (targetLang === 'en'
                          ? (language === 'vi' ? 'Dịch sang Tiếng Anh' : 'Translate to English')
                          : (language === 'vi' ? 'Dịch sang Tiếng Việt' : 'Translate to Vietnamese')
                        )
                    )
                }
              </span>
            </button>
            
            {showTranslation && (
              <span className="text-[9px] bg-emerald-500/10 text-emerald-400 px-2 py-0.5 rounded font-black uppercase tracking-wider">
                {language === 'vi' ? 'Bản dịch AI' : 'AI Translated'}
              </span>
            )}
          </div>
        )}

        {/* THẺ TÓM TẮT THỰC THỂ (Nếu AI kích hoạt Graph) - Tông màu Hổ Phách/Đồng YHCT */}
        {isBot && metadata?.plant_name && (
          <div className="inline-flex items-center gap-2 bg-amber-950/40 border border-amber-500/35 hover:border-amber-400 text-amber-300 px-4 py-1.5 rounded-full text-xs font-bold mt-2 shadow-[0_0_12px_rgba(193,160,89,0.08)] hover:-translate-y-0.5 active:translate-y-0 transition-all duration-300 cursor-pointer">
            <Leaf size={13} className="text-emerald-400 animate-bounce" style={{ animationDuration: '3s' }} />
            <span className="text-emerald-400 font-medium">
              {language === 'vi' ? 'Thực thể nhận diện:' : 'Recognized entity:'}
            </span>
            <span className="text-amber-300 font-black tracking-wide">{metadata.plant_name}</span>
          </div>
        )}
      </div>
    </div>
  );
};

export default MessageItem;