"use client";
import { useEffect, useState } from "react";
import { AdminAPI } from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Stethoscope, CheckCircle, Search, Loader2, Trash2, Building } from "lucide-react";
import { Input } from "@/components/ui/input";

import { Modal } from "@/components/ui/modal";
import { User, Calendar, Phone, MapPin, Eye } from "lucide-react";

export default function AdminDoctors() {
  const [doctors, setDoctors] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");

  // Modal State
  const [selectedDoc, setSelectedDoc] = useState<any>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [detailsLoading, setDetailsLoading] = useState(false);

  const fetchDocs = async () => {
    setLoading(true);
    try {
      const res = await AdminAPI.getDoctors();
      setDoctors(res.data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDocs();
  }, []);

  const handleVerify = async (id: number) => {
    try {
      await AdminAPI.approveAccount(id, "doctor");
      fetchDocs();
    } catch (e) {
      alert("Failed to verify");
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm("Are you sure? This will delete the doctor's account permanently.")) return;
    try {
      await AdminAPI.deleteEntity(id, "doctor");
      fetchDocs();
    } catch (e) {
      alert("Failed to delete");
    }
  };

  const openProfile = async (id: number) => {
    setIsModalOpen(true);
    setDetailsLoading(true);
    try {
      const res = await AdminAPI.getDoctorDetails(id);
      setSelectedDoc(res.data);
    } catch (error) {
      console.error("Failed to fetch details", error);
      alert("Could not fetch doctor details.");
      setIsModalOpen(false);
    } finally {
      setDetailsLoading(false);
    }
  };

  const filteredDocs = doctors.filter(d =>
    d.name.toLowerCase().includes(search.toLowerCase()) ||
    d.specialization.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      <div className="flex justify-between items-center bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Medical Staff</h1>
          <p className="text-sm text-slate-500">Verification & management of doctors</p>
        </div>
        <div className="relative w-72">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
          <Input
            placeholder="Search doctor..."
            className="pl-9 bg-slate-50 border-slate-200 focus:bg-white"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
      </div>

      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        {loading ? (
          <div className="col-span-full flex justify-center py-20"><Loader2 className="animate-spin text-slate-400 h-8 w-8" /></div>
        ) : filteredDocs.length === 0 ? (
          <div className="col-span-full text-center py-20 bg-white rounded-xl border border-dashed border-slate-300">
            <Stethoscope className="h-12 w-12 text-slate-300 mx-auto mb-3" />
            <p className="text-slate-500">No doctors found.</p>
          </div>
        ) : (
          filteredDocs.map((doc) => (
            <Card key={doc.id} className="p-6 hover:shadow-lg transition-all border-slate-200 group relative overflow-hidden flex flex-col justify-between">

              <div className="absolute top-0 right-0 p-4 opacity-0 group-hover:opacity-100 transition-opacity flex gap-2">
                <Button size="icon" variant="ghost" className="h-8 w-8 text-blue-500 hover:text-blue-700 hover:bg-blue-50" onClick={() => openProfile(doc.id)}>
                  <Eye className="h-4 w-4" />
                </Button>
                <Button size="icon" variant="ghost" className="h-8 w-8 text-red-500 hover:text-red-700 hover:bg-red-50" onClick={() => handleDelete(doc.id)}>
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>

              <div>
                <div className="flex justify-between items-start mb-4 pr-20">
                  <div className="h-12 w-12 bg-indigo-50 rounded-full flex items-center justify-center ring-4 ring-white shadow-sm">
                    <Stethoscope className="h-6 w-6 text-indigo-600" />
                  </div>
                  <span className="flex items-center gap-1 text-[10px] font-bold bg-green-100 text-green-700 px-2 py-1 rounded-full border border-green-200">
                    VERIFIED <CheckCircle className="h-3 w-3" />
                  </span>
                </div>

                <h3 className="font-bold text-lg text-slate-900 line-clamp-1">{doc.name}</h3>
                <p className="text-sm text-indigo-600 font-medium mb-4">{doc.specialization}</p>

                <div className="space-y-2 mb-6">
                  <div className="flex items-center gap-2 text-xs text-slate-500">
                    <Building className="h-3.5 w-3.5 text-slate-400" />
                    <span className="line-clamp-1">{doc.hospital_name}</span>
                  </div>
                </div>
              </div>

              <Button variant="outline" className="w-full text-xs" onClick={() => openProfile(doc.id)}>
                View Profile
              </Button>
            </Card>
          ))
        )}
      </div>

      {/* Doctor Profile Modal */}
      <Modal isOpen={isModalOpen} onClose={() => setIsModalOpen(false)} title="Doctor Profile">
        {detailsLoading ? (
          <div className="p-4 text-center">Loading details...</div>
        ) : selectedDoc ? (
          <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center gap-4 pb-4 border-b">
              <div className="h-16 w-16 bg-blue-100 rounded-full flex items-center justify-center">
                <Stethoscope className="h-8 w-8 text-blue-600" />
              </div>
              <div>
                <h2 className="text-xl font-bold">{selectedDoc.full_name}</h2>
                <p className="text-slate-500">{selectedDoc.email}</p>
                <p className="text-xs text-blue-600 font-bold bg-blue-50 px-2 py-1 rounded-full mt-1 w-fit">{selectedDoc.specialization}</p>
              </div>
            </div>

            {/* Details Grid */}
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1">
                <p className="text-xs font-bold text-slate-400 uppercase">Hospital</p>
                <div className="flex items-center gap-2 text-slate-700">
                  <Building className="h-4 w-4" /> {selectedDoc.hospital_name}
                </div>
              </div>
              <div className="space-y-1">
                <p className="text-xs font-bold text-slate-400 uppercase">Phone</p>
                <div className="flex items-center gap-2 text-slate-700">
                  <Phone className="h-4 w-4" /> {selectedDoc.phone}
                </div>
              </div>
              <div className="space-y-1">
                <p className="text-xs font-bold text-slate-400 uppercase">Date of Birth</p>
                <div className="flex items-center gap-2 text-slate-700">
                  <Calendar className="h-4 w-4" /> {selectedDoc.dob}
                </div>
              </div>

              <div className="col-span-2 space-y-1">
                <p className="text-xs font-bold text-slate-400 uppercase">Address</p>
                <div className="flex items-center gap-2 text-slate-700">
                  <MapPin className="h-4 w-4" /> {selectedDoc.address}
                </div>
              </div>
            </div>
          </div>
        ) : (
          <p>No data available.</p>
        )}
      </Modal>
    </div>
  );
}