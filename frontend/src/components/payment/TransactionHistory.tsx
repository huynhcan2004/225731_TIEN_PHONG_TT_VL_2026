import React, { useEffect, useState } from 'react';
// Giả định huynh dùng axios hoặc fetch để gọi API

export const TransactionHistory = () => {
    const [history, setHistory] = useState([]);

    return (
        <div className="p-4 bg-white rounded-lg shadow">
            <h3 className="text-lg font-bold mb-4">Lịch sử giao dịch Token</h3>
            <table className="w-full text-left border-collapse">
                <thead>
                    <tr className="border-b bg-gray-50">
                        <th className="p-2">Thời gian</th>
                        <th className="p-2">Loại</th>
                        <th className="p-2">Số lượng</th>
                        <th className="p-2">Nội dung</th>
                    </tr>
                </thead>
                <tbody>
                    {history.map((item: any) => (
                        <tr key={item.id} className="border-b hover:bg-gray-50">
                            <td className="p-2 text-sm">{new Date(item.created_at).toLocaleString()}</td>
                            <td className="p-2">
                                <span className={item.type === 'in' ? 'text-green-600' : 'text-red-600'}>
                                    {item.type === 'in' ? '➕ Nạp' : '➖ Tiêu'}
                                </span>
                            </td>
                            <td className="p-2 font-mono">{item.amount.toLocaleString()}</td>
                            <td className="p-2 text-sm text-gray-600">{item.description}</td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
};