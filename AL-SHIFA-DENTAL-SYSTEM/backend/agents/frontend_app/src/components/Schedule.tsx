import React from 'react';
import { useApp } from '../context/AppContext';
import { Clock, User, CheckCircle } from 'lucide-react';

export const Schedule: React.FC = () => {
  const { appointments, patients, user } = useApp();
  
  // Filter for this doctor and sort by time
  const mySchedule = appointments
    .filter(a => a.doctorId === user?.id)
    .sort((a, b) => a.timeSlot.localeCompare(b.timeSlot));

  return (
    <div className="space-y-6">
        <div className="flex justify-between items-center">
            <h2 className="text-2xl font-bold text-slate-800">Today's Schedule</h2>
            <span className="bg-medical-100 text-medical-700 px-3 py-1 rounded-full text-sm font-medium">
                {new Date().toDateString()}
            </span>
        </div>

        <div className="bg-white rounded-xl shadow-sm overflow-hidden">
            {mySchedule.length === 0 ? (
                <div className="p-8 text-center text-slate-500">No appointments scheduled for today.</div>
            ) : (
                <div className="divide-y divide-gray-100">
                    {mySchedule.map(apt => {
                        const patient = patients.find(p => p.id === apt.patientId);
                        return (
                            <div key={apt.id} className="p-4 hover:bg-slate-50 transition-colors flex items-center justify-between">
                                <div className="flex items-center gap-4">
                                    <div className="w-24 font-mono text-slate-600 font-medium flex items-center gap-1">
                                        <Clock size={16} className="text-medical-400"/> {apt.timeSlot}
                                    </div>
                                    <div>
                                        <h3 className="font-bold text-slate-800">{patient?.name}</h3>
                                        <p className="text-sm text-slate-500">{apt.type}</p>
                                    </div>
                                </div>
                                <div className="flex items-center gap-3">
                                    <span className={`px-3 py-1 rounded-full text-xs font-bold ${apt.status === 'Confirmed' ? 'bg-blue-100 text-blue-700' : 'bg-green-100 text-green-700'}`}>
                                        {apt.status}
                                    </span>
                                    <button className="text-sm text-red-500 hover:underline">Block</button>
                                </div>
                            </div>
                        );
                    })}
                </div>
            )}
        </div>
    </div>
  );
};
