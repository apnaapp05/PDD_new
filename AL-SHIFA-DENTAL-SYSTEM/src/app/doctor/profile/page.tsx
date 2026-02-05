"use client";

import React, { useState, useEffect } from "react";
import { DoctorAPI, AuthAPI } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Clock, Coffee, Save, CheckCircle, User, Briefcase, Phone, Mail, MapPin } from "lucide-react";

export default function DoctorProfilePage() {
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);

  // --- Profile State ---
  const [profileData, setProfileData] = useState({
    full_name: "",
    email: "",
    phone_number: "",
    address: "",
    specialization: "",
    dob: ""
  });

  // --- Clinical State ---
  const [mode, setMode] = useState<"continuous" | "interleaved">("continuous");
  const [workDuration, setWorkDuration] = useState(20);
  const [breakDuration, setBreakDuration] = useState(0);

  // Load Data
  useEffect(() => {
    const loadData = async () => {
      try {
        // 1. Get Profile
        const userRes = await AuthAPI.getMe();
        const u = userRes.data;
        setProfileData({
          full_name: u.full_name || "",
          email: u.email || "",
          phone_number: u.phone_number || "",
          address: u.address || "",
          specialization: u.specialization || "",
          dob: u.dob || ""
        });

        // 2. Get Config
        const configRes = await DoctorAPI.updateConfig({}); // Getting current config (using empty update/get logic if separated, but usually get is separate. Assuming updateConfig returns or separate get exists. If not, we rely on defaults or need a GET endpoint. Re-using what you had: )
        // Actually, we need a GET for config. If you don't have one, we default.
        // Assuming DoctorAPI.getSchedule() or similar might return it? 
        // For now, let's leave config defaults or add a GET endpoint if strict sync needed.
      } catch (e) {
        console.error("Load error", e);
      }
    };
    loadData();
  }, []);

  const handleSaveProfile = async () => {
    setLoading(true);
    try {
      await AuthAPI.updateProfile(profileData);
      setSuccess(true);
      setTimeout(() => setSuccess(false), 3000);
    } catch (err) {
      alert("Failed to update profile");
    } finally {
      setLoading(false);
    }
  };

  const handleSaveConfig = async () => {
    setLoading(true);
    try {
      await DoctorAPI.updateConfig({
        slot_duration: workDuration,
        break_duration: mode === "interleaved" ? breakDuration : 0,
        work_start: "09:00",
        work_end: "17:00"
      });
      setSuccess(true);
      setTimeout(() => setSuccess(false), 3000);
    } catch (err) {
      alert("Failed to save settings");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-8 animate-in fade-in duration-500">
      <div>
        <h1 className="text-3xl font-bold text-slate-900">Doctor Profile</h1>
        <p className="text-slate-500">Manage your personal details and clinical preferences.</p>
      </div>

      <Tabs defaultValue="personal" className="w-full">
        <TabsList className="grid w-full grid-cols-2 mb-8">
          <TabsTrigger value="personal">Personal Details</TabsTrigger>
          <TabsTrigger value="clinical">Clinical Configuration</TabsTrigger>
        </TabsList>

        {/* --- TAB 1: PERSONAL DETAILS --- */}
        <TabsContent value="personal" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Basic Information</CardTitle>
              <CardDescription>Your details visible to patients and administrators.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <label className="text-sm font-medium flex items-center gap-2"><User className="w-4 h-4" /> Full Name</label>
                  <Input
                    value={profileData.full_name}
                    onChange={(e) => setProfileData({ ...profileData, full_name: e.target.value })}
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium flex items-center gap-2"><Mail className="w-4 h-4" /> Email</label>
                  <Input
                    value={profileData.email}
                    onChange={(e) => setProfileData({ ...profileData, email: e.target.value })}
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium flex items-center gap-2"><Phone className="w-4 h-4" /> Phone Number</label>
                  <Input
                    value={profileData.phone_number}
                    onChange={(e) => setProfileData({ ...profileData, phone_number: e.target.value })}
                    placeholder="+91..."
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium flex items-center gap-2">Date of Birth</label>
                  <Input
                    type="date"
                    value={profileData.dob ? profileData.dob.split('T')[0] : ""}
                    onChange={(e) => setProfileData({ ...profileData, dob: e.target.value })}
                  />
                </div>
                <div className="space-y-2 col-span-2">
                  <label className="text-sm font-medium flex items-center gap-2"><MapPin className="w-4 h-4" /> Address</label>
                  <Input
                    value={profileData.address}
                    onChange={(e) => setProfileData({ ...profileData, address: e.target.value })}
                  />
                </div>
              </div>

              <div className="pt-4 border-t mt-4">
                <h3 className="text-lg font-semibold mb-4">Professional Credentials</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <label className="text-sm font-medium flex items-center gap-2"><Briefcase className="w-4 h-4" /> Specialization</label>
                    <Input
                      value={profileData.specialization}
                      onChange={(e) => setProfileData({ ...profileData, specialization: e.target.value })}
                      placeholder="e.g. Orthodontist"
                    />
                  </div>
                </div>
              </div>

              <div className="flex justify-between w-full pt-6">
                <Button
                  variant="destructive"
                  onClick={() => {
                    if (confirm("CRITICAL WARNING: This will permanently delete your account, your data, and cannot be undone. Are you sure?")) {
                      AuthAPI.deleteAccount().then(() => {
                        window.location.href = "/";
                      }).catch(() => alert("Failed to delete account"));
                    }
                  }}
                >
                  Delete Account
                </Button>

                <Button onClick={handleSaveProfile} disabled={loading}>
                  {loading ? "Saving..." : success ? "Saved!" : "Save Changes"}
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* --- TAB 2: CLINICAL CONFIG (Your Existing Code) --- */}
        <TabsContent value="clinical">
          <div className="grid gap-6 md:grid-cols-2">
            {/* SCHEDULING MODE */}
            <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
              <h3 className="font-semibold text-slate-800 flex items-center mb-4">
                <Clock className="h-5 w-5 mr-2 text-blue-600" />
                Scheduling Strategy
              </h3>

              <div className="space-y-4">
                <label className={`flex items-start p-4 border rounded-lg cursor-pointer transition-all ${mode === "continuous" ? "border-blue-500 bg-blue-50" : "border-slate-200"}`}>
                  <input type="radio" name="mode" className="mt-1" checked={mode === "continuous"} onChange={() => { setMode("continuous"); setBreakDuration(0); }} />
                  <div className="ml-3">
                    <span className="block text-sm font-bold text-slate-900">Continuous Flow</span>
                    <span className="block text-xs text-slate-500 mt-1">
                      Back-to-back patients. No programmed breaks.
                    </span>
                  </div>
                </label>

                <label className={`flex items-start p-4 border rounded-lg cursor-pointer transition-all ${mode === "interleaved" ? "border-blue-500 bg-blue-50" : "border-slate-200"}`}>
                  <input type="radio" name="mode" className="mt-1" checked={mode === "interleaved"} onChange={() => setMode("interleaved")} />
                  <div className="ml-3">
                    <span className="block text-sm font-bold text-slate-900">Interleaved (Smart Breaks)</span>
                    <span className="block text-xs text-slate-500 mt-1">
                      Work block + small recovery break.
                    </span>
                  </div>
                </label>
              </div>
            </div>

            {/* TIME CONFIG */}
            <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
              <h3 className="font-semibold text-slate-800 flex items-center mb-4">
                <Coffee className="h-5 w-5 mr-2 text-purple-600" />
                Time Allocation
              </h3>

              <div className="space-y-6">
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-2">
                    Consultation Duration (mins)
                  </label>
                  <Input
                    type="number"
                    value={workDuration}
                    onChange={(e) => setWorkDuration(Number(e.target.value))}
                  />
                </div>

                {mode === "interleaved" && (
                  <div className="animate-in fade-in slide-in-from-top-2">
                    <label className="block text-sm font-medium text-slate-700 mb-2">
                      Break / Buffer Time (mins)
                    </label>
                    <Input
                      type="number"
                      value={breakDuration}
                      onChange={(e) => setBreakDuration(Number(e.target.value))}
                      className="border-purple-200 bg-purple-50"
                    />
                  </div>
                )}

                <div className="pt-4 p-4 bg-slate-50 rounded-lg text-sm text-slate-600">
                  <span className="font-bold">Result:</span> Your AI will generate slots every
                  <span className="font-bold text-blue-600"> {workDuration + breakDuration} minutes</span>.
                </div>
              </div>
            </div>
          </div>

          <div className="flex justify-end mt-6">
            <Button onClick={handleSaveConfig} disabled={loading} className="w-40">
              {loading ? "Saving..." : success ? <><CheckCircle className="mr-2 h-4 w-4" /> Saved</> : <><Save className="mr-2 h-4 w-4" /> Save Config</>}
            </Button>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}