"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Loader2, User, AlertCircle } from "lucide-react";
import Link from "next/link";
import { AuthAPI } from "@/lib/api";

export default function PatientSignup() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // Form State
  const [formData, setFormData] = useState({
    name: "",
    email: "",
    password: "",
    confirmPassword: "",
    dob: "",
    phone: "",
    address: "",
    gender: "",
  });

  const [privacyChecked, setPrivacyChecked] = useState(false);
  const [showPrivacy, setShowPrivacy] = useState(false);

  const handleSignup = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    // Validations
    if (formData.password !== formData.confirmPassword) {
      setError("Passwords do not match"); return;
    }
    if (!formData.dob || !formData.gender) {
      setError("Please fill all required fields"); return;
    }
    if (formData.phone.length !== 10) {
      setError("Mobile number must be exactly 10 digits"); return;
    }
    if (!privacyChecked) {
      setError("You must agree to the Privacy Policy"); return;
    }

    // Calculate Age from DOB
    const birthDate = new Date(formData.dob);
    const age = new Date().getFullYear() - birthDate.getFullYear();

    setLoading(true);

    try {
      await AuthAPI.register({
        email: formData.email,
        password: formData.password,
        full_name: formData.name,
        phone_number: formData.phone,
        address: formData.address,
        dob: formData.dob,
        role: "patient",
        age: age, // Backend still expects 'age' for Patient model
        gender: formData.gender
      });

      // 2. Success: Save email for the OTP page
      localStorage.setItem("pending_email", formData.email);

      // 3. Redirect to the Global OTP Page
      router.push("/auth/verify-otp");

    } catch (err: any) {
      console.error(err);
      const detail = err.response?.data?.detail;
      setError(typeof detail === "string" ? detail : "Registration failed. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 flex items-center justify-center p-4">
      <Card className="w-full max-w-lg shadow-lg border-slate-200">
        <CardHeader className="text-center">
          <div className="mx-auto h-12 w-12 bg-blue-100 rounded-full flex items-center justify-center mb-4">
            <User className="h-6 w-6 text-blue-600" />
          </div>
          <CardTitle className="text-2xl font-bold text-slate-900">Patient Registration</CardTitle>
          <CardDescription>Create an account to book appointments</CardDescription>
        </CardHeader>
        <CardContent>

          {error && (
            <div className="mb-4 p-3 bg-red-50 text-red-600 text-sm rounded-md flex items-center gap-2 border border-red-100">
              <AlertCircle className="h-4 w-4" /> {error}
            </div>
          )}

          <form onSubmit={handleSignup} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="name">Full Name</Label>
              <Input
                id="name"
                placeholder="Letters only"
                required
                value={formData.name}
                onChange={(e) => {
                  if (/^[a-zA-Z\s]*$/.test(e.target.value)) setFormData({ ...formData, name: e.target.value });
                }}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="email">Email Address</Label>
              <Input
                id="email"
                type="email"
                placeholder="patient@example.com"
                required
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="dob">Date of Birth</Label>
                <Input
                  id="dob"
                  type="date"
                  required
                  value={formData.dob}
                  onChange={(e) => setFormData({ ...formData, dob: e.target.value })}
                />
              </div>
              <div className="space-y-2">
                <Label>Gender</Label>
                <div className="flex gap-2">
                  {["Male", "Female"].map((g) => (
                    <div
                      key={g}
                      onClick={() => setFormData({ ...formData, gender: g })}
                      className={`flex-1 flex flex-col items-center justify-center p-3 rounded-xl border-2 cursor-pointer transition-all duration-200 ${formData.gender === g
                        ? "border-blue-600 bg-blue-50 text-blue-700 shadow-sm transform scale-105"
                        : "border-slate-100 bg-slate-50 text-slate-500 hover:border-blue-200 hover:bg-white"
                        }`}
                    >
                      <span className="text-sm font-semibold">{g}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="phone">Mobile Number</Label>
                <Input
                  id="phone"
                  type="tel"
                  placeholder="10 digits"
                  required
                  maxLength={10}
                  value={formData.phone}
                  onChange={(e) => {
                    if (/^\d*$/.test(e.target.value)) setFormData({ ...formData, phone: e.target.value });
                  }}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="ageDisplay">Age</Label>
                <Input
                  id="ageDisplay"
                  readOnly
                  value={formData.dob ? new Date().getFullYear() - new Date(formData.dob).getFullYear() : ""}
                  placeholder="Auto-calc"
                  className="bg-slate-50 cursor-not-allowed"
                  tabIndex={-1}
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="address">Address</Label>
              <Input
                id="address"
                placeholder="Full residential address"
                required
                value={formData.address}
                onChange={(e) => setFormData({ ...formData, address: e.target.value })}
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="password">Password</Label>
                <Input
                  id="password"
                  type="password"
                  required
                  value={formData.password}
                  onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="confirm">Confirm Password</Label>
                <Input
                  id="confirm"
                  type="password"
                  required
                  value={formData.confirmPassword}
                  onChange={(e) => setFormData({ ...formData, confirmPassword: e.target.value })}
                />
              </div>
            </div>

            {/* Privacy Policy */}
            <div className="flex items-start space-x-2 pt-2">
              <input
                type="checkbox"
                id="privacy"
                checked={privacyChecked}
                onChange={(e) => setPrivacyChecked(e.target.checked)}
                className="mt-1 h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              <label htmlFor="privacy" className="text-xs text-slate-600 leading-tight">
                I agree to the <button type="button" onClick={() => setShowPrivacy(true)} className="text-blue-600 underline">Privacy Policy</button>, including data collection and processing terms.
              </label>
            </div>

            <Button type="submit" className="w-full bg-blue-600 hover:bg-blue-700 mt-2" disabled={loading}>
              {loading ? <Loader2 className="animate-spin mr-2 h-4 w-4" /> : "Create Account"}
            </Button>
          </form>

          {/* Privacy Modal */}
          {showPrivacy && (
            <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
              <div className="bg-white rounded-lg max-w-lg w-full max-h-[80vh] overflow-y-auto p-6 shadow-2xl relative">
                <button onClick={() => setShowPrivacy(false)} className="absolute top-4 right-4 text-slate-400 hover:text-slate-600 font-bold">✕</button>
                <h2 className="text-xl font-bold mb-4">Privacy Policy</h2>
                <div className="prose prose-sm text-slate-600 space-y-4">
                  <p><strong>1. Data Collection:</strong> We collect personal information (name, DOB, contact details) to facilitate medical services.</p>
                  <p><strong>2. Usage:</strong> Your data is used for appointment scheduling, record keeping, and verification.</p>
                  <p><strong>3. Security:</strong> We employ industry-standard encryption to protect your data.</p>
                  <p><strong>4. Deletion:</strong> You may delete your account at any time from your profile settings.</p>
                </div>
                <div className="mt-6 flex justify-end">
                  <Button onClick={() => setShowPrivacy(false)}>Close</Button>
                </div>
              </div>
            </div>
          )}

          <p className="mt-6 text-center text-xs text-slate-500">
            Already have an account? <Link href="/auth/patient/login" className="text-blue-600 font-bold hover:underline">Sign in</Link>
          </p>
        </CardContent>
      </Card>
    </div>
  );
}