"use client";
import { useEffect, useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Building2, User, Calendar, ArrowLeft, Stethoscope, Clock, Loader2, AlertCircle } from "lucide-react";
import { useRouter } from "next/navigation";
import { PatientAPI, AuthAPI, api } from "@/lib/api";

export default function NewBookingPage() {
  const router = useRouter();
  const [step, setStep] = useState(1);
  const [hospitals, setHospitals] = useState<any[]>([]);
  const [doctors, setDoctors] = useState<any[]>([]);
  const [treatments, setTreatments] = useState<any[]>([]); 
  const [selHosp, setSelHosp] = useState<any>(null);
  const [selDoc, setSelDoc] = useState<any>(null);
  
  const [availableSlots, setAvailableSlots] = useState<string[]>([]);
  const [isLoadingSlots, setIsLoadingSlots] = useState(false);
  const [slotError, setSlotError] = useState("");
  
  const [form, setForm] = useState({ date: "", time: "", reason: "" });

  useEffect(() => {
    AuthAPI.getVerifiedHospitals().then(res => setHospitals(res.data));
    PatientAPI.getDoctors().then(res => setDoctors(res.data));
  }, []);

  useEffect(() => {
    if (selDoc) {
      PatientAPI.getDoctorTreatments(selDoc.id)
        .then(res => setTreatments(res.data))
        .catch(err => console.error("Error fetching treatments", err));
    }
  }, [selDoc]);

  // --- STANDARD DATE LOGIC ---
  useEffect(() => {
    if (selDoc && form.date) {
        setIsLoadingSlots(true);
        setAvailableSlots([]); 
        setSlotError("");
        setForm(prev => ({ ...prev, time: "" })); 

        api.get(`/doctors/${selDoc.id}/booked-slots?date=${form.date}`)
           .then(res => {
               const blocked = res.data || [];
               api.get(`/doctors/${selDoc.id}/settings`)
                 .then(s => {
                     generateTimeSlots(s.data.work_start_time, s.data.work_end_time, s.data.slot_duration, blocked);
                     setIsLoadingSlots(false);
                 })
                 .catch(() => {
                     generateTimeSlots("09:00", "17:00", 30, blocked);
                     setIsLoadingSlots(false);
                 });
           })
           .catch(err => {
               console.error("Error fetching slots", err);
               setSlotError("Could not load schedule. Try another date.");
               setIsLoadingSlots(false);
           });
    }
  }, [form.date, selDoc]);

  const generateTimeSlots = (start: string, end: string, duration: number, blocked: string[]) => {
      const toMinutes = (time: string) => {
          const [h, m] = time.split(":").map(Number);
          return h * 60 + m;
      };

      const toTimeStr = (totalMinutes: number) => {
          const h = Math.floor(totalMinutes / 60);
          const m = totalMinutes % 60;
          const ampm = h >= 12 ? "PM" : "AM";
          const hour12 = h % 12 || 12; 
          return `${hour12.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')} ${ampm}`;
      };

      const startMin = toMinutes(start);
      const endMin = toMinutes(end);
      const validSlots = [];

      const normalize = (t: string) => t.replace(/[^a-zA-Z0-9]/g, "").replace(/^0+/, "").toUpperCase();
      const normalizedBlocked = blocked.map(normalize);

      for (let time = startMin; time < endMin; time += duration) {
          const slotLabel = toTimeStr(time);
          const compareKey = normalize(slotLabel);
          
          if (!normalizedBlocked.includes(compareKey)) {
              validSlots.push(slotLabel);
          }
      }

      setAvailableSlots(validSlots);
      if (validSlots.length === 0) setSlotError("No available slots for this date.");
  };

  const submit = async () => {
    if (!form.reason || form.reason === "Select Treatment") { alert("Please select a reason."); return; }
    if (!form.time || form.time === "Select Slot") { alert("Please select a time slot."); return; }
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
                    </div>
                </div>
            )}
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
                            <select className={`border p-3 rounded-lg w-full outline-none focus:ring-2 focus:ring-blue-500 text-slate-700 ${(!form.date || slotError) ? 'bg-slate-100 text-slate-500 cursor-not-allowed' : 'bg-white'}`} disabled={!form.date || isLoadingSlots || slotError !== ""} onChange={e => setForm({...form, time: e.target.value})} value={form.time}>
                                <option value="">{!form.date ? "Select Date First" : isLoadingSlots ? "Checking availability..." : slotError ? slotError : "Select Slot"}</option>
                                {!isLoadingSlots && !slotError && availableSlots.length > 0 && availableSlots.map(t => <option key={t} value={t}>{t}</option>)}
                            </select>
                            {isLoadingSlots && <div className="text-xs text-blue-500 mt-1 flex items-center"><Loader2 className="h-3 w-3 animate-spin mr-1"/> finding slots...</div>}
                            {slotError && <div className="text-xs text-red-500 mt-1 flex items-center"><AlertCircle className="h-3 w-3 mr-1"/> {slotError}</div>}
                        </div>
                    </div>
                    <div>
                        <label className="text-xs font-bold text-slate-600 mb-2 block flex items-center gap-1"><Stethoscope className="h-3 w-3"/> Reason / Treatment</label>
                        <select className="border p-3 rounded-lg w-full bg-white outline-none focus:ring-2 focus:ring-blue-500 text-slate-700" onChange={e => setForm({...form, reason: e.target.value})}>
                            <option>Select Treatment</option>
                            {treatments.length > 0 ? (treatments.map((t: any) => <option key={t.id} value={t.name}>{t.name} (Rs. {t.cost})</option>)) : (<><option value="General Checkup">General Checkup</option><option value="Consultation">Consultation</option></>)}
                        </select>
                    </div>
                    <Button onClick={submit} disabled={isLoadingSlots || availableSlots.length === 0} className="w-full bg-blue-600 hover:bg-blue-700 text-lg h-12 shadow-lg shadow-blue-200 font-bold disabled:opacity-50 disabled:cursor-not-allowed">Confirm Appointment</Button>
                </div>
            )}
        </CardContent>
      </Card>
    </div>
  );
}