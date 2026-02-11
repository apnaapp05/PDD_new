"use client";
import { useEffect, useState } from "react";
import { AdminAPI } from "@/lib/api";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Trash2, Eye, User, Calendar, Phone, MapPin, Loader2, Users, Search } from "lucide-react";
import { Modal } from "@/components/ui/modal";
import { Input } from "@/components/ui/input";

export default function AdminPatients() {
  const [patients, setPatients] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");

  // State for Profile Modal
  const [selectedPatient, setSelectedPatient] = useState<any>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [detailsLoading, setDetailsLoading] = useState(false);

  const fetchPatients = async () => {
    try {
      const res = await AdminAPI.getPatients();
      setPatients(res.data);
    } catch (error) {
      console.error("Failed to load patients", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPatients();
  }, []);

  const handleDelete = async (id: number) => {
    if (!confirm("Are you sure you want to delete this patient?")) return;
    try {
      await AdminAPI.deleteEntity(id, "patient");
      fetchPatients();
    } catch (error) {
      alert("Failed to delete patient");
    }
  };

  const openProfile = async (id: number) => {
    setIsModalOpen(true);
    setDetailsLoading(true);
    try {
      const res = await AdminAPI.getPatientDetails(id);
      setSelectedPatient(res.data);
    } catch (error) {
      console.error("Failed to fetch details", error);
      alert("Could not fetch patient details.");
      setIsModalOpen(false);
    } finally {
      setDetailsLoading(false);
    }
  };

  const filteredPatients = patients.filter(p =>
    p.name.toLowerCase().includes(search.toLowerCase()) ||
    p.email.toLowerCase().includes(search.toLowerCase()) ||
    p.id.toString().includes(search)
  );

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      <div className="flex justify-between items-center bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Manage Patients</h1>
          <p className="text-sm text-slate-500">View and manage registered patients</p>
        </div>
        <div className="relative w-72">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
          <Input
            placeholder="Search patient..."
            className="pl-9 bg-slate-50 border-slate-200 focus:bg-white"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
      </div>

      {loading ? (
        <div className="flex justify-center py-20"><Loader2 className="animate-spin text-slate-400 h-8 w-8" /></div>
      ) : filteredPatients.length === 0 ? (
        <div className="text-center py-20 bg-white rounded-xl border border-dashed border-slate-300">
          <Users className="h-12 w-12 text-slate-300 mx-auto mb-3" />
          <p className="text-slate-500">No patients found.</p>
        </div>
      ) : (
        <div className="grid gap-4">
          {filteredPatients.map((p) => (
            <Card key={p.id} className="p-4 flex items-center justify-between hover:shadow-md transition-shadow">
              <div>
                <h3 className="font-bold text-lg text-slate-900">{p.name}</h3>
                <p className="text-slate-500 text-sm">{p.email}</p>
                <div className="flex gap-4 mt-1 text-xs text-slate-400">
                  <span className="bg-slate-100 px-2 py-0.5 rounded text-slate-600 font-mono">ID: #{p.id}</span>
                  <span>Age: {p.age || "N/A"}</span>
                  <span>Gender: {p.gender || "N/A"}</span>
                </div>
              </div>
              <div className="flex gap-2">
                <Button variant="outline" size="sm" onClick={() => openProfile(p.id)}>
                  <Eye className="h-4 w-4 mr-2" />
                  View Profile
                </Button>
                <Button variant="destructive" size="sm" onClick={() => handleDelete(p.id)}>
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* Patient Profile Modal */}
      <Modal isOpen={isModalOpen} onClose={() => setIsModalOpen(false)} title="Patient Profile">
        {detailsLoading ? (
          <div className="p-4 text-center">Loading details...</div>
        ) : selectedPatient ? (
          <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center gap-4 pb-4 border-b">
              <div className="h-16 w-16 bg-blue-100 rounded-full flex items-center justify-center">
                <User className="h-8 w-8 text-blue-600" />
              </div>
              <div>
                <h2 className="text-xl font-bold">{selectedPatient.full_name}</h2>
                <p className="text-slate-500">{selectedPatient.email}</p>
              </div>
            </div>

            {/* Details Grid */}
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1">
                <p className="text-xs font-bold text-slate-400 uppercase">Phone</p>
                <div className="flex items-center gap-2 text-slate-700">
                  <Phone className="h-4 w-4" /> {selectedPatient.phone}
                </div>
              </div>
              <div className="space-y-1">
                <p className="text-xs font-bold text-slate-400 uppercase">Address</p>
                <div className="flex items-center gap-2 text-slate-700">
                  <MapPin className="h-4 w-4" /> {selectedPatient.address}
                </div>
              </div>
              <div className="space-y-1">
                <p className="text-xs font-bold text-slate-400 uppercase">Age / Gender</p>
                <div className="flex items-center gap-2 text-slate-700">
                  <Calendar className="h-4 w-4" /> {selectedPatient.age} Y / {selectedPatient.gender}
                </div>
              </div>
              <div className="space-y-1">
                <p className="text-xs font-bold text-slate-400 uppercase">Blood Group</p>
                <p className="text-slate-700 font-medium">{selectedPatient.blood_group}</p>
              </div>
            </div>

            {/* Medical History Preview */}
            <div className="pt-4 border-t">
              <h3 className="font-semibold text-slate-800 mb-2">Recent Medical History</h3>
              {selectedPatient.history && selectedPatient.history.length > 0 ? (
                <ul className="space-y-2">
                  {selectedPatient.history.slice(0, 3).map((rec: any, i: number) => (
                    <li key={i} className="text-sm p-2 bg-slate-50 rounded border">
                      <span className="font-bold block">{rec.diagnosis}</span>
                      <span className="text-xs text-slate-500">{new Date(rec.date).toLocaleDateString()} • Dr. {rec.doctor}</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-sm text-slate-400 italic">No medical records found.</p>
              )}
            </div>
          </div>
        ) : (
          <p>No data available.</p>
        )}
      </Modal>
    </div>
  );
}