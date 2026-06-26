import React, { useState, useEffect } from 'react';
import { X, QrCode, Loader2, CheckCircle } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';

interface Props {
  isOpen: boolean;
  onClose: () => void;
}

interface PaymentData {
  hex_id: string;
  content: string;
  amount: number;
  qr_url: string;
}

const TopupModal: React.FC<Props> = ({ isOpen, onClose }) => {
  const { user, refreshUser } = useAuth(); 
  // Sửa giá trị mặc định ban đầu là 2k
  const [amountK, setAmountK] = useState<number>(2); 
  const [paymentData, setPaymentData] = useState<PaymentData | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [status, setStatus] = useState<'idle' | 'pending' | 'completed'>('idle');
  const [rate, setRate] = useState<number>(10000);

  const token = localStorage.getItem('access_token');
  const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'; 

  useEffect(() => {
    const fetchRate = async () => {
      try {
        const res = await fetch(`${API_BASE_URL}/payment/rate`);
        if (res.ok) {
          const data = await res.json();
          setRate(data.tokens_per_1000_vnd);
        }
      } catch (error) {
        console.error("Lỗi lấy tỷ lệ quy đổi:", error);
      }
    };
    if (isOpen) {
      fetchRate();
    }
  }, [isOpen]);

  const handleCreatePayment = async () => {
    try {
      setLoading(true);
      const res = await fetch(`${API_BASE_URL}/payment/create?amount_k=${amountK}`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });
      
      if (!res.ok) throw new Error("Không thể tạo hóa đơn");
      
      const data = await res.json();
      setPaymentData(data);
      setStatus('pending');
    } catch (error) {
      console.error(error);
      alert("Lỗi hệ thống. Vui lòng thử lại sau.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    let interval: NodeJS.Timeout;
    
    const checkStatus = async () => {
      // Chỉ hỏi thăm (polling) khi đang ở trạng thái pending
      if (!paymentData?.hex_id || status !== 'pending') return;
      
      try {
        const res = await fetch(`${API_BASE_URL}/payment/status/${paymentData.hex_id}`, {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        const data = await res.json();
        
        // Ngay khi Backend báo hoàn tất, chuyển state để dập tắt vòng lặp
        if (data.status === 'completed') {
          setStatus('completed');
          if (refreshUser) refreshUser(); 
        }
      } catch (error) {
        console.error("Lỗi polling:", error);
      }
    };

    if (status === 'pending') {
      interval = setInterval(checkStatus, 6000); 
    }
    
    // Clear interval ngay khi status thay đổi khỏi 'pending' hoặc component unmount
    return () => clearInterval(interval);
  }, [paymentData, status, token, refreshUser]);

  useEffect(() => {
    if (!isOpen) {
      setPaymentData(null);
      setStatus('idle');
      // Reset về mức tối thiểu 2k khi đóng modal
      setAmountK(2); 
    }
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-md flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-[2rem] shadow-2xl w-full max-w-md overflow-hidden relative border border-slate-100">
        <button 
          onClick={onClose} 
          className="absolute top-6 right-6 p-2 text-slate-400 hover:text-slate-600 bg-slate-50 rounded-full transition-colors"
        >
          <X size={20} />
        </button>

        <div className="p-10 text-center">
          {status === 'idle' && (
            <>
              <div className="w-20 h-20 bg-emerald-50 text-emerald-600 rounded-3xl flex items-center justify-center mx-auto mb-6">
                <QrCode size={40} />
              </div>
              <h2 className="text-2xl font-black text-slate-800 mb-2">Nạp Token</h2>
              <p className="text-slate-500 mb-8 text-sm">Mệnh giá thấp nhất là 2k (2.000đ = {(2 * rate).toLocaleString()} Token)</p>
              
              <div className="grid grid-cols-3 gap-3 mb-4">
                {[20, 50, 100].map(val => (
                  <button
                    key={val}
                    onClick={() => setAmountK(val)}
                    className={`py-3 rounded-2xl border-2 text-sm font-bold transition-all ${
                      amountK === val 
                        ? 'border-emerald-500 bg-emerald-50 text-emerald-700' 
                        : 'border-slate-100 text-slate-500 hover:border-emerald-100'
                    }`}
                  >
                    {val}k
                  </button>
                ))}
              </div>

              <div className="mb-8 text-left">
                <label className="block text-sm font-medium text-slate-700 mb-2">Hoặc nhập số tiền khác (Tối thiểu 2k):</label>
                <div className="relative">
                  <input
                    type="number"
                    min="2"
                    value={amountK || ''}
                    onChange={(e) => setAmountK(Number(e.target.value))}
                    className="w-full py-3 px-4 pr-16 bg-slate-50 border border-slate-200 rounded-2xl outline-none focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 transition-all text-slate-800 font-bold"
                  />
                  <div className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-400 font-semibold">.000 đ</div>
                </div>
                {amountK >= 2 ? (
                  <p className="text-emerald-600 text-xs font-bold mt-2">Nhận được: {(amountK * rate).toLocaleString()} Tokens</p>
                ) : (
                  <p className="text-red-500 text-xs mt-2">Số tiền tối thiểu là 2k VNĐ.</p>
                )}
              </div>

              <button
                onClick={handleCreatePayment}
                disabled={loading || amountK < 2}
                className="w-full py-4 bg-emerald-600 hover:bg-emerald-700 text-white rounded-2xl font-bold flex justify-center items-center gap-3 transition-all shadow-lg shadow-emerald-200 disabled:opacity-50"
              >
                {loading ? <Loader2 size={20} className="animate-spin" /> : 'Xác nhận nạp'}
              </button>
            </>
          )}

          {status === 'pending' && paymentData && (
            <>
              <div className="animate-pulse mb-6">
                <div className="w-16 h-2 bg-blue-100 rounded-full mx-auto"></div>
              </div>
              <h2 className="text-xl font-bold text-slate-800 mb-2">Quét mã thanh toán</h2>
              <p className="text-xs text-red-500 mb-2 font-bold animate-pulse">⚠️ Vui lòng không đóng giao diện này khi đang thanh toán</p>
              <p className="text-xs text-slate-400 mb-6 italic">Hệ thống đang chờ xác nhận từ ngân hàng...</p>

              <div className="bg-white p-4 rounded-3xl border-4 border-slate-50 inline-block mb-6 shadow-sm">
                <img src={paymentData.qr_url} alt="VietQR" className="w-56 h-56 object-contain" />
              </div>

              <div className="text-left space-y-3 bg-slate-50 p-5 rounded-2xl border border-slate-100">
                <div className="flex justify-between items-center">
                  <span className="text-slate-500 text-xs">Số tiền:</span>
                  <span className="font-black text-emerald-600">{paymentData.amount.toLocaleString()} VNĐ</span>
                </div>
                <div className="pt-2 border-t border-slate-200">
                  <span className="text-slate-500 text-xs block mb-1">Nội dung chuyển khoản:</span>
                  <div className="font-mono bg-white p-3 rounded-lg border border-slate-200 text-center font-bold text-slate-800 tracking-tighter">
                    {paymentData.content}
                  </div>
                </div>
              </div>
            </>
          )}

          {status === 'completed' && paymentData && (
            <>
              <div className="w-24 h-24 bg-emerald-50 text-emerald-500 rounded-full flex items-center justify-center mx-auto mb-6 shadow-inner">
                <CheckCircle size={56} />
              </div>
              <h2 className="text-2xl font-black text-slate-800 mb-2">Thành công!</h2>
              <p className="text-slate-500 text-sm mb-8">
                Hệ thống đã nhận được {paymentData.amount.toLocaleString()}đ. Token đã được cộng vào tài khoản của huynh.
              </p>
              <button
                onClick={onClose}
                className="w-full py-4 bg-slate-900 text-white rounded-2xl font-bold hover:bg-slate-800 transition-all shadow-xl"
              >
                Tiếp tục sử dụng
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
};

export default TopupModal;