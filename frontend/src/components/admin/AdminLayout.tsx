import React, { useState } from 'react';
import { NavLink, Outlet, useNavigate, Link } from 'react-router-dom';
import { 
    LayoutDashboard, 
    Users, 
    Wallet, 
    Network, 
    Settings, 
    LogOut, 
    Menu, 
    Leaf,
    MessageSquare
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { useLanguageTheme, BG_THEMES, BgColor } from '../../context/LanguageThemeContext';
import { useSiteSettings } from '../../context/SiteSettingsContext';

export const AdminLayout = () => {
    const [isSidebarOpen, setSidebarOpen] = useState(true);
    const { user, logout } = useAuth();
    const navigate = useNavigate();
    const { language, setLanguage, bgColor, setBgColor, currentBg, t } = useLanguageTheme();
    const { siteTitle, siteLogo } = useSiteSettings();

    const menuItems = [
        { path: '/admin', name: t('systemOverview'), icon: LayoutDashboard },
        { path: '/admin/seo', name: t('syncKnowledge'), icon: Network },
        { path: '/admin/finance', name: t('transactions'), icon: Wallet },
        { path: '/admin/users', name: t('userManagement'), icon: Users },
        { path: '/admin/settings', name: t('aiConfig'), icon: Settings },
    ];

    const handleLogout = () => {
        logout();
    };

    return (
        <div className="flex h-screen text-slate-100 overflow-hidden font-sans relative" style={{ backgroundColor: currentBg.bodyBg }}>
            
            {/* Cyber Grid Background */}
            <div className="absolute inset-0 opacity-[0.02] pointer-events-none z-0" 
                 style={{ backgroundImage: 'radial-gradient(#10b981 1px, transparent 1px)', backgroundSize: '32px 32px' }}>
            </div>

            {/* --- SIDEBAR --- */}
            <aside 
                className={`backdrop-blur-md text-white transition-all duration-300 ease-in-out flex flex-col shadow-2xl z-20 border-r border-emerald-500/10
                ${isSidebarOpen ? 'w-64' : 'w-20'} relative z-10`}
                style={{ backgroundColor: currentBg.panelBg }}
            >
                <div className="flex items-center justify-center h-20 border-b border-emerald-500/10">
                    <Link to="/" className="flex items-center hover:opacity-90 transition-opacity">
                        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-emerald-500 via-teal-500 to-amber-500 flex items-center justify-center shadow-lg shadow-emerald-500/15 border border-emerald-400/20 shrink-0">
                            {siteLogo ? (
                                <img src={siteLogo} alt="Logo" className="w-6 h-6 object-contain rounded-lg" />
                            ) : (
                                <Leaf className="w-5 h-5 text-white" />
                            )}
                        </div>
                        {isSidebarOpen && (
                            <span className="ml-3 text-sm font-black tracking-wide text-transparent bg-clip-text bg-gradient-to-r from-emerald-100 via-teal-100 to-amber-100 truncate pr-2">
                                {siteTitle}
                            </span>
                        )}
                    </Link>
                </div>

                {/* Navigation Links */}
                <nav className="flex-1 px-3 py-6 space-y-1.5 overflow-y-auto custom-scrollbar">
                    {/* Nút quay lại màn hình Chat (Ai cũng thấy) */}
                    <NavLink
                        to="/chat"
                        className="flex items-center px-3 py-3 mb-4 rounded-xl text-emerald-400/70 hover:bg-emerald-950/20 hover:text-emerald-300 transition-all border border-emerald-500/10 group"
                    >
                        <MessageSquare className="w-5 h-5 flex-shrink-0" />
                        {isSidebarOpen && <span className="ml-3 font-semibold text-sm">{t('backToChatbot')}</span>}
                    </NavLink>

                    <div className="h-px bg-emerald-500/10 mx-2 mb-4"></div>

                    {/* Menu Admin */}
                    {menuItems.map((item) => (
                        <NavLink
                            key={item.path}
                            to={item.path}
                            end={item.path === '/admin'} 
                            className={({ isActive }) =>
                                `flex items-center px-3 py-3 rounded-xl transition-all duration-200 group relative overflow-hidden border
                                ${isActive 
                                    ? 'bg-gradient-to-r from-emerald-600 via-teal-600 to-amber-500 text-white shadow-lg shadow-emerald-500/10 border-emerald-400/35' 
                                    : 'text-emerald-500/50 hover:bg-emerald-950/20 hover:text-emerald-300 border-transparent'}`
                            }
                        >
                            {({ isActive }) => (
                                <>
                                    <item.icon className="w-5 h-5 flex-shrink-0 relative z-10 transition-transform group-hover:scale-110" />
                                    {isSidebarOpen && <span className="ml-3 font-semibold text-sm relative z-10">{item.name}</span>}
                                    
                                    {/* Hiệu ứng thanh dọc bên trái khi đang chọn */}
                                    {isActive && (
                                        <div className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-8 bg-amber-400 rounded-r-md"></div>
                                    )}
                                </>
                            )}
                        </NavLink>
                    ))}
                </nav>

                {/* User Info & Logout */}
                <div className="p-4 border-t border-emerald-500/10 z-10" style={{ backgroundColor: currentBg.bodyBg }}>
                    {isSidebarOpen && (
                        <div className="flex items-center mb-4 px-2">
                            <div className="w-8 h-8 rounded-full bg-emerald-950 border border-emerald-500/30 text-emerald-300 flex items-center justify-center font-bold text-xs">
                                {user?.username?.charAt(0).toUpperCase() || 'A'}
                            </div>
                            <div className="ml-3 overflow-hidden">
                                <p className="text-sm font-bold text-emerald-50 truncate">{user?.username}</p>
                                <p className="text-[10px] text-emerald-500/60 font-mono uppercase tracking-widest">{user?.role}</p>
                            </div>
                        </div>
                    )}
                    <button 
                        onClick={handleLogout}
                        className={`flex items-center w-full px-3 py-2.5 text-rose-400/70 rounded-xl hover:bg-rose-950/30 hover:text-rose-400 transition-colors border border-rose-500/10 hover:border-rose-500/30 cursor-pointer
                        ${!isSidebarOpen && 'justify-center'}`}
                    >
                        <LogOut className="w-5 h-5 flex-shrink-0" />
                        {isSidebarOpen && <span className="ml-3 font-semibold text-sm">{t('logout')}</span>}
                    </button>
                </div>
            </aside>

            {/* --- MAIN CONTENT --- */}
            <main className="flex-1 flex flex-col h-screen overflow-hidden relative z-10 bg-transparent">
                {/* Header (Topbar) */}
                <header className="flex items-center justify-between px-6 h-20 border-b border-emerald-500/10 shadow-lg shadow-black/10 z-10" style={{ backgroundColor: currentBg.panelBg + 'cc' }}>
                    <button 
                        onClick={() => setSidebarOpen(!isSidebarOpen)}
                        className="p-2 rounded-xl bg-emerald-950/30 hover:bg-emerald-950/50 text-emerald-400 hover:text-emerald-300 transition-colors border border-emerald-500/20 cursor-pointer"
                    >
                        <Menu className="w-5 h-5" />
                    </button>
                    
                    <div className="flex items-center space-x-3.5 z-10">
                        {/* Theme Selector Dropdown */}
                        <div className="relative">
                            <select
                                value={bgColor}
                                onChange={(e) => setBgColor(e.target.value as BgColor)}
                                className="px-3 py-2 rounded-xl bg-emerald-950/30 hover:bg-emerald-950/50 text-emerald-400 border border-emerald-500/20 text-xs font-bold transition-all cursor-pointer shadow-sm outline-none focus:border-emerald-400/50 hover:border-emerald-500/40"
                            >
                                {Object.values(BG_THEMES).map((theme) => (
                                    <option key={theme.id} value={theme.id} className="bg-slate-900 text-slate-100">
                                        {language === 'vi' ? theme.nameVi : theme.nameEn}
                                    </option>
                                ))}
                            </select>
                        </div>

                        {/* Language Toggle Button */}
                        <button
                            onClick={() => setLanguage(language === 'vi' ? 'en' : 'vi')}
                            className="px-3.5 py-2 rounded-xl bg-emerald-950/30 hover:bg-emerald-950/50 text-emerald-400 hover:text-emerald-300 border border-emerald-500/20 text-xs font-black transition-all flex items-center space-x-1.5 cursor-pointer shadow-sm hover:border-emerald-500/40"
                        >
                            <span>{language === 'vi' ? '🇻🇳 VI' : '🇬🇧 EN'}</span>
                        </button>

                        {/* Date and Admin Section Label */}
                        <div className="text-right hidden md:block pl-2 border-l border-emerald-500/10">
                            <p className="text-sm font-black text-emerald-50">{t('adminSection')}</p>
                            <p className="text-[10px] font-bold text-emerald-400/70 mt-0.5">
                                {new Date().toLocaleDateString(language === 'vi' ? 'vi-VN' : 'en-US', { weekday: 'short', year: 'numeric', month: 'short', day: 'numeric' })}
                            </p>
                        </div>
                    </div>
                </header>

                {/* Dynamic Content (Outlet) */}
                <div className="flex-1 overflow-auto p-8 relative scroll-smooth custom-scrollbar">
                    <div className="relative z-10 max-w-7xl mx-auto">
                        <Outlet />
                    </div>
                </div>
            </main>
        </div>
    );
};