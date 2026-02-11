'use client';

import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Textarea } from '@/components/ui/textarea';
import { Upload, FileText, CheckCircle, AlertCircle, Loader2, FileType } from 'lucide-react';
import { AgentAPI } from '@/lib/api';

export default function KnowledgeUpload() {
    const [file, setFile] = useState<File | null>(null);
    const [textInput, setTextInput] = useState("");
    const [uploading, setUploading] = useState(false);
    const [status, setStatus] = useState<{ type: 'success' | 'error'; message: string } | null>(null);
    const [activeTab, setActiveTab] = useState("file");

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files[0]) {
            setFile(e.target.files[0]);
            setStatus(null);
        }
    };

    const handleUpload = async () => {
        setUploading(true);
        setStatus(null);

        const formData = new FormData();

        try {
            if (activeTab === "file") {
                if (!file) return;
                formData.append('file', file);
            } else {
                if (!textInput.trim()) return;
                // Create a text file from the input
                const blob = new Blob([textInput], { type: "text/plain" });
                const timestamp = new Date().toISOString().replace(/[:.]/g, "-");
                const filename = `protocol-${timestamp}.txt`;
                formData.append('file', blob, filename);
            }

            const res = await AgentAPI.uploadKnowledge(formData);

            if (res.data.status === 'success') {
                setStatus({ type: 'success', message: res.data.message });
                setFile(null);
                setTextInput("");
            } else {
                setStatus({ type: 'error', message: res.data.message || 'Upload failed' });
            }
        } catch (err: any) {
            console.error(err);
            setStatus({ type: 'error', message: err.response?.data?.message || 'Connection error' });
        } finally {
            setUploading(false);
        }
    };

    return (
        <Card className="border-t-4 border-teal-500 shadow-sm">
            <CardHeader className="pb-3">
                <CardTitle className="flex items-center gap-2 text-lg">
                    <Upload className="h-5 w-5 text-teal-600" />
                    Teach the Agent
                </CardTitle>
                <CardDescription>
                    Add clinical knowledge to the AI brain.
                </CardDescription>
            </CardHeader>
            <CardContent>
                <Tabs defaultValue="file" value={activeTab} onValueChange={setActiveTab} className="w-full">
                    <TabsList className="grid w-full grid-cols-2 mb-4">
                        <TabsTrigger value="file">Upload File</TabsTrigger>
                        <TabsTrigger value="text">Paste Text</TabsTrigger>
                    </TabsList>

                    <TabsContent value="file" className="space-y-4">
                        <div className="flex items-center gap-3">
                            <input
                                type="file"
                                accept=".txt,.pdf"
                                onChange={handleFileChange}
                                className="block w-full text-sm text-slate-500
                                file:mr-4 file:py-2 file:px-4
                                file:rounded-full file:border-0
                                file:text-sm file:font-semibold
                                file:bg-teal-50 file:text-teal-700
                                hover:file:bg-teal-100 placeholder-gray-400"
                            />
                        </div>
                        {file && (
                            <div className="flex items-center gap-2 text-sm text-slate-700 bg-slate-50 p-2 rounded-md border">
                                <FileText className="h-4 w-4 text-blue-500" />
                                <span className="truncate flex-1">{file.name}</span>
                                <span className="text-xs text-slate-400">({(file.size / 1024).toFixed(1)} KB)</span>
                            </div>
                        )}
                    </TabsContent>

                    <TabsContent value="text" className="space-y-4">
                        <textarea
                            placeholder="Paste clinical protocol here..."
                            className="min-h-[150px] w-full p-3 text-sm border rounded-md border-slate-200 focus:outline-none focus:ring-2 focus:ring-teal-500"
                            value={textInput}
                            onChange={(e) => setTextInput(e.target.value)}
                        />
                        <p className="text-xs text-slate-400">Will be saved as a text file.</p>
                    </TabsContent>
                </Tabs>

                <div className="mt-4 space-y-4">
                    <Button
                        onClick={handleUpload}
                        disabled={(activeTab === 'file' && !file) || (activeTab === 'text' && !textInput.trim()) || uploading}
                        className="w-full bg-teal-600 hover:bg-teal-700"
                    >
                        {uploading ? (
                            <>
                                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                Processing...
                            </>
                        ) : (
                            'Upload & Train'
                        )}
                    </Button>

                    {status && (
                        <div className={`p-3 rounded-lg text-sm flex items-start gap-2 ${status.type === 'success' ? 'bg-green-50 text-green-700 border border-green-200' : 'bg-red-50 text-red-700 border border-red-200'
                            }`}>
                            {status.type === 'success' ? <CheckCircle className="h-5 w-5 shrink-0" /> : <AlertCircle className="h-5 w-5 shrink-0" />}
                            <p>{status.message}</p>
                        </div>
                    )}
                </div>
            </CardContent>
        </Card>
    );
}
