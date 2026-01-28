import React from 'react';
import { useApp } from "../context/AppContext";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { Download } from 'lucide-react';

export const Finance: React.FC = () => {
  const { invoices } = useApp();

  const revenueData = [
      { month: 'Jan', revenue: 8500 },
      { month: 'Feb', revenue: 9200 },
      { month: 'Mar', revenue: 11000 },
      { month: 'Apr', revenue: 10500 },
      { month: 'May', revenue: 12400 },
      { month: 'Jun', revenue: 9800 },
  ];

  return (
    <div className="space-y-6">
        <h2 className="text-2xl font-bold text-slate-800">Financial Overview</h2>

        {/* Chart */}
        <div className="bg-white p-6 rounded-xl shadow-sm">
            <h3 className="text-lg font-semibold mb-4 text-slate-700">Revenue Trends (Last 6 Months)</h3>
            <div className="h-80">
                <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={revenueData}>
                        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                        <XAxis dataKey="month" axisLine={false} tickLine={false} tick={{fill: '#64748b'}} />
                        <YAxis axisLine={false} tickLine={false} tick={{fill: '#64748b'}} tickFormatter={(value) => `$${value/1000}k`} />
                        <Tooltip 
                            contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 12px rgba(0,0,0,0.1)' }} 
                            formatter={(value: number) => [`$${value}`, 'Revenue']}
                        />
                        <Bar dataKey="revenue" fill="#0077B6" radius={[4, 4, 0, 0]} barSize={40} />
                    </BarChart>
                </ResponsiveContainer>
            </div>
        </div>

        {/* Recent Invoices */}
        <div className="bg-white rounded-xl shadow-sm overflow-hidden">
            <div className="p-6 border-b border-gray-100 flex justify-between items-center">
                <h3 className="text-lg font-semibold text-slate-700">Recent Invoices</h3>
                <button className="text-sm text-medical-600 hover:underline flex items-center gap-1"><Download size={14}/> Export CSV</button>
            </div>
            <table className="w-full">
                <thead className="bg-slate-50">
                    <tr>
                        <th className="p-4 text-left text-sm font-medium text-slate-500">Invoice ID</th>
                        <th className="p-4 text-left text-sm font-medium text-slate-500">Patient</th>
                        <th className="p-4 text-left text-sm font-medium text-slate-500">Date</th>
                        <th className="p-4 text-left text-sm font-medium text-slate-500">Amount</th>
                        <th className="p-4 text-left text-sm font-medium text-slate-500">Status</th>
                    </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                    {invoices.map(inv => (
                        <tr key={inv.id} className="hover:bg-slate-50">
                            <td className="p-4 font-mono text-xs text-slate-500">#{inv.id.toUpperCase()}</td>
                            <td className="p-4 font-medium text-slate-800">{inv.patientName}</td>
                            <td className="p-4 text-slate-600">{inv.date}</td>
                            <td className="p-4 font-bold text-slate-800">${inv.amount}</td>
                            <td className="p-4">
                                <span className={`px-2 py-1 rounded-full text-xs font-bold ${inv.status === 'Paid' ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700'}`}>
                                    {inv.status}
                                </span>
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    </div>
  );
};
