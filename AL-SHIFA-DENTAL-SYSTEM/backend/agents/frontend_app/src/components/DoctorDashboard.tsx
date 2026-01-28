import React from 'react';
import { useApp } from '../context/AppContext';
import { Calendar, AlertTriangle, TrendingUp, Users } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';

export const DoctorDashboard: React.FC = () => {
  const { appointments, inventory, user } = useApp();

  // Stats
  const today = new Date().toISOString().split('T')[0];
  const appointmentsToday = appointments.filter(a => a.date === today && a.doctorId === user?.id).length;
  const lowStockItems = inventory.filter(i => i.stock <= i.minThreshold);
  
  const data = [
    { name: 'Mon', patients: 4 },
    { name: 'Tue', patients: 7 },
    { name: 'Wed', patients: 5 },
    { name: 'Thu', patients: 8 },
    { name: 'Fri', patients: 6 },
  ];

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-slate-800">Dashboard Overview</h2>
      
      {/* Quick Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-white p-6 rounded-xl shadow-sm border-l-4 border-medical-500">
            <div className="flex justify-between items-start">
                <div>
                    <p className="text-slate-500 text-sm mb-1">Appointments Today</p>
                    <h3 className="text-3xl font-bold text-slate-800">{appointmentsToday}</h3>
                </div>
                <div className="bg-blue-50 p-3 rounded-lg text-medical-600">
                    <Calendar size={24} />
                </div>
            </div>
        </div>
        <div className="bg-white p-6 rounded-xl shadow-sm border-l-4 border-yellow-500">
             <div className="flex justify-between items-start">
                <div>
                    <p className="text-slate-500 text-sm mb-1">Pending Cases</p>
                    <h3 className="text-3xl font-bold text-slate-800">12</h3>
                </div>
                <div className="bg-yellow-50 p-3 rounded-lg text-yellow-600">
                    <Users size={24} />
                </div>
            </div>
        </div>
        <div className="bg-white p-6 rounded-xl shadow-sm border-l-4 border-green-500">
             <div className="flex justify-between items-start">
                <div>
                    <p className="text-slate-500 text-sm mb-1">Monthly Revenue</p>
                    <h3 className="text-3xl font-bold text-slate-800">$12.4k</h3>
                </div>
                <div className="bg-green-50 p-3 rounded-lg text-green-600">
                    <TrendingUp size={24} />
                </div>
            </div>
        </div>
      </div>

      {/* Alerts & Chart Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Alerts */}
        <div className="bg-white p-6 rounded-xl shadow-sm">
             <h3 className="font-bold text-slate-800 mb-4 flex items-center gap-2">
                 <AlertTriangle className="text-red-500" size={20}/> Attention Needed
             </h3>
             <div className="space-y-3">
                 {lowStockItems.map(item => (
                     <div key={item.id} className="bg-red-50 p-3 rounded-lg border border-red-100 flex justify-between items-center">
                         <span className="text-red-800 text-sm font-medium">Low Stock: {item.name}</span>
                         <span className="text-red-600 text-xs font-bold">{item.stock} {item.unit} left</span>
                     </div>
                 ))}
                 {lowStockItems.length === 0 && <p className="text-slate-500 text-sm">No active alerts.</p>}
                 
                 <div className="bg-yellow-50 p-3 rounded-lg border border-yellow-100 flex justify-between items-center">
                     <span className="text-yellow-800 text-sm font-medium">Follow-up: Bob Williams</span>
                     <span className="text-yellow-600 text-xs font-bold">Overdue 2 days</span>
                 </div>
             </div>
        </div>

        {/* Mini Chart */}
        <div className="bg-white p-6 rounded-xl shadow-sm">
             <h3 className="font-bold text-slate-800 mb-4">Patient Activity (This Week)</h3>
             <div className="h-48">
                <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={data}>
                        <XAxis dataKey="name" fontSize={12} tickLine={false} axisLine={false} />
                        <YAxis hide />
                        <Tooltip cursor={{fill: 'transparent'}} contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 12px rgba(0,0,0,0.1)' }} />
                        <Bar dataKey="patients" fill="#0077B6" radius={[4, 4, 0, 0]} barSize={30} />
                    </BarChart>
                </ResponsiveContainer>
             </div>
        </div>
      </div>
    </div>
  );
};
