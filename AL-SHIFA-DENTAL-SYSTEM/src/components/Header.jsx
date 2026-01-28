"use client";

import React, { useState, useEffect } from 'react';
import { Menu, Bell, CheckCircle } from 'lucide-react';
import { Button } from "@/components/ui/button";
import { useRouter, usePathname } from 'next/navigation';
import { AuthAPI } from "@/lib/api"; 

export default function Header({ onMenuClick, title }) {
  const router = useRouter();
  const pathname = usePathname();
  const [user, setUser] = useState({
    name: "Loading...",
    roleLabel: "User",
    rawRole: "",
    initials: ".."
  });

  useEffect(() => {
    const fetchUser = async () => {
      try {
        const res = await AuthAPI.getMe();
        const u = res.data;
        
        const initials = u.full_name
          ? u.full_name.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase()
          : "U";

        let label = "User";
        if (u.role === 'doctor') label = "Verified Practitioner";
        else if (u.role === 'patient') label = "Patient Account";
        else if (u.role === 'organization') label = "Organization Admin";
        else if (u.role === 'admin') label = "System Administrator";

        setUser({
          name: u.full_name || "Unknown User",
          roleLabel: label,
          rawRole: u.role,
          initials: initials
        });
      } catch (error) {
        console.error("Header fetch error", error);
        setUser(prev => ({ ...prev, name: "Guest", roleLabel: "Visitor" }));
      }
    };
    fetchUser();
  }, []);

  const handleProfileClick = () => {
    console.log("Profile Button Clicked. Navigating for role:", user.rawRole);

    if (user.rawRole === 'doctor') {
      router.push('/doctor/profile');
    } else if (user.rawRole === 'patient') {
      router.push('/patient/profile');
    } else if (user.rawRole === 'organization') {
      router.push('/organization/profile');
    } else if (user.rawRole === 'admin') {
      router.push('/admin/dashboard'); 
    } else {
      if (pathname.includes('/doctor')) router.push('/doctor/profile');
      else router.push('/auth/login');
    }
  };

  return (
    <header className="sticky top-0 z-30 flex items-center justify-between px-6 py-4 bg-white/80 backdrop-blur-md border-b border-slate-100 transition-all duration-300">
      
      {/* LEFT: Menu & Title */}
      <div className="flex items-center gap-4">
        <Button 
          variant="ghost" 
          size="icon" 
          onClick={onMenuClick}
          className="rounded-full h-12 w-12 bg-slate-50 hover:bg-slate-100 border border-slate-200 shadow-sm transition-transform active:scale-95 flex items-center justify-center group"
        >
          <Menu className="h-6 w-6 text-slate-700 group-hover:text-teal-700 transition-colors" />
        </Button>
        
        <h1 className="text-xl font-bold text-slate-800 tracking-tight hidden md:block">
          {title || "Al-Shifa Dashboard"}
        </h1>
      </div>

      {/* RIGHT: Profile Section */}
      <div className="flex items-center gap-4">
        
        <Button variant="ghost" size="icon" className="rounded-full text-slate-500 hover:text-teal-600 relative">
          <Bell className="h-5 w-5" />
          <span className="absolute top-2 right-2 h-2 w-2 bg-red-500 rounded-full border border-white"></span>
        </Button>
        
        {/* CLICKABLE PROFILE BUTTON */}
        <Button 
          variant="ghost"
          onClick={handleProfileClick}
          className="flex items-center gap-3 h-auto p-1 pr-4 rounded-full border border-transparent hover:border-slate-200 hover:bg-slate-50 transition-all cursor-pointer group"
          title="Go to Profile"
        >
          {/* Initials Circle */}
          <div className="h-10 w-10 rounded-full bg-teal-600 text-white flex items-center justify-center font-bold text-sm shadow-md ring-2 ring-teal-50 group-hover:ring-teal-200 transition-all">
            {user.initials}
          </div>

          {/* Name & Role Text */}
          <div className="hidden md:flex flex-col items-start text-left">
            <span className="text-sm font-bold text-slate-700 leading-none group-hover:text-teal-700 transition-colors">
              {user.name}
            </span>
            <span className="text-[10px] font-medium text-slate-500 uppercase tracking-wide flex items-center mt-1">
              {user.roleLabel === "Verified Practitioner" && <CheckCircle className="w-3 h-3 mr-1 text-teal-500" />}
              {user.roleLabel}
            </span>
          </div>
        </Button>

      </div>
    </header>
  );
}