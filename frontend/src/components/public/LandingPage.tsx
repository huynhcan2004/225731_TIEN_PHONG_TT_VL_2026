import React from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { useSiteSettings } from '../../context/SiteSettingsContext';
import { useLanguageTheme } from '../../context/LanguageThemeContext';
import { 
  Leaf, 
  MessageSquare, 
  Share2, 
  Search, 
  BookOpen, 
  ShieldCheck, 
  Zap, 
  ArrowRight, 
  HelpCircle,
  Database,
  Cpu,
  Coins
} from 'lucide-react';

const LandingPage: React.FC = () => {
  const { user } = useAuth();
  const { siteTitle, siteLogo } = useSiteSettings();
  const { language, setLanguage, currentBg, t } = useLanguageTheme();

  const renderLogo = (className = "w-6 h-6") => {
    if (siteLogo) {
      return <img src={siteLogo} alt="Logo" className={className} />;
    }
    return <Leaf className={`text-[#a3c9a8] ${className}`} />;
  };

  const features = [
    {
      icon: Cpu,
      title: t('feat1Title'),
      description: t('feat1Desc')
    },
    {
      icon: BookOpen,
      title: t('feat2Title'),
      description: t('feat2Desc')
    },
    {
      icon: Share2,
      title: t('feat3Title'),
      description: t('feat3Desc')
    },
    {
      icon: ShieldCheck,
      title: t('feat4Title'),
      description: t('feat4Desc')
    }
  ];

  const steps = [
    {
      num: "01",
      title: t('step1Title'),
      desc: t('step1Desc')
    },
    {
      num: "02",
      title: t('step2Title'),
      desc: t('step2Desc')
    },
    {
      num: "03",
      title: t('step3Title'),
      desc: t('step3Desc')
    }
  ];

  return (
    <div className="min-h-screen text-slate-100 font-sans selection:bg-emerald-500 selection:text-white overflow-x-hidden transition-colors duration-300" style={{ backgroundColor: currentBg.bodyBg }}>
      {/* Background decoration - Ẩn trên giao diện trắng để tránh bị xanh lè dơ bẩn */}
      {!currentBg.isLight && (
        <>
          <div className="absolute top-0 left-1/4 w-96 h-96 bg-emerald-500/10 rounded-full blur-3xl -z-10 animate-pulse" />
          <div className="absolute top-1/3 right-1/4 w-[400px] h-[400px] bg-teal-500/5 rounded-full blur-3xl -z-10" />
        </>
      )}

      {/* Header */}
      <header className="sticky top-0 z-50 backdrop-blur-md border-b border-emerald-500/10 shadow-sm transition-colors duration-300" style={{ backgroundColor: currentBg.panelBg + 'cc' }}>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl flex items-center justify-center shadow-lg border border-emerald-500/10" style={{ backgroundColor: currentBg.bodyBg }}>
              {renderLogo("w-5.5 h-5.5")}
            </div>
            <div>
              <span className="font-black text-lg tracking-tight text-white">
                {siteTitle}
              </span>
              <span className="hidden sm:inline-block ml-2 px-2 py-0.5 bg-emerald-950 text-emerald-400 text-[10px] font-bold rounded-full border border-emerald-500/20">
                GraphRAG Portal
              </span>
            </div>
          </div>

          <div className="flex items-center gap-4">
            <Link 
              to="/privacy-policy" 
              className="hidden md:inline-block text-xs font-semibold text-slate-400 hover:text-white transition-colors"
            >
              {t('landingDocLink')}
            </Link>
            
            {/* Language Toggle */}
            <button
              onClick={() => setLanguage(language === 'vi' ? 'en' : 'vi')}
              className="flex items-center gap-1.5 bg-emerald-950/20 hover:bg-emerald-950/40 py-1.5 px-3 rounded-full border border-emerald-500/10 hover:border-emerald-500/30 text-xs font-bold text-emerald-400 transition-all cursor-pointer shadow-sm hover:shadow-md"
            >
              <span>{language === 'vi' ? '🇻🇳 VI' : '🇬🇧 EN'}</span>
            </button>

            <Link 
              to={user ? "/chat" : "/login"} 
              className="flex items-center gap-1.5 px-4.5 py-2 text-xs font-bold text-white no-light-override bg-emerald-600 hover:bg-emerald-500 rounded-xl transition-all duration-200 shadow-md shadow-emerald-950/20 hover:scale-[1.02]"
            >
              <span className="no-light-override">{user ? t('landingChatBtn') : t('landingLoginBtn')}</span>
              <ArrowRight className="w-3.5 h-3.5 no-light-override" />
            </Link>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-20 pb-24 text-center lg:text-left flex flex-col lg:flex-row items-center justify-between gap-12">
        <div className="max-w-2xl space-y-6 lg:w-1/2">
          <div className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-emerald-950/50 text-emerald-400 text-xs font-bold rounded-full border border-emerald-500/20 mb-2">
            <Zap className="w-3.5 h-3.5 text-emerald-400 animate-bounce" />
            <span>{t('landingBadge')}</span>
          </div>
          
          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-black text-white tracking-tight leading-tight">
            {t('landingHeroTitle1')} <br />
            <span className="bg-gradient-to-r from-emerald-400 to-teal-300 bg-clip-text text-transparent">{t('landingHeroTitle2')}</span> <br />
            {t('landingHeroTitle3')}
          </h1>
          
          <p className="text-slate-400 text-sm sm:text-base leading-relaxed font-medium">
            {t('landingHeroDesc').replace('{siteTitle}', siteTitle)}
          </p>

          <div className="flex flex-col sm:flex-row items-center gap-4 pt-4 justify-center lg:justify-start">
            <Link 
              to={user ? "/chat" : "/login"} 
              className="w-full sm:w-auto flex items-center justify-center gap-2 px-8 py-4 bg-emerald-600 hover:bg-emerald-500 text-white no-light-override font-bold rounded-2xl shadow-lg shadow-emerald-900/30 hover:shadow-xl transition-all duration-200 hover:-translate-y-0.5 cursor-pointer text-sm"
            >
              <span className="no-light-override">{t('landingStartBtn')}</span>
              <MessageSquare className="w-4 h-4 no-light-override" />
            </Link>
            
            <Link 
              to="/privacy-policy" 
              className="w-full sm:w-auto flex items-center justify-center gap-2 px-8 py-4 bg-emerald-950/10 hover:bg-emerald-950/20 text-slate-200 font-bold rounded-2xl border border-emerald-500/10 transition-all duration-200 cursor-pointer text-sm"
            >
              <span>{t('landingPolicyBtn')}</span>
              <HelpCircle className="w-4 h-4" />
            </Link>
          </div>
        </div>

        {/* Hero Interactive Graph Graphics */}
        <div className="lg:w-1/2 flex items-center justify-center relative select-none">
          <div className="w-80 h-80 sm:w-[450px] sm:h-[450px] rounded-full bg-emerald-500/5 border-2 border-dashed border-emerald-500/10 flex items-center justify-center animate-spin duration-100000">
            {/* Dynamic CSS Connecting Graph Network Graphic */}
            <div className="absolute w-[80%] h-[80%] rounded-full border border-teal-500/10" />
            <div className="absolute w-[60%] h-[60%] rounded-full border border-emerald-500/10 animate-reverseSpin" />
          </div>

          {/* Floating Graph Nodes */}
          <div className="absolute w-24 h-24 sm:w-28 sm:h-28 rounded-2xl border border-emerald-500/20 flex flex-col items-center justify-center shadow-2xl p-3 animate-bounce shadow-emerald-950/40" style={{ backgroundColor: currentBg.panelBg }}>
            <div className="w-8 h-8 rounded-lg bg-emerald-500/15 text-emerald-400 flex items-center justify-center mb-1">
              <Database className="w-4 h-4" />
            </div>
            <span className="text-[10px] font-bold text-emerald-400 uppercase tracking-widest">Neo4j Graph</span>
            <span className="text-[9px] text-slate-400 mt-0.5 font-medium">10,000+ Nodes</span>
          </div>

          <div className="absolute top-8 right-8 w-20 h-20 backdrop-blur-md rounded-2xl border border-emerald-500/10 flex flex-col items-center justify-center shadow-xl p-2.5 hover:scale-105 transition-all" style={{ backgroundColor: currentBg.panelBg + 'cc' }}>
            <span className="text-[9px] font-black text-emerald-400 uppercase">GraphRAG</span>
            <span className="text-[8px] text-slate-400 text-center leading-tight mt-1">
              {language === 'vi' ? 'Đối sánh thực thể thực tế' : 'Entity cross-referencing'}
            </span>
          </div>

          <div className="absolute bottom-8 left-8 w-24 h-24 backdrop-blur-md rounded-2xl border border-emerald-500/10 flex flex-col items-center justify-center shadow-xl p-2.5 hover:scale-105 transition-all" style={{ backgroundColor: currentBg.panelBg + 'cc' }}>
            <Coins className="w-5 h-5 text-amber-400 mb-1" />
            <span className="text-[8px] font-black text-amber-400 uppercase">
              {language === 'vi' ? 'Đối Soát Ví' : 'Wallet Sync'}
            </span>
            <span className="text-[8px] text-slate-400 text-center leading-tight mt-0.5">
              {language === 'vi' ? 'SePay QR Động' : 'Dynamic SePay QR'}
            </span>
          </div>
        </div>
      </section>

      {/* Features Grid Section */}
      <section className="border-y border-emerald-500/10 py-24 transition-colors duration-300" style={{ backgroundColor: currentBg.bodyBg === '#ffffff' || currentBg.isLight ? 'rgba(0,0,0,0.015)' : 'rgba(0,0,0,0.15)' }}>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-3xl mx-auto mb-16 space-y-4">
            <h2 className="text-xs font-bold text-emerald-400 uppercase tracking-widest">{t('landingFeatureBadge')}</h2>
            <p className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight">
              {t('landingFeatureTitle')}{siteTitle}
            </p>
            <p className="text-slate-400 text-sm">
              {t('landingFeatureSub')}
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            {features.map((feat, index) => {
              const Icon = feat.icon;
              return (
                <div key={index} className="p-8 border border-emerald-500/10 hover:border-emerald-500/30 rounded-3xl transition-all duration-200 hover:-translate-y-1 shadow-md hover:shadow-emerald-950/10 flex gap-5 items-start transition-colors duration-300" style={{ backgroundColor: currentBg.panelBg }}>
                  <div className="p-3 bg-[#2c4a3e]/30 text-emerald-400 rounded-xl shadow-inner shrink-0">
                    <Icon className="w-6 h-6" />
                  </div>
                  <div className="space-y-2">
                    <h3 className="text-lg font-black text-white">{feat.title}</h3>
                    <p className="text-slate-400 text-xs leading-relaxed">{feat.description}</p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* How it Works Section */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-24">
        <div className="text-center max-w-3xl mx-auto mb-16 space-y-4">
          <h2 className="text-xs font-bold text-emerald-400 uppercase tracking-widest">{t('landingStepBadge')}</h2>
          <p className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight">{t('landingStepTitle')}</p>
          <p className="text-slate-400 text-sm">{t('landingStepSub')}</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 relative">
          {/* Connecting line */}
          <div className="hidden md:block absolute top-1/2 left-20 right-20 h-0.5 bg-gradient-to-r from-emerald-500/20 via-teal-500/20 to-emerald-500/20 -translate-y-12 -z-10" />

          {steps.map((step, index) => (
            <div key={index} className="p-8 border border-emerald-500/10 rounded-3xl shadow-sm text-center space-y-4 hover:border-emerald-500/20 transition-all relative transition-colors duration-300" style={{ backgroundColor: currentBg.panelBg + 'cc' }}>
              <span className="absolute -top-6 left-1/2 -translate-x-1/2 w-12 h-12 bg-slate-950 border-2 border-emerald-500 rounded-full flex items-center justify-center font-black text-emerald-400 text-sm">
                {step.num}
              </span>
              <div className="pt-4 space-y-2">
                <h3 className="text-base font-black text-white">{step.title}</h3>
                <p className="text-slate-400 text-xs leading-relaxed">{step.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Dynamic CTA Banner */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pb-24">
        <div className="p-8 sm:p-12 rounded-[2.5rem] border border-emerald-500/10 text-center space-y-6 relative overflow-hidden shadow-2xl transition-all duration-300" style={{ backgroundImage: `linear-gradient(135deg, ${currentBg.panelBg}, ${currentBg.bodyBg})` }}>
          <div className="absolute top-0 right-0 w-80 h-80 bg-emerald-500/5 rounded-full blur-2xl -z-10" />
          <h2 className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight">
            {t('landingCtaTitle')}
          </h2>
          <p className="text-slate-350 text-xs sm:text-sm max-w-lg mx-auto leading-relaxed">
            {t('landingCtaSub')}
          </p>
          <div className="pt-2">
            <Link 
              to={user ? "/chat" : "/login"} 
              className="inline-flex items-center gap-2 px-8 py-4 bg-emerald-600 hover:bg-emerald-500 text-white no-light-override font-bold rounded-2xl shadow-lg transition-all duration-200 hover:-translate-y-0.5 text-sm cursor-pointer"
            >
              <span className="no-light-override">{t('landingCtaBtn')}</span>
              <ArrowRight className="w-4 h-4 no-light-override" />
            </Link>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="text-slate-500 py-12 border-t border-emerald-500/10 transition-colors duration-300" style={{ backgroundColor: currentBg.bodyBg === '#ffffff' || currentBg.isLight ? 'rgba(0,0,0,0.02)' : 'rgba(0,0,0,0.2)' }}>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col md:flex-row items-center justify-between gap-6">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg flex items-center justify-center border border-emerald-500/10" style={{ backgroundColor: currentBg.panelBg }}>
              {renderLogo("w-4.5 h-4.5")}
            </div>
            <div>
              <span className="font-bold text-sm tracking-tight text-white">
                {siteTitle}
              </span>
              <span className="block text-[10px] text-slate-600">Knowledge Graph & GraphRAG</span>
            </div>
          </div>

          <div className="flex flex-wrap justify-center gap-x-6 gap-y-2 text-xs">
            <Link to="/privacy-policy" className="hover:text-white transition-colors">{t('privacy')}</Link>
            <Link to="/terms-of-service" className="hover:text-white transition-colors">{t('terms')}</Link>
            <Link to="/data-deletion" className="hover:text-white transition-colors">{t('dataDeletion')}</Link>
            <Link to="/support" className="hover:text-white transition-colors">{t('support')}</Link>
            <Link to="/contact" className="hover:text-white transition-colors">{t('contact')}</Link>
          </div>

          <div className="text-[10px] text-slate-600 text-center md:text-right">
            &copy; {new Date().getFullYear()} {siteTitle}. All rights reserved. <br />
            {t('landingFooterDesc')}
          </div>
        </div>
      </footer>
    </div>
  );
};

export default LandingPage;
