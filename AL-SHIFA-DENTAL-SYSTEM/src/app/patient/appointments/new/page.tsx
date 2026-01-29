"use client";
import { useEffect, useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Building2, User, Calendar, ArrowLeft, Stethoscope, Clock } from "lucide-react";
import { useRouter } from "next/navigation";
import { PatientAPI, AuthAPI, api } from "@/lib/api";

export default function NewBookingPage() {
  const router = useRouter();
  const [step, setStep] = useState(1);
  const [hospitals, setHospitals] = useState<any[]>([]);
  const [doctors, setDoctors] = useState<any[]>([]);
  const [treatments, setTreatments] = useState<any[]>([]); // Store Doctor Treatments
  const [selHosp, setSelHosp] = useState<any>(null);
  const [selDoc, setSelDoc] = useState<any>(null);
  const [availableSlots, setAvailableSlots] = useState<string[]>([]);
  const [form, setForm] = useState({ date: "", time: "", reason: "" });

  useEffect(() => {
    AuthAPI.getVerifiedHospitals().then(res => setHospitals(res.data));
    PatientAPI.getDoctors().then(res => setDoctors(res.data));
  }, []);

  useEffect(() => {
    if (selDoc) {
      // 1. Fetch Doctor Treatments for the Dropdown
      PatientAPI.getDoctorTreatments(selDoc.id)
        .then(res => setTreatments(res.data))
        .catch(err => console.error("Error fetching treatments", err));

      // 2. Fetch Doctor Schedule Settings
      api.get(`/doctors/${selDoc.id}/settings`)
         .then(res => generateTimeSlots(res.data.work_start_time, res.data.work_end_time, res.data.slot_duration))
         .catch(() => generateTimeSlots("09:00", "17:00", 30));
    }
  }, [selDoc]);

  const generateTimeSlots = (start: string, end: string, duration: number) => {
      const slots = [];
      const startTime = new Date(`1970-01-01T${start}:00`);
      const endTime = new Date(`1970-01-01T${end}:00`);
      while (startTime < endTime) {
          slots.push(startTime.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: true }));
          startTime.setMinutes(startTime.getMinutes() + duration);
      }
      setAvailableSlots(slots);
  };

  const submit = async () => {
    if (!form.reason || form.reason === "Select Treatment") {
        alert("Please select a reason for the visit.");
        return;
    }
    try {
      await PatientAPI.bookAppointment({ doctor_id: selDoc.id, date: form.date, time: form.time, reason: form.reason });
      alert("Booked Successfully!"); router.push("/patient/dashboard");
    } catch (e: any) { alert("Booking failed: " + (e.response?.data?.detail || "Unknown error")); }
  };

  return (
    <div className="max-w-3xl mx-auto pt-10 p-6 animate-in fade-in duration-700">
      <Button variant="ghost" onClick={() => {
          if(step > 1) setStep(step - 1);
          else router.back();
      }} className="mb-4 text-slate-500"><ArrowLeft className="h-4 w-4 mr-2"/> Back</Button>
      
      <div className="text-center mb-8">
        <h1 className="text-3xl font-bold text-slate-800">Book Appointment</h1>
        <p className="text-slate-500">Select a hospital, doctor, and treatment plan.</p>
      </div>

      <Card className="shadow-xl border-slate-200">
        <CardContent className="p-8">
            {/* STEP 1: HOSPITAL */}
            {step === 1 && (
                <div className="space-y-4">
                    <p className="font-bold text-slate-500 text-sm uppercase tracking-wider">Step 1: Choose Hospital</p>
                    <div className="grid gap-3">
                    {hospitals.map(h => (
                        <div key={h.id} onClick={() => { setSelHosp(h); setStep(2); }} className="border p-4 rounded-xl hover:border-blue-500 hover:bg-blue-50 cursor-pointer flex gap-4 items-center transition-all">
                            <div className="h-10 w-10 bg-blue-100 rounded-full flex items-center justify-center text-blue-600"><Building2 className="h-5 w-5"/></div>
                            <div><div className="font-bold text-lg">{h.name}</div><div className="text-sm text-slate-500">{h.address}</div></div>
                        </div>
                    ))}
                    </div>
                </div>
            )}
            
            {/* STEP 2: DOCTOR */}
            {step === 2 && (
                <div className="space-y-4">
                    <div className="flex justify-between items-center">
                        <p className="font-bold text-slate-500 text-sm uppercase tracking-wider">Step 2: Choose Doctor</p>
                        <Button variant="link" onClick={() => setStep(1)} className="text-xs">Change Hospital</Button>
                    </div>
                    <div className="grid gap-3">
                    {doctors.filter(d => d.hospital_id === selHosp.id).map(d => (
                        <div key={d.id} onClick={() => { setSelDoc(d); setStep(3); }} className="border p-4 rounded-xl hover:border-purple-500 hover:bg-purple-50 cursor-pointer flex gap-4 items-center transition-all">
                            <div className="h-10 w-10 bg-purple-100 rounded-full flex items-center justify-center text-purple-600"><User className="h-5 w-5"/></div>
                            <div><div className="font-bold text-lg">{d.full_name}</div><div className="text-sm text-slate-500">{d.specialization}</div></div>
                        </div>
                    ))}
                    {doctors.filter(d => d.hospital_id === selHosp.id).length === 0 && <p className="text-center text-slate-500 py-4">No doctors found at this hospital.</p>}
                    </div>
                </div>
            )}
            
            {/* STEP 3: DETAILS */}
            {step === 3 && (
                <div className="space-y-6">
                    <div className="flex justify-between items-center">
                         <p className="font-bold text-slate-500 text-sm uppercase tracking-wider">Step 3: Final Details</p>
                         <Button variant="link" onClick={() => setStep(2)} className="text-xs">Change Doctor</Button>
                    </div>
                    
                    <div className="grid grid-cols-2 gap-6">
                        <div>
                            <label className="text-xs font-bold text-slate-600 mb-2 block flex items-center gap-1"><Calendar className="h-3 w-3"/> Date</label>
                            <input type="date" className="border p-3 rounded-lg w-full outline-none focus:ring-2 focus:ring-blue-500 text-slate-700" onChange={e => setForm({...form, date: e.target.value})}/>
                        </div>
                        <div>
                            <label className="text-xs font-bold text-slate-600 mb-2 block flex items-center gap-1"><Clock className="h-3 w-3"/> Time</label>
                            <select className="border p-3 rounded-lg w-full bg-white outline-none focus:ring-2 focus:ring-blue-500 text-slate-700" onChange={e => setForm({...form, time: e.target.value})}>
                                <option>Select Slot</option>{availableSlots.map(t => <option key={t}>{t}</option>)}
                            </select>
                        </div>
                    </div>
                    
                    {/* TREATMENT DROPDOWN */}
                    <div>
                        <label className="text-xs font-bold text-slate-600 mb-2 block flex items-center gap-1"><Stethoscope className="h-3 w-3"/> Reason / Treatment</label>
                        <select 
                            className="border p-3 rounded-lg w-full bg-white outline-none focus:ring-2 focus:ring-blue-500 text-slate-700"
                            onChange={e => setForm({...form, reason: e.target.value})}
                        >
                            <option>Select Treatment</option>
                            {treatments.length > 0 ? (
                                treatments.map((t: any) => (
                                    <option key={t.id} value={t.name}>
                                        {t.name} (Rs. {t.cost})
                                    </option>
                                ))
                            ) : (
                                // Fallback if no treatments found (e.g. general checkup)
                                <>
                                    <option value="General Checkup">General Checkup</option>
                                    <option value="Consultation">Consultation</option>
                                </>
                            )}
                        </select>
                    </div>

                    <Button onClick={submit} className="w-full bg-blue-600 hover:bg-blue-700 text-lg h-12 shadow-lg shadow-blue-200 font-bold">
                        Confirm Appointment
                    </Button>
                </div>
            )}
        </CardContent>
      </Card>
    </div>
  );
}
