"use client";
import { useEffect, useState } from "react";
import { PatientAPI } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Loader2, User, Phone, Mail, Calendar, Droplet, MapPin, Edit2, Save, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

export default function PatientProfile() {
  const [profile, setProfile] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [isEditing, setIsEditing] = useState(false);
  const [formData, setFormData] = useState<any>({});
  const [saveLoading, setSaveLoading] = useState(false);

  const fetchProfile = async () => {
    try {
      const res = await PatientAPI.getProfile();
      setProfile(res.data);
      setFormData(res.data); // Initialize form with current data
    } catch (error) {
      console.error("Failed to load profile", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProfile();
  }, []);

  // In src/app/patient/profile/page.tsx

  const handleSave = async () => {
    setSaveLoading(true);
    try {
      // FIX: Ensure age is a valid number, or 0 if empty
      const safeAge = formData.age ? parseInt(formData.age) : 0;

      const payload = {
        full_name: formData.full_name,
        age: isNaN(safeAge) ? 0 : safeAge, // Prevent NaN error
        gender: formData.gender || "",
        address: formData.address || "",
        blood_group: formData.blood_group || ""
      };
      
      await PatientAPI.updateProfile(payload);
      await fetchProfile(); 
      setIsEditing(false);
    } catch (error) {
      console.error("Failed to update profile", error);
      alert("Failed to update profile. Please try again.");
    } finally {
      setSaveLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex h-[50vh] items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
      </div>
    );
  }

  if (!profile) {
    return (
      <div className="p-8 text-center text-slate-500">
        <p>Could not load profile data.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-in fade-in duration-500 max-w-3xl mx-auto pb-10">
      {/* Header Section */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
        <div className="flex items-center gap-4">
          <div className="h-20 w-20 bg-blue-100 rounded-full flex items-center justify-center border-4 border-white shadow-lg">
            <User className="h-10 w-10 text-blue-600" />
          </div>
          <div>
            <h1 className="text-3xl font-bold text-slate-900">{profile.full_name}</h1>
            <p className="text-slate-500">Patient ID: #{profile.id}</p>
          </div>
        </div>
        
        {!isEditing ? (
          <Button onClick={() => setIsEditing(true)} variant="outline" className="flex items-center gap-2">
            <Edit2 className="h-4 w-4" />
            Edit Profile
          </Button>
        ) : (
          <div className="flex gap-2">
            <Button onClick={() => setIsEditing(false)} variant="ghost" disabled={saveLoading}>
              <X className="h-4 w-4 mr-2" /> Cancel
            </Button>
            <Button onClick={handleSave} disabled={saveLoading} className="bg-blue-600 hover:bg-blue-700">
              {saveLoading ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Save className="h-4 w-4 mr-2" />}
              Save Changes
            </Button>
          </div>
        )}
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        {/* Contact Info Card */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-slate-500 uppercase tracking-wider">Contact Info</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Email (Read Only) */}
            <div className="flex items-center gap-3">
              <Mail className="h-5 w-5 text-blue-500" />
              <div className="w-full">
                <p className="text-sm font-bold text-slate-700">Email Address</p>
                <p className="text-slate-600">{profile.email}</p>
              </div>
            </div>

            {/* Address */}
            <div className="flex items-start gap-3">
              <MapPin className="h-5 w-5 text-red-500 mt-1" />
              <div className="w-full">
                <p className="text-sm font-bold text-slate-700 mb-1">Address</p>
                {isEditing ? (
                  <Input 
                    value={formData.address || ""} 
                    onChange={(e) => setFormData({...formData, address: e.target.value})}
                    placeholder="Enter your address"
                  />
                ) : (
                  <p className="text-slate-600">{profile.address || "Not set"}</p>
                )}
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Personal Details Card */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-slate-500 uppercase tracking-wider">Personal Details</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            
            {/* Name (Editable) */}
            {isEditing && (
               <div className="flex items-center gap-3">
               <User className="h-5 w-5 text-gray-500" />
               <div className="w-full">
                 <p className="text-sm font-bold text-slate-700 mb-1">Full Name</p>
                 <Input 
                   value={formData.full_name} 
                   onChange={(e) => setFormData({...formData, full_name: e.target.value})}
                 />
               </div>
             </div>
            )}

            {/* Age */}
            <div className="flex items-center gap-3">
              <Calendar className="h-5 w-5 text-purple-500" />
              <div className="w-full">
                <p className="text-sm font-bold text-slate-700 mb-1">Age</p>
                {isEditing ? (
                   <Input 
                   type="number"
                   value={formData.age} 
                   onChange={(e) => setFormData({...formData, age: e.target.value})}
                 />
                ) : (
                  <p className="text-slate-600">{profile.age} Years</p>
                )}
              </div>
            </div>

            {/* Gender */}
            <div className="flex items-center gap-3">
              <User className="h-5 w-5 text-orange-500" />
              <div className="w-full">
                <p className="text-sm font-bold text-slate-700 mb-1">Gender</p>
                {isEditing ? (
                  <Select 
                    value={formData.gender} 
                    onValueChange={(val) => setFormData({...formData, gender: val})}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select Gender" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="Male">Male</SelectItem>
                      <SelectItem value="Female">Female</SelectItem>
                      <SelectItem value="Other">Other</SelectItem>
                    </SelectContent>
                  </Select>
                ) : (
                  <p className="text-slate-600">{profile.gender}</p>
                )}
              </div>
            </div>

            {/* Blood Group */}
            <div className="flex items-center gap-3">
              <Droplet className="h-5 w-5 text-red-600" />
              <div className="w-full">
                <p className="text-sm font-bold text-slate-700 mb-1">Blood Group</p>
                {isEditing ? (
                   <Select 
                   value={formData.blood_group || ""} 
                   onValueChange={(val) => setFormData({...formData, blood_group: val})}
                 >
                   <SelectTrigger>
                     <SelectValue placeholder="Select Blood Group" />
                   </SelectTrigger>
                   <SelectContent>
                     <SelectItem value="A+">A+</SelectItem>
                     <SelectItem value="A-">A-</SelectItem>
                     <SelectItem value="B+">B+</SelectItem>
                     <SelectItem value="B-">B-</SelectItem>
                     <SelectItem value="AB+">AB+</SelectItem>
                     <SelectItem value="AB-">AB-</SelectItem>
                     <SelectItem value="O+">O+</SelectItem>
                     <SelectItem value="O-">O-</SelectItem>
                   </SelectContent>
                 </Select>
                ) : (
                  <p className="text-slate-600">{profile.blood_group || "N/A"}</p>
                )}
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}