import React from 'react';
import { useApp } from '../context/AppContext';
import { Package, RefreshCw } from 'lucide-react';

export const Inventory: React.FC = () => {
  const { inventory, updateStock } = useApp();

  return (
    <div className="space-y-6">
       <h2 className="text-2xl font-bold text-slate-800">Inventory Management</h2>
       
       <div className="bg-white rounded-xl shadow-sm overflow-hidden">
           <div className="overflow-x-auto">
               <table className="w-full">
                   <thead className="bg-slate-50 border-b border-gray-200">
                       <tr>
                           <th className="p-4 text-left text-sm font-semibold text-slate-600">Item Name</th>
                           <th className="p-4 text-left text-sm font-semibold text-slate-600">Category</th>
                           <th className="p-4 text-left text-sm font-semibold text-slate-600">Stock Level</th>
                           <th className="p-4 text-left text-sm font-semibold text-slate-600">Status</th>
                           <th className="p-4 text-left text-sm font-semibold text-slate-600">Actions</th>
                       </tr>
                   </thead>
                   <tbody className="divide-y divide-gray-100">
                       {inventory.map(item => {
                           const isCritical = item.stock <= 5;
                           const isLow = item.stock <= item.minThreshold;
                           
                           return (
                               <tr key={item.id} className="hover:bg-slate-50">
                                   <td className="p-4 font-medium text-slate-800 flex items-center gap-2">
                                       <Package size={16} className="text-slate-400"/> {item.name}
                                   </td>
                                   <td className="p-4 text-slate-600">{item.category}</td>
                                   <td className="p-4 font-mono">
                                       {item.stock} <span className="text-xs text-slate-400">{item.unit}</span>
                                   </td>
                                   <td className="p-4">
                                       {isCritical ? (
                                           <span className="bg-red-100 text-red-700 px-2 py-1 rounded text-xs font-bold">CRITICAL</span>
                                       ) : isLow ? (
                                           <span className="bg-yellow-100 text-yellow-700 px-2 py-1 rounded text-xs font-bold">LOW</span>
                                       ) : (
                                           <span className="bg-green-100 text-green-700 px-2 py-1 rounded text-xs font-bold">GOOD</span>
                                       )}
                                   </td>
                                   <td className="p-4 flex gap-2">
                                       <button 
                                        onClick={() => updateStock(item.id, item.stock + 10)}
                                        className="p-1 hover:bg-medical-50 text-medical-600 rounded" title="Restock"
                                       >
                                           <RefreshCw size={18} />
                                       </button>
                                   </td>
                               </tr>
                           )
                       })}
                   </tbody>
               </table>
           </div>
       </div>
    </div>
  );
};
