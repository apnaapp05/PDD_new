"use client";
import { useEffect, useState, useRef } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { 
  Plus, Search, AlertTriangle, CheckCircle2, Package, RefreshCcw, 
  ArrowUpCircle, ArrowDownCircle, Upload, X 
} from "lucide-react";
import { DoctorAPI, api } from "@/lib/api";
import { useRouter } from "next/navigation";

interface InventoryItem {
  id: number;
  name: string;
  quantity: number;
  unit: string;
  min_threshold: number;
  last_updated: string;
}

export default function InventoryPage() {
  const router = useRouter();
  const [items, setItems] = useState<InventoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  
  // Modal State
  const [showAddModal, setShowAddModal] = useState(false);
  const [newItem, setNewItem] = useState({ name: "", quantity: "", unit: "Pcs", min_threshold: "10" });
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const fetchInventory = async () => {
    setLoading(true);
    const token = localStorage.getItem("token");
    if (!token) return router.push("/auth/doctor/login");

    try {
      const res = await DoctorAPI.getInventory();
      setItems(res.data);
    } catch (error) {
      console.error("Failed to load inventory", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchInventory(); }, []);

  // --- ACTIONS ---

  const handleAddItem = async () => {
    if (!newItem.name || !newItem.quantity) return alert("Please fill details");
    try {
        await api.post("/doctor/inventory", {
            name: newItem.name,
            quantity: parseInt(newItem.quantity),
            unit: newItem.unit,
            min_threshold: parseInt(newItem.min_threshold)
        });
        setShowAddModal(false);
        setNewItem({ name: "", quantity: "", unit: "Pcs", min_threshold: "10" });
        fetchInventory();
    } catch(e) { alert("Failed to add item"); }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files || e.target.files.length === 0) return;
    const file = e.target.files[0];
    setUploading(true);
    
    const formData = new FormData();
    formData.append("file", file);

    try {
        await api.post("/doctor/inventory/upload", formData, {
            headers: { "Content-Type": "multipart/form-data" }
        });
        alert("CSV Uploaded Successfully!");
        fetchInventory();
    } catch (error) {
        alert("Upload failed. Ensure CSV has 'Item Name' and 'Quantity' columns.");
    } finally {
        setUploading(false);
        if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const updateStock = async (id: number, currentQty: number, change: number) => {
    const newQty = currentQty + change;
    if (newQty < 0) return alert("Cannot reduce below 0");
    try {
        await DoctorAPI.updateStock(id, newQty);
        fetchInventory();
    } catch(e) { alert("Failed to update"); }
  };

  const filteredItems = items.filter(i => 
    i.name.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="space-y-6 animate-in fade-in duration-500 relative">
      
      {/* HEADER ACTIONS */}
      <div className="flex flex-col md:flex-row justify-between md:items-center gap-4">
        <div>
            <h1 className="text-2xl font-bold text-slate-900">Inventory Management</h1>
            <p className="text-slate-500">Track supplies, low stock alerts, and procurement.</p>
        </div>
        <div className="flex gap-2">
            <Button variant="outline" onClick={fetchInventory}><RefreshCcw className="mr-2 h-4 w-4"/> Refresh</Button>
            
            <input 
                type="file" 
                ref={fileInputRef} 
                className="hidden" 
                accept=".csv" 
                onChange={handleFileUpload} 
            />
            <Button variant="secondary" onClick={() => fileInputRef.current?.click()} disabled={uploading}>
                <Upload className="mr-2 h-4 w-4" /> {uploading ? "Uploading..." : "Import CSV"}
            </Button>

            <Button className="bg-indigo-600 hover:bg-indigo-700" onClick={() => setShowAddModal(true)}>
                <Plus className="mr-2 h-4 w-4" /> Add Item
            </Button>
        </div>
      </div>

      {/* SEARCH */}
      <Card>
        <CardContent className="p-4">
            <div className="relative">
                <Search className="absolute left-3 top-3 h-4 w-4 text-slate-400" />
                <Input 
                    placeholder="Search supplies..." 
                    className="pl-10"
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                />
            </div>
        </CardContent>
      </Card>

      {/* TABLE */}
      <Card>
        <CardHeader><CardTitle>Stock List</CardTitle></CardHeader>
        <CardContent className="p-0">
            <div className="overflow-x-auto">
                <table className="w-full text-sm text-left">
                    <thead className="bg-slate-50 text-slate-500 uppercase text-xs font-bold">
                        <tr>
                            <th className="p-4">Item Name</th>
                            <th className="p-4">Quantity</th>
                            <th className="p-4">Unit</th>
                            <th className="p-4">Threshold</th>
                            <th className="p-4">Status</th>
                            <th className="p-4 text-center">Quick Action</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                        {loading ? (
                            <tr><td colSpan={6} className="p-8 text-center text-slate-500">Loading inventory...</td></tr>
                        ) : filteredItems.length === 0 ? (
                            <tr><td colSpan={6} className="p-8 text-center text-slate-500">No items found.</td></tr>
                        ) : (
                            filteredItems.map((item) => {
                                const isLow = item.quantity <= item.min_threshold;
                                return (
                                    <tr key={item.id} className="hover:bg-slate-50 transition-colors">
                                        <td className="p-4 font-medium text-slate-900 flex items-center gap-3">
                                            <div className="p-2 bg-slate-100 rounded-lg text-slate-500">
                                                <Package className="h-4 w-4" />
                                            </div>
                                            {item.name}
                                        </td>
                                        <td className="p-4 font-bold text-slate-800 text-base">{item.quantity}</td>
                                        <td className="p-4 text-slate-500">{item.unit}</td>
                                        <td className="p-4 text-slate-400">Min: {item.min_threshold}</td>
                                        <td className="p-4">
                                            {isLow ? (
                                                <span className="flex items-center gap-1.5 text-red-600 bg-red-50 px-2.5 py-1 rounded-full text-xs font-bold border border-red-100 w-fit">
                                                    <AlertTriangle className="h-3 w-3" /> Low Stock
                                                </span>
                                            ) : (
                                                <span className="flex items-center gap-1.5 text-green-600 bg-green-50 px-2.5 py-1 rounded-full text-xs font-bold border border-green-100 w-fit">
                                                    <CheckCircle2 className="h-3 w-3" /> Healthy
                                                </span>
                                            )}
                                        </td>
                                        <td className="p-4">
                                            <div className="flex justify-center gap-1">
                                                <Button size="icon" variant="ghost" className="h-8 w-8 text-green-600 hover:bg-green-50" onClick={() => updateStock(item.id, item.quantity, 1)}>
                                                    <ArrowUpCircle className="h-5 w-5" />
                                                </Button>
                                                <Button size="icon" variant="ghost" className="h-8 w-8 text-red-500 hover:bg-red-50" onClick={() => updateStock(item.id, item.quantity, -1)}>
                                                    <ArrowDownCircle className="h-5 w-5" />
                                                </Button>
                                            </div>
                                        </td>
                                    </tr>
                                );
                            })
                        )}
                    </tbody>
                </table>
            </div>
        </CardContent>
      </Card>

      {/* ADD ITEM MODAL OVERLAY */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4 backdrop-blur-sm">
            <Card className="w-full max-w-md shadow-2xl relative animate-in fade-in zoom-in duration-200">
                <Button variant="ghost" size="icon" className="absolute right-2 top-2 text-slate-400 hover:text-slate-600" onClick={() => setShowAddModal(false)}>
                    <X className="h-4 w-4" />
                </Button>
                <CardHeader>
                    <CardTitle>Add New Item</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                    <div>
                        <label className="text-sm font-medium text-slate-700">Item Name</label>
                        <Input value={newItem.name} onChange={e => setNewItem({...newItem, name: e.target.value})} placeholder="e.g. Surgical Gloves" />
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                        <div>
                            <label className="text-sm font-medium text-slate-700">Quantity</label>
                            <Input type="number" value={newItem.quantity} onChange={e => setNewItem({...newItem, quantity: e.target.value})} placeholder="0" />
                        </div>
                        <div>
                            <label className="text-sm font-medium text-slate-700">Unit</label>
                            <Input value={newItem.unit} onChange={e => setNewItem({...newItem, unit: e.target.value})} placeholder="Box" />
                        </div>
                    </div>
                    <div>
                        <label className="text-sm font-medium text-slate-700">Low Stock Threshold</label>
                        <Input type="number" value={newItem.min_threshold} onChange={e => setNewItem({...newItem, min_threshold: e.target.value})} placeholder="10" />
                        <p className="text-xs text-slate-500 mt-1">Alert when stock drops below this.</p>
                    </div>
                    <Button className="w-full bg-indigo-600 hover:bg-indigo-700 mt-2" onClick={handleAddItem}>
                        Save Item
                    </Button>
                </CardContent>
            </Card>
        </div>
      )}

    </div>
  );
}
