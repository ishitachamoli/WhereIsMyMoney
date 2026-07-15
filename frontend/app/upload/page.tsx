'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { api } from '@/lib/api';
import { UploadResponse } from '@/types';
import { FileUploadDropzone } from '@/components/FileUploadDropzone';
import { ErrorBoundary } from '@/components/ErrorBoundary';

const BANKS = [
  { value: 'auto', label: '🔍 Auto-detect' },
  { value: 'hdfc', label: '🏦 HDFC Bank' },
  { value: 'icici', label: '🏦 ICICI Bank' },
  { value: 'sbi', label: '🏦 SBI' },
  { value: 'axis', label: '🏦 Axis Bank' },
  { value: 'kotak', label: '🏦 Kotak Mahindra' },
  { value: 'idfc', label: '🏦 IDFC First' },
];

function UploadContent() {
  const router = useRouter();
  const [selectedBank, setSelectedBank] = useState('auto');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const handleFileAccepted = (file: File) => {
    setSelectedFile(file);
    setError(null);
  };

  const handleUpload = async () => {
    if (!selectedFile) return;

    try {
      setUploading(true);
      setError(null);
      setUploadProgress(0);

      const response: UploadResponse = await api.upload(selectedFile, selectedBank, (progress) => {
        setUploadProgress(progress);
      });

      // Redirect to dashboard immediately — classification runs in background
      const params = new URLSearchParams();
      if (response.classification_job_id) {
        params.set('classification_job_id', response.classification_job_id);
      }
      const query = params.toString();
      router.push(`/dashboard${query ? `?${query}` : ''}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed');
      setUploading(false);
    }
  };

  return (
    <div className="space-y-6 max-w-3xl mx-auto">
      <div>
        <h1 className="text-2xl font-bold text-white">Upload Statement</h1>
        <p className="text-sm text-zinc-400 mt-1">
          Upload your bank statement to analyze your spending
        </p>
      </div>

      <div className="bg-zinc-800 rounded-xl p-6 border border-zinc-700/50 space-y-5">
        <div>
          <label className="block text-sm font-medium text-zinc-300 mb-2">
            Select Bank
          </label>
          <select
            value={selectedBank}
            onChange={(e) => setSelectedBank(e.target.value)}
            className="w-full bg-zinc-900 border border-zinc-700 rounded-lg px-4 py-2.5 text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            {BANKS.map((bank) => (
              <option key={bank.value} value={bank.value}>
                {bank.label}
              </option>
            ))}
          </select>
        </div>

        <FileUploadDropzone
          onFileAccepted={handleFileAccepted}
          disabled={uploading}
        />

        {selectedFile && !uploading && (
          <div className="flex items-center justify-between p-4 bg-zinc-900 rounded-lg border border-zinc-700">
            <div className="flex items-center gap-3">
              <span className="text-2xl">📄</span>
              <div>
                <p className="text-sm font-medium text-white">{selectedFile.name}</p>
                <p className="text-xs text-zinc-500">
                  {(selectedFile.size / 1024).toFixed(1)} KB
                </p>
              </div>
            </div>
            <button
              onClick={handleUpload}
              className="px-5 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-medium transition-colors"
            >
              Upload & Analyze
            </button>
          </div>
        )}

        {uploading && (
          <div className="space-y-3">
            <div className="flex items-center justify-between text-sm">
              <span className="text-zinc-300">Uploading & processing transactions...</span>
              <span className="text-zinc-400">{uploadProgress}%</span>
            </div>
            <div className="h-2 bg-zinc-700 rounded-full overflow-hidden">
              <div
                className="h-full bg-blue-500 rounded-full transition-all duration-300"
                style={{ width: `${uploadProgress}%` }}
              />
            </div>
            <p className="text-xs text-zinc-500">
              Parsing your statement and applying rule-based classification...
            </p>
          </div>
        )}

        {error && (
          <div className="p-4 bg-red-900/30 border border-red-800 rounded-lg">
            <p className="text-sm text-red-300">{error}</p>
          </div>
        )}
      </div>

      <div className="bg-zinc-800/50 rounded-xl p-5 border border-zinc-700/30">
        <h3 className="text-sm font-medium text-zinc-300 mb-3">How it works</h3>
        <div className="space-y-2">
          <div className="flex items-start gap-3">
            <span className="text-zinc-500 text-xs font-mono mt-0.5">1</span>
            <p className="text-xs text-zinc-400">Upload your bank statement (CSV, Excel, or PDF)</p>
          </div>
          <div className="flex items-start gap-3">
            <span className="text-zinc-500 text-xs font-mono mt-0.5">2</span>
            <p className="text-xs text-zinc-400">Instant rule-based classification categorizes most transactions</p>
          </div>
          <div className="flex items-start gap-3">
            <span className="text-zinc-500 text-xs font-mono mt-0.5">3</span>
            <p className="text-xs text-zinc-400">AI classifies remaining transactions in the background while you explore your dashboard</p>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function UploadPage() {
  return (
    <ErrorBoundary>
      <UploadContent />
    </ErrorBoundary>
  );
}
