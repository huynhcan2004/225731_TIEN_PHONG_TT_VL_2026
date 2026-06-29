import React, { useEffect, useState } from 'react';
import { Activity, Coins, BrainCircuit, Users, Loader2, ArrowUpRight,Wallet, } from 'lucide-react';
import { useLanguageTheme } from '../../context/LanguageThemeContext';

export const AdminDashboard = () => {
    const [data, setData] = useState<any>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [daysRange, setDaysRange] = useState(7);
    const { language, t } = useLanguageTheme();

    useEffect(() => {
        const fetchStats = async () => {
            try {
                const token = localStorage.getItem('access_token'); 
                const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
                
                const response = await fetch(`${API_URL}/admin/dashboard-stats?days=${daysRange}`, {
                    headers: { 'Authorization': `Bearer ${token}` }
                });
                
                if (response.ok) {
                    const result = await response.json();
                    setData(result);
                } else {
                    setError(language === 'vi' ? "Không thể tải dữ liệu thống kê." : "Failed to load dashboard statistics.");
                }
            } catch (err) {
                setError(language === 'vi' ? "Lỗi kết nối tới máy chủ." : "Server connection error.");
            } finally {
                setLoading(false);
            }
        };

        fetchStats();
    }, [language, daysRange]);

    if (loading) {
        return (
            <div className="flex flex-col items-center justify-center h-[60vh] text-[#2c4a3e]">
                <div className="relative">
                    <Loader2 className="w-12 h-12 animate-spin mb-4 opacity-20" />
                    <Loader2 className="w-12 h-12 animate-spin mb-4 absolute top-0 left-0 text-emerald-500" style={{ animationDirection: 'reverse', animationDuration: '3s' }} />
                </div>
                <p className="font-bold tracking-widest uppercase text-sm animate-pulse text-emerald-700">
                    {language === 'vi' ? 'Đang đồng bộ GraphRAG...' : 'Syncing GraphRAG...'}
                </p>
            </div>
        );
    }

    if (error) {
        return (
            <div className="bg-red-50 text-red-600 p-6 rounded-2xl border border-red-100 flex items-center justify-center">
                <p className="font-bold">{error}</p>
            </div>
        );
    }

    const stats = [
        { 
            title: t('revenueSepay'), 
            value: `${data?.total_revenue?.toLocaleString('vi-VN') || 0} đ`, 
            subValue: t('realMoney'),
            icon: Coins, 
            color: 'text-amber-500', 
            bg: 'bg-gradient-to-br from-amber-500/10 to-amber-700/20',
            border: 'border-amber-500/20'
        },
        { 
            title: t('aiQueries'), 
            value: data?.total_queries?.toLocaleString('vi-VN') || 0, 
            subValue: t('historyQueries'),
            icon: BrainCircuit, 
            color: 'text-emerald-400', 
            bg: 'bg-gradient-to-br from-emerald-500/10 to-emerald-700/20',
            border: 'border-emerald-500/20'
        },
        { 
            title: t('graphEntities'), 
            value: data?.total_nodes?.toLocaleString('vi-VN') || 0, 
            subValue: t('nodesInNeo4j'),
            icon: Activity, 
            color: 'text-emerald-400', 
            bg: 'bg-gradient-to-br from-emerald-500/10 to-emerald-700/20',
            border: 'border-emerald-500/20'
        },
        { 
            title: t('users'), 
            value: data?.total_users?.toLocaleString('vi-VN') || 0, 
            subValue: t('systemAccounts'),
            icon: Users, 
            color: 'text-amber-500', 
            bg: 'bg-gradient-to-br from-amber-500/10 to-amber-700/20',
            border: 'border-amber-500/20'
        },
    ];

    // --- BIỂU ĐỒ DỮ LIỆU ĐỘNG ---
    const dailyQueries = data?.daily_queries || [];
    const counts = dailyQueries.map((d: any) => d.count);
    const maxVal = counts.length > 0 ? Math.max(...counts, 5) : 5;
    
    const svgWidth = 500;
    const svgHeight = 150;
    const paddingY = 25;
    const chartHeight = svgHeight - paddingY * 2;
    
    const points = dailyQueries.map((item: any, idx: number) => {
        const x = dailyQueries.length > 1 ? (idx / (dailyQueries.length - 1)) * svgWidth : svgWidth / 2;
        const y = svgHeight - paddingY - (item.count / maxVal) * chartHeight;
        return { x, y };
    });
    
    let pathD = "";
    if (points.length > 0) {
        pathD = `M ${points[0].x},${points[0].y}`;
        for (let i = 1; i < points.length; i++) {
            const cpX1 = points[i-1].x + (points[i].x - points[i-1].x) / 2;
            const cpY1 = points[i-1].y;
            const cpX2 = points[i-1].x + (points[i].x - points[i-1].x) / 2;
            const cpY2 = points[i].y;
            pathD += ` C ${cpX1},${cpY1} ${cpX2},${cpY2} ${points[i].x},${points[i].y}`;
        }
    }
    
    const fillD = pathD ? `${pathD} L ${svgWidth},${svgHeight} L 0,${svgHeight} Z` : "";

    const getWeekdayLabel = (dateStr: string) => {
        const date = new Date(dateStr);
        const day = date.getDay();
        if (language === 'vi') {
            const viDays = ["CN", "T2", "T3", "T4", "T5", "T6", "T7"];
            return viDays[day];
        } else {
            const enDays = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
            return enDays[day];
        }
    };

    const formatDateLabel = (dateStr: string) => {
        const parts = dateStr.split('-');
        if (parts.length === 3) {
            return `${parts[2]}/${parts[1]}`;
        }
        const date = new Date(dateStr);
        const day = date.getDate().toString().padStart(2, '0');
        const month = (date.getMonth() + 1).toString().padStart(2, '0');
        return `${day}/${month}`;
    };

    const shouldShowLabel = (idx: number) => {
        if (dailyQueries.length <= 7) return true;
        return idx % 5 === 0 || idx === dailyQueries.length - 1;
    };

    return (
        <div className="space-y-8 animate-fadeIn relative">
            
            {/* Tiêu đề trang */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between border-b border-emerald-500/10 pb-5 gap-4">
                <div>
                    <h1 className="text-3xl font-black text-slate-100 tracking-tight">
                        {language === 'vi' ? <>Tổng quan <span className="text-transparent bg-clip-text bg-gradient-to-r from-emerald-400 via-teal-400 to-amber-400">Hệ thống</span></> : <>System <span className="text-transparent bg-clip-text bg-gradient-to-r from-emerald-400 via-teal-400 to-amber-400">Overview</span></>}
                    </h1>
                    <p className="text-slate-400 font-medium mt-1">{t('overviewSub')}</p>
                </div>
                <button className="self-start sm:self-auto flex items-center gap-2 bg-[#060e0a]/80 border border-emerald-500/20 text-slate-300 px-4 py-2.5 rounded-xl text-sm font-bold shadow-sm hover:border-emerald-400 hover:text-emerald-100 active:scale-98 transition-all duration-200 cursor-pointer">
                    {t('exportReport')} <ArrowUpRight className="w-4 h-4" />
                </button>
            </div>

            {/* Khối Thống kê - Giao diện Cyber-Card */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                {stats.map((stat, idx) => (
                    <div 
                        key={idx} 
                        className={`bg-[#060e0a]/80 backdrop-blur-sm rounded-3xl p-6 shadow-[0_8px_30px_rgba(0,0,0,0.2)] hover:shadow-[0_0_20px_rgba(16,185,129,0.1)] hover:-translate-y-1 border border-emerald-500/10 hover:border-emerald-500/30 transition-all duration-300 relative overflow-hidden group`}
                    >
                        <div className={`absolute -right-6 -top-6 w-32 h-32 rounded-full ${stat.bg} opacity-20 group-hover:scale-150 transition-transform duration-700 ease-in-out`}></div>
                        
                        <div className="relative z-10 flex flex-col h-full justify-between space-y-5">
                            <div className="flex justify-between items-start">
                                <div className={`p-3 rounded-2xl ${stat.bg} shadow-inner border border-emerald-500/10`}>
                                    <stat.icon className={`w-5 h-5 ${stat.color}`} />
                                </div>
                                <span className="bg-emerald-950/40 border border-emerald-500/20 text-[10px] font-black text-emerald-400 uppercase tracking-wider px-2.5 py-1 rounded-full shadow-sm">
                                    {stat.subValue}
                                </span>
                            </div>
                            
                            <div>
                                <h3 className="text-2xl sm:text-3xl font-black text-slate-100 tracking-tight">{stat.value}</h3>
                                <p className="text-xs sm:text-sm font-bold text-emerald-500/50 mt-1">{stat.title}</p>
                            </div>
                        </div>
                    </div>
                ))}
            </div>

            {/* Khối Biểu đồ & Bảng dữ liệu */}
            <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
                
                {/* Khu vực Biểu đồ */}
                <div className="xl:col-span-2 bg-[#060e0a]/80 backdrop-blur-sm rounded-3xl shadow-[0_8px_30px_rgba(0,0,0,0.2)] border border-emerald-500/10 p-6 sm:p-8 h-[440px] flex flex-col relative overflow-hidden">
                    <div className="flex items-center justify-between mb-4">
                        <div>
                          <h3 className="text-lg sm:text-xl font-black text-slate-100">{t('frequencyQueries')}</h3>
                          <p className="text-xs text-emerald-500/50 font-medium">{t('statisticsQueries')}</p>
                        </div>
                        <select 
                            value={daysRange}
                            onChange={(e) => setDaysRange(Number(e.target.value))}
                            className="bg-emerald-950/40 border border-emerald-500/20 text-xs sm:text-sm font-semibold text-emerald-300 rounded-xl px-3 py-1.5 outline-none focus:border-emerald-400 cursor-pointer transition-colors hover:bg-emerald-950/60"
                        >
                            <option className="bg-[#060e0a]" value={7}>{t('sevenDays')}</option>
                            <option className="bg-[#060e0a]" value={30}>{t('thirtyDays')}</option>
                        </select>
                    </div>
                    
                    <div className="flex-1 flex flex-col justify-end bg-emerald-950/5 rounded-2xl border border-emerald-500/5 relative overflow-hidden p-4">
                        {/* Native dynamic spline SVG graph */}
                        <div className="absolute inset-x-0 bottom-0 top-10 flex flex-col justify-end">
                            {dailyQueries.length > 0 ? (
                                <svg className="w-full h-full" viewBox="0 0 500 150" preserveAspectRatio="none">
                                    <defs>
                                        <linearGradient id="chartGrad" x1="0" y1="0" x2="0" y2="1">
                                            <stop offset="0%" stopColor="var(--chart-fill, #10b981)" stopOpacity="0.25" />
                                            <stop offset="100%" stopColor="var(--chart-fill, #10b981)" stopOpacity="0.0" />
                                        </linearGradient>
                                    </defs>
                                    {pathD && (
                                        <path 
                                            d={pathD}
                                            fill="none" 
                                            stroke="var(--chart-line, #10b981)" 
                                            strokeWidth="3.5" 
                                            strokeLinecap="round" 
                                            className="animate-pulse"
                                            style={{ animationDuration: '4s' }}
                                        />
                                    )}
                                    {fillD && (
                                        <path 
                                            d={fillD} 
                                            fill="url(#chartGrad)" 
                                        />
                                    )}
                                </svg>
                            ) : (
                                <div className="h-full flex items-center justify-center text-slate-500 text-xs font-bold uppercase tracking-wider">
                                    {language === 'vi' ? 'Không có dữ liệu truy vấn' : 'No query data available'}
                                </div>
                            )}
                        </div>
                        
                        {/* Labels cho Chart */}
                        <div className="relative z-10 flex justify-between text-[10px] font-bold text-emerald-500/60 mt-2 px-2 border-t border-emerald-500/10 pt-2 bg-[#08150f]/80 backdrop-blur-sm rounded-xl">
                            {dailyQueries.map((item: any, idx: number) => (
                                <span key={idx} className={shouldShowLabel(idx) ? "" : "invisible w-0"}>
                                    {dailyQueries.length <= 7 ? getWeekdayLabel(item.date) : formatDateLabel(item.date)}
                                </span>
                            ))}
                        </div>
                    </div>
                </div>

                {/* Bảng Đối soát Giao dịch */}
                <div className="bg-[#060e0a]/80 backdrop-blur-sm rounded-3xl shadow-[0_8px_30px_rgba(0,0,0,0.2)] border border-emerald-500/10 p-6 sm:p-8 h-[440px] flex flex-col">
                    <div className="flex items-center justify-between mb-6">
                        <div>
                          <h3 className="text-lg sm:text-xl font-black text-slate-100">{t('recentTrans')}</h3>
                          <p className="text-xs text-emerald-500/50 font-medium">{t('invoiceSepay')}</p>
                        </div>
                        <span className="flex items-center justify-center px-2.5 py-1 bg-emerald-950/65 border border-emerald-500/20 text-emerald-400 rounded-full text-xs font-black">
                            {data?.recent_transactions?.length || 0}
                        </span>
                    </div>

                    <div className="flex-1 overflow-y-auto pr-1 space-y-3 custom-scrollbar">
                        {!data?.recent_transactions || data.recent_transactions.length === 0 ? (
                            <div className="h-full flex flex-col items-center justify-center text-slate-500 py-10">
                                <Wallet className="w-10 h-10 mb-3 opacity-20" />
                                <p className="text-xs font-bold uppercase tracking-wider">{t('noTransactions')}</p>
                            </div>
                        ) : (
                            data.recent_transactions.map((tx: any) => (
                                <div key={tx.id} className="group flex items-center justify-between p-3.5 rounded-2xl border border-emerald-500/5 hover:border-emerald-500/20 hover:bg-emerald-950/20 hover:shadow-sm transition-all duration-200">
                                    <div className="flex items-center gap-3">
                                        <div className={`w-9 h-9 rounded-xl flex items-center justify-center font-bold text-xs shadow-inner bg-emerald-950 border border-emerald-500/20 text-emerald-400`}>
                                            #{tx.id}
                                        </div>
                                        <div>
                                            <p className="text-xs sm:text-sm font-bold text-slate-200">
                                                {tx.transaction_type === 'admin' ? `Admin điều chỉnh #${tx.user_id}` : `${t('userPrefix')} #${tx.user_id}`}
                                            </p>
                                            <p className="text-[10px] font-semibold text-emerald-500/50 mt-0.5">
                                                {new Date(tx.created_at).toLocaleTimeString(language === 'vi' ? 'vi-VN' : 'en-US', { hour: '2-digit', minute: '2-digit' })} • {new Date(tx.created_at).toLocaleDateString(language === 'vi' ? 'vi-VN' : 'en-US')}
                                            </p>
                                        </div>
                                    </div>
                                    <div className="text-right">
                                        {tx.transaction_type === 'admin' ? (
                                            <p className="text-xs sm:text-sm font-black text-purple-400">
                                                {tx.token_amount >= 0 ? '+' : ''}{tx.token_amount.toLocaleString()} Tokens
                                            </p>
                                        ) : (
                                            <p className="text-sm sm:text-base font-black text-slate-100">
                                                +{tx.amount_vnd.toLocaleString('vi-VN')}đ
                                            </p>
                                        )}
                                        <span className={`inline-flex items-center gap-1 mt-1 text-[8px] sm:text-[9px] font-black uppercase tracking-wider px-2 py-0.5 rounded-full border bg-emerald-950/50 border-emerald-500/30 text-emerald-400`}>
                                            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
                                            {tx.status === 'completed' ? t('success') : t('pending')}
                                        </span>
                                    </div>
                                </div>
                            ))
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
};