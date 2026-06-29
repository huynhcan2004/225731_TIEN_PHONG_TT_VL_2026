import React, { useEffect, useState } from 'react';
import { 
    CreditCard, 
    CheckCircle2, 
    Clock, 
    AlertCircle, 
    TrendingUp, 
    ArrowDownLeft, 
    Search,
    Loader2,
    UserCog
} from 'lucide-react';

interface PaymentData {
    id: number;
    user_id: number;
    user_email: string; // Khớp với alias trong admin.py
    amount_vnd: number;
    token_amount: number;
    status: 'pending' | 'completed' | 'failed';
    transaction_type?: 'sepay' | 'admin';
    created_at: string;
}

export const FinanceManager = () => {
    const [payments, setPayments] = useState<PaymentData[]>([]);
    const [loading, setLoading] = useState(true);
    const [searchTerm, setSearchTerm] = useState('');

    useEffect(() => {
        const fetchPayments = async () => {
            try {
                const token = localStorage.getItem('access_token');
                const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
                
                // Sử dụng đúng prefix /api/admin từ backend
                const res = await fetch(`${API_URL}/admin/payments`, {
                    headers: { 'Authorization': `Bearer ${token}` }
                });
                
                if (res.ok) {
                    const data = await res.json();
                    setPayments(data);
                }
            } catch (error) {
                console.error("Lỗi đối soát giao dịch:", error);
            } finally {
                setLoading(false);
            }
        };
        fetchPayments();
    }, []);

    const filteredPayments = payments.filter(p => 
        p.user_email?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        p.id.toString().includes(searchTerm)
    );

    const totalRevenue = payments
        .filter(p => p.status === 'completed' && p.transaction_type !== 'admin')
        .reduce((sum, curr) => sum + curr.amount_vnd, 0);

    if (loading) {
        return (
            <div className="flex flex-col items-center justify-center h-[60vh] text-emerald-600">
                <Loader2 className="w-10 h-10 animate-spin mb-4" />
                <p className="font-bold tracking-widest uppercase text-xs">Đang tải dữ liệu SePay...</p>
            </div>
        );
    }

    return (
        <div className="space-y-6 animate-fadeIn">
            {/* Header Thống kê nhanh */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="bg-gradient-to-br from-emerald-600 to-teal-700 p-6 rounded-3xl text-white shadow-lg">
                    <div className="flex items-center justify-between mb-4">
                        <TrendingUp className="w-6 h-6 opacity-80" />
                        <span className="text-[10px] font-bold bg-white/20 px-2 py-1 rounded-full uppercase">Real-time</span>
                    </div>
                    <p className="text-sm font-medium opacity-80">Tổng doanh thu thực tế</p>
                    <h3 className="text-3xl font-black mt-1">{totalRevenue.toLocaleString('vi-VN')} đ</h3>
                </div>
                
                <div className="bg-white p-6 rounded-3xl border border-gray-100 shadow-sm md:col-span-2 flex items-center justify-between">
                    <div>
                        <h2 className="text-xl font-black text-slate-800">Đối soát Giao dịch</h2>
                        <p className="text-slate-500 text-sm">Quản lý dòng tiền nạp qua hệ thống SePay và Admin điều chỉnh.</p>
                    </div>
                    <div className="relative">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                        <input 
                            type="text" 
                            placeholder="Tìm theo email hoặc mã đơn..." 
                            className="pl-10 pr-4 py-2 bg-gray-50 border border-gray-200 rounded-xl text-sm outline-none focus:border-emerald-500 w-64"
                            value={searchTerm}
                            onChange={(e) => setSearchTerm(e.target.value)}
                        />
                    </div>
                </div>
            </div>

            {/* Danh sách giao dịch */}
            <div className="bg-white rounded-3xl shadow-sm border border-gray-100 overflow-hidden">
                <div className="overflow-x-auto">
                    <table className="w-full text-left border-collapse">
                        <thead className="bg-slate-50 border-b border-gray-100">
                            <tr>
                                <th className="p-5 text-xs font-bold text-slate-500 uppercase tracking-widest">Mã đơn</th>
                                <th className="p-5 text-xs font-bold text-slate-500 uppercase tracking-widest">Khách hàng</th>
                                <th className="p-5 text-xs font-bold text-slate-500 uppercase tracking-widest">Loại GD</th>
                                <th className="p-5 text-xs font-bold text-slate-500 uppercase tracking-widest">Số tiền</th>
                                <th className="p-5 text-xs font-bold text-slate-500 uppercase tracking-widest">Trạng thái</th>
                                <th className="p-5 text-xs font-bold text-slate-500 uppercase tracking-widest">Thời gian</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-50">
                            {filteredPayments.length === 0 ? (
                                <tr>
                                    <td colSpan={6} className="p-10 text-center text-slate-400 italic font-medium">
                                        Chưa có lịch sử giao dịch nào được ghi nhận.
                                    </td>
                                </tr>
                            ) : (
                                filteredPayments.map(p => (
                                    <tr key={p.id} className="hover:bg-emerald-50/20 transition-colors group">
                                        <td className="p-5 font-mono text-xs font-bold text-emerald-700">#{p.id}</td>
                                        <td className="p-5">
                                            <div className="flex items-center gap-2">
                                                <div className="p-2 bg-slate-100 rounded-lg group-hover:bg-white transition-colors">
                                                    {p.transaction_type === 'admin' ? (
                                                        <UserCog className="w-4 h-4 text-purple-500" />
                                                    ) : (
                                                        <ArrowDownLeft className="w-4 h-4 text-slate-500" />
                                                    )}
                                                </div>
                                                <span className="text-sm font-semibold text-slate-700">{p.user_email}</span>
                                            </div>
                                        </td>
                                        <td className="p-5">
                                            {p.transaction_type === 'admin' ? (
                                                <span className="px-2.5 py-1 rounded-full text-[10px] font-black uppercase tracking-wider bg-purple-100 text-purple-700 border border-purple-200">
                                                    Admin nạp/trừ
                                                </span>
                                            ) : (
                                                <span className="px-2.5 py-1 rounded-full text-[10px] font-black uppercase tracking-wider bg-emerald-100 text-emerald-700 border border-emerald-200">
                                                    Nạp SePay
                                                </span>
                                            )}
                                        </td>
                                        <td className="p-5">
                                            {p.transaction_type === 'admin' ? (
                                                <p className="text-sm font-bold text-slate-500">0 đ</p>
                                            ) : (
                                                <p className="text-sm font-black text-slate-800">{p.amount_vnd.toLocaleString()} đ</p>
                                            )}
                                            <p className={`text-[10px] font-bold ${p.token_amount >= 0 ? 'text-emerald-600' : 'text-rose-500'}`}>
                                                {p.token_amount >= 0 ? '+' : ''}{p.token_amount.toLocaleString()} Tokens
                                            </p>
                                        </td>
                                        <td className="p-5">
                                            <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-wider
                                                ${p.status === 'completed' 
                                                    ? 'bg-emerald-100 text-emerald-700 border border-emerald-200' 
                                                    : 'bg-orange-100 text-orange-700 border border-orange-200'}`}>
                                                {p.status === 'completed' ? <CheckCircle2 className="w-3 h-3" /> : <Clock className="w-3 h-3" />}
                                                {p.status === 'completed' ? 'Thành công' : 'Chờ xử lý'}
                                            </span>
                                        </td>
                                        <td className="p-5 text-xs text-slate-400 font-medium">
                                            {new Date(p.created_at).toLocaleString('vi-VN')}
                                        </td>
                                    </tr>
                                ))
                            )}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
};