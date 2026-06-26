// frontend/src/components/admin/UserList.tsx
import React, { useEffect, useState } from 'react';
import { User, ShieldCheck, Mail, Coins, Search, Loader2, ShieldAlert, ArrowRight } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { useLanguageTheme } from '../../context/LanguageThemeContext';

interface UserData {
    id: number | string;
    username: string;
    email: string;
    role: string;
    token_balance: number;
    is_premium: boolean;
    is_root_admin: boolean;
    created_at: string;
}

export const UserList = () => {
    const { user: currentUser } = useAuth();
    const { t, language } = useLanguageTheme();
    const [users, setUsers] = useState<UserData[]>([]);
    const [loading, setLoading] = useState(true);
    const [searchTerm, setSearchTerm] = useState('');

    // State cho Form đổi quyền
    const [roleEmail, setRoleEmail] = useState('');
    const [roleValue, setRoleValue] = useState('admin');
    const [submittingRole, setSubmittingRole] = useState(false);

    // State cho Form cộng/trừ Token
    const [tokenEmail, setTokenEmail] = useState('');
    const [tokenAmount, setTokenAmount] = useState('');
    const [submittingTokens, setSubmittingTokens] = useState(false);

    const fetchUsers = async () => {
        try {
            const token = localStorage.getItem('access_token');
            const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
            const res = await fetch(`${API_URL}/api/admin/users`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (res.ok) {
                setUsers(await res.json());
            }
        } catch (error) {
            console.error("Lỗi lấy danh sách người dùng:", error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchUsers();
    }, []);

    const handleRoleChange = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!roleEmail.trim()) {
            alert(language === 'vi' ? "Vui lòng nhập email." : "Please enter email.");
            return;
        }

        if (!window.confirm(language === 'vi' ? `Xác nhận đổi vai trò của tài khoản ${roleEmail} thành ${roleValue.toUpperCase()}?` : `Confirm changing role of account ${roleEmail} to ${roleValue.toUpperCase()}?`)) {
            return;
        }

        setSubmittingRole(true);
        try {
            const token = localStorage.getItem('access_token');
            const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
            const res = await fetch(`${API_URL}/api/admin/users/role-by-email`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    email: roleEmail.trim(),
                    role: roleValue
                })
            });

            const data = await res.json();
            if (res.ok) {
                alert(data.message || (language === 'vi' ? "Đổi vai trò thành công!" : "Role changed successfully!"));
                setRoleEmail('');
                fetchUsers();
            } else {
                alert(data.detail || (language === 'vi' ? "Lỗi khi cập nhật vai trò." : "Error updating role."));
            }
        } catch (error) {
            alert(language === 'vi' ? "Lỗi kết nối hệ thống." : "System connection error.");
        } finally {
            setSubmittingRole(false);
        }
    };

    const handleTokenAdjustment = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!tokenEmail.trim()) {
            alert(language === 'vi' ? "Vui lòng nhập email." : "Please enter email.");
            return;
        }

        const amt = parseFloat(tokenAmount);
        if (isNaN(amt)) {
            alert(language === 'vi' ? "Vui lòng nhập số lượng token hợp lệ." : "Please enter a valid token amount.");
            return;
        }

        if (!window.confirm(language === 'vi' ? `Xác nhận nạp/trừ ${amt.toLocaleString('vi-VN')} Token cho tài khoản ${tokenEmail}?` : `Confirm adding/deducting ${amt.toLocaleString('en-US')} Token for account ${tokenEmail}?`)) {
            return;
        }

        setSubmittingTokens(true);
        try {
            const token = localStorage.getItem('access_token');
            const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
            const res = await fetch(`${API_URL}/api/admin/users/add-tokens`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    email: tokenEmail.trim(),
                    tokens: amt
                })
            });

            const data = await res.json();
            if (res.ok) {
                alert(data.message || (language === 'vi' ? "Cập nhật Token thành công!" : "Token updated successfully!"));
                setTokenEmail('');
                setTokenAmount('');
                fetchUsers();
            } else {
                alert(data.detail || (language === 'vi' ? "Lỗi khi cập nhật Token." : "Error updating Token."));
            }
        } catch (error) {
            alert(language === 'vi' ? "Lỗi kết nối hệ thống." : "System connection error.");
        } finally {
            setSubmittingTokens(false);
        }
    };

    const filteredUsers = users.filter(u =>
        u.username.toLowerCase().includes(searchTerm.toLowerCase()) ||
        u.email.toLowerCase().includes(searchTerm.toLowerCase())
    );

    if (loading) {
        return (
            <div className="flex flex-col items-center justify-center h-64 text-emerald-500">
                <Loader2 className="w-8 h-8 animate-spin mb-4" />
                <p className="font-bold text-sm text-emerald-400">{t('loadingUsers')}</p>
            </div>
        );
    }

    return (
        <div className="space-y-8 animate-fadeIn text-slate-100 relative">
            
            {/* Header + Search Bar */}
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-emerald-500/10 pb-5">
                <div>
                    <h2 className="text-2xl font-black text-slate-100 flex items-center gap-2">
                        <User className="w-6 h-6 text-emerald-400" /> {t('userManagementTitle')}
                    </h2>
                    <p className="text-xs text-slate-400 mt-1">{t('userManagementSub')}</p>
                </div>
                <div className="relative w-full md:w-80">
                    <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-emerald-500/50" />
                    <input 
                        type="text" 
                        placeholder={t('searchPlaceholder')}
                        className="w-full pl-10 pr-4 py-2.5 bg-emerald-950/20 border border-emerald-500/20 rounded-xl text-sm outline-none focus:border-emerald-400 transition-all font-semibold text-slate-200"
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                    />
                </div>
            </div>

            {/* BẢNG ĐIỀU KHIỂN DÀNH RIÊNG CHO ADMIN GỐC */}
            {currentUser?.is_root_admin && (
                <div className="bg-[#0b1611]/90 rounded-3xl p-6 border border-amber-500/20 shadow-lg space-y-6">
                    <div className="flex items-center gap-2 border-b border-emerald-500/10 pb-3">
                        <ShieldAlert className="w-5 h-5 text-amber-400 animate-pulse" />
                        <h3 className="text-sm font-black text-amber-300 uppercase tracking-widest">
                            {t('rootAdminPanelTitle')}
                        </h3>
                    </div>
                    
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                        {/* Box 1: Đổi Quyền Admin */}
                        <form onSubmit={handleRoleChange} className="bg-emerald-950/10 border border-emerald-500/10 p-5 rounded-2xl space-y-4">
                            <h4 className="text-xs font-black text-emerald-400 uppercase tracking-wider">
                                {t('setRoleTitle')}
                            </h4>
                            
                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                                <div>
                                    <label className="text-[10px] font-bold text-slate-400 uppercase ml-1 block mb-1">{t('emailToModify')}</label>
                                    <input 
                                        type="email" 
                                        required
                                        placeholder="user@gmail.com"
                                        value={roleEmail}
                                        onChange={(e) => setRoleEmail(e.target.value)}
                                        className="w-full p-2.5 bg-[#060e0a] border border-emerald-500/20 rounded-xl text-xs text-slate-200 outline-none focus:border-emerald-400"
                                    />
                                </div>
                                <div>
                                    <label className="text-[10px] font-bold text-slate-400 uppercase ml-1 block mb-1">{t('newRole')}</label>
                                    <select 
                                        value={roleValue}
                                        onChange={(e) => setRoleValue(e.target.value)}
                                        className="w-full p-2.5 bg-[#060e0a] border border-emerald-500/20 rounded-xl text-xs font-bold text-slate-200 outline-none focus:border-emerald-400"
                                    >
                                        <option value="user">{t('roleUserOption')}</option>
                                        <option value="admin">{t('roleAdminOption')}</option>
                                    </select>
                                </div>
                            </div>
                            
                            <button 
                                type="submit" 
                                disabled={submittingRole}
                                className="w-full py-2 bg-amber-500 hover:bg-amber-600 disabled:opacity-50 text-white font-bold rounded-xl text-xs transition-colors flex items-center justify-center gap-1 cursor-pointer"
                            >
                                {submittingRole ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <ArrowRight className="w-3.5 h-3.5" />}
                                {t('updateRoleBtn')}
                            </button>
                        </form>

                        {/* Box 2: Cộng/Trừ Token */}
                        <form onSubmit={handleTokenAdjustment} className="bg-emerald-950/10 border border-emerald-500/10 p-5 rounded-2xl space-y-4">
                            <h4 className="text-xs font-black text-emerald-400 uppercase tracking-wider">
                                {t('adjustTokensTitle')}
                            </h4>
                            
                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                                <div>
                                    <label className="text-[10px] font-bold text-slate-400 uppercase ml-1 block mb-1">{t('emailToDeposit')}</label>
                                    <input 
                                        type="email" 
                                        required
                                        placeholder="user@gmail.com"
                                        value={tokenEmail}
                                        onChange={(e) => setTokenEmail(e.target.value)}
                                        className="w-full p-2.5 bg-[#060e0a] border border-emerald-500/20 rounded-xl text-xs text-slate-200 outline-none focus:border-emerald-400"
                                    />
                                </div>
                                <div>
                                    <label className="text-[10px] font-bold text-slate-400 uppercase ml-1 block mb-1">{t('tokenAmountLabel')}</label>
                                    <input 
                                        type="number" 
                                        required
                                        placeholder={language === 'vi' ? "VD: 50000 hoặc -20000" : "E.g. 50000 or -20000"}
                                        value={tokenAmount}
                                        onChange={(e) => setTokenAmount(e.target.value)}
                                        className="w-full p-2.5 bg-[#060e0a] border border-emerald-500/20 rounded-xl text-xs text-slate-200 outline-none focus:border-emerald-400"
                                    />
                                </div>
                            </div>
                            
                            <button 
                                type="submit" 
                                disabled={submittingTokens}
                                className="w-full py-2 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white font-bold rounded-xl text-xs transition-colors flex items-center justify-center gap-1 cursor-pointer"
                            >
                                {submittingTokens ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Coins className="w-3.5 h-3.5" />}
                                {t('adjustTokensBtn')}
                            </button>
                        </form>
                    </div>
                </div>
            )}

            {/* BẢNG DANH SÁCH NGƯỜI DÙNG */}
            <div className="bg-[#060e0a]/90 rounded-3xl border border-emerald-500/10 overflow-hidden shadow-2xl">
                <table className="w-full text-left border-collapse text-sm">
                    <thead>
                        <tr className="bg-emerald-950/40 border-b border-emerald-500/10 text-emerald-400 font-bold text-xs uppercase tracking-wider">
                            <th className="p-5">{t('userCol')}</th>
                            <th className="p-5 w-[180px]">{t('userRoleCol')}</th>
                            <th className="p-5 w-[180px]">{t('tokenBalanceCol')}</th>
                            <th className="p-5 w-[180px]">{t('joinedDateCol')}</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-emerald-500/5 bg-[#060e0a]/50">
                        {filteredUsers.length === 0 ? (
                            <tr>
                                <td colSpan={4} className="p-8 text-center text-slate-500 italic">
                                    {t('noUsersFound')}
                                </td>
                            </tr>
                        ) : (
                            filteredUsers.map(u => (
                                <tr key={u.id} className="hover:bg-emerald-950/20 transition-colors">
                                    <td className="p-5 flex items-center gap-3">
                                        <div className="w-9 h-9 rounded-xl bg-emerald-950 border border-emerald-500/25 flex items-center justify-center text-emerald-300 font-black text-sm shadow-inner">
                                            {u.username ? u.username[0].toUpperCase() : 'U'}
                                        </div>
                                        <div>
                                            <p className="text-sm font-bold text-slate-200">{u.username || t('anonymousUser')}</p>
                                            <p className="text-xs text-slate-400 font-mono mt-0.5">{u.email}</p>
                                        </div>
                                    </td>
                                    <td className="p-5">
                                        <div className="flex items-center gap-1.5">
                                            <span className={`px-2.5 py-1 rounded-full text-[10px] font-black uppercase tracking-wider border ${
                                                u.role === 'admin' 
                                                    ? 'bg-purple-950/40 text-purple-400 border-purple-500/25' 
                                                    : 'bg-emerald-950/30 text-emerald-400 border-emerald-500/20'
                                            }`}>
                                                {u.role}
                                            </span>
                                            {u.is_root_admin && (
                                                <span className="px-2 py-0.5 rounded-full text-[9px] font-black uppercase tracking-wider bg-amber-950/40 text-amber-400 border border-amber-500/30 animate-pulse">
                                                    {t('rootLabel')}
                                                </span>
                                            )}
                                        </div>
                                    </td>
                                    <td className="p-5">
                                        <span className="text-sm font-bold text-emerald-300 font-mono">
                                            {u.token_balance.toLocaleString(language === 'vi' ? 'vi-VN' : 'en-US')}
                                        </span>
                                        <span className="text-xs text-emerald-500/60 font-semibold ml-1">Tokens</span>
                                    </td>
                                    <td className="p-5 text-xs text-slate-400 font-semibold">
                                        {new Date(u.created_at).toLocaleDateString(language === 'vi' ? 'vi-VN' : 'en-US')}
                                    </td>
                                </tr>
                            ))
                        )}
                    </tbody>
                </table>
            </div>
        </div>
    );
};