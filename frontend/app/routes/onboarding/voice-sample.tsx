

// app/routes/onboarding/voice-sample.tsx - Updated with state management
import React, { useState } from "react";
import { useNavigate } from "react-router";
import { Button } from "~/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "~/components/ui/card";
import { Alert, AlertDescription } from "~/components/ui/alert";
import { Progress } from "~/components/ui/progress";
import { motion } from "framer-motion";
import {
  Mic,
  Upload,
  ArrowRight,
  ArrowLeft,
  CheckCircle,
  AlertCircle,
  PlayCircle,
  Trash2
} from "lucide-react";
import { useApp } from "contexts/appContext";

export default function OnboardingVoiceSample() {
  const navigate = useNavigate();
  const { uploadVoiceSample, state } = useApp();
  
  const [file, setFile] = useState<File | null>(null);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadedUrl, setUploadedUrl] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [dragActive, setDragActive] = useState(false);

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    const files = e.dataTransfer.files;
    if (files && files[0]) {
      handleFileSelect(files[0]);
    }
  };

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      handleFileSelect(e.target.files[0]);
    }
  };

  const handleFileSelect = (selectedFile: File) => {
    // Validate file type
    const allowedTypes = ['audio/mpeg', 'audio/mp3', 'audio/wav', 'audio/m4a', 'audio/x-m4a'];
    if (!allowedTypes.includes(selectedFile.type)) {
      setError("Please upload an audio file (MP3, WAV, or M4A)");
      return;
    }

    // Validate file size (max 50MB)
    if (selectedFile.size > 50 * 1024 * 1024) {
      setError("File size must be less than 50MB");
      return;
    }

    setFile(selectedFile);
    setError("");
    uploadFile(selectedFile);
  };

  const uploadFile = async (fileToUpload: File) => {
    try {
      // Simulate upload progress
      setUploadProgress(0);
      const progressInterval = setInterval(() => {
        setUploadProgress(prev => {
          if (prev >= 90) {
            clearInterval(progressInterval);
            return prev;
          }
          return prev + 10;
        });
      }, 200);

      const fileUrl = await uploadVoiceSample(fileToUpload);
      clearInterval(progressInterval);
      setUploadProgress(100);
      setUploadedUrl(fileUrl);
    } catch (error: any) {
      setError(error.message || "Failed to upload voice sample. Please try again.");
      console.error("Upload error:", error);
    }
  };

  const removeFile = () => {
    setFile(null);
    setUploadedUrl(null);
    setUploadProgress(0);
    setError("");
  };

  const handleContinue = () => {
    navigate("/onboarding/languages");
  };

  const handleSkip = () => {
    navigate("/onboarding/languages");
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-purple-50 flex items-center justify-center p-4">
      <motion.div
        initial={{ scale: 0.9, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ duration: 0.6, ease: "easeOut" }}
        className="w-full max-w-2xl"
      >
        <Card className="backdrop-blur-md bg-white/80 shadow-2xl border-0 overflow-hidden">
          <CardHeader className="text-center pb-6">
            <div className="w-16 h-16 bg-gradient-to-r from-purple-500 to-pink-600 rounded-3xl flex items-center justify-center mx-auto mb-4">
              <Mic className="w-8 h-8 text-white" />
            </div>
            <CardTitle className="text-2xl md:text-3xl font-bold text-gray-900">
              Upload Your Voice Sample
            </CardTitle>
            <p className="text-gray-600 mt-2">
              Upload a 1-5 minute audio sample to enable voice cloning for authentic translations
            </p>
          </CardHeader>
          <CardContent className="space-y-6 px-8 pb-8">
            {!uploadedUrl ? (
              <div
                onDragEnter={handleDrag}
                onDragLeave={handleDrag}
                onDragOver={handleDrag}
                onDrop={handleDrop}
                className={`border-2 border-dashed rounded-xl p-8 text-center transition-colors ${
                  dragActive
                    ? "border-purple-400 bg-purple-50"
                    : "border-gray-300 hover:border-gray-400"
                }`}
              >
                <input
                  type="file"
                  id="voice-upload"
                  className="hidden"
                  accept="audio/*"
                  onChange={handleFileInput}
                  disabled={state.isLoading}
                />
                {!state.isLoading ? (
                  <>
                    <Mic className="w-16 h-16 text-gray-400 mx-auto mb-4" />
                    <h3 className="text-lg font-semibold text-gray-900 mb-2">
                      Drop your audio file here
                    </h3>
                    <p className="text-gray-600 mb-6">
                      or click to browse files
                    </p>
                    <Button
                      onClick={() => document.getElementById('voice-upload')?.click()}
                      className="bg-purple-600 hover:bg-purple-700"
                    >
                      <Upload className="w-4 h-4 mr-2" />
                      Choose Audio File
                    </Button>
                    <p className="text-sm text-gray-500 mt-4">
                      Supported formats: MP3, WAV, M4A (max 50MB)
                    </p>
                  </>
                ) : (
                  <div className="space-y-4">
                    <div className="w-16 h-16 bg-purple-100 rounded-full flex items-center justify-center mx-auto">
                      <Mic className="w-8 h-8 text-purple-600" />
                    </div>
                    <div>
                      <p className="font-medium text-gray-900 mb-2">Uploading {file?.name}</p>
                      <Progress value={uploadProgress} className="w-full" />
                      <p className="text-sm text-gray-500 mt-1">{uploadProgress}% complete</p>
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="p-6 bg-green-50 border border-green-200 rounded-xl"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <CheckCircle className="w-8 h-8 text-green-600" />
                    <div>
                      <h3 className="font-semibold text-green-900">Voice sample uploaded!</h3>
                      <p className="text-green-700 text-sm">{file?.name}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Button variant="outline" size="sm">
                      <PlayCircle className="w-4 h-4 mr-2" />
                      Preview
                    </Button>
                    <Button variant="outline" size="sm" onClick={removeFile}>
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  </div>
                </div>
              </motion.div>
            )}

            {error && (
              <Alert variant="destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}

            {/* Tips */}
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <h4 className="font-medium text-blue-900 mb-2">Tips for best results:</h4>
              <ul className="text-sm text-blue-800 space-y-1">
                <li>• Use clear, high-quality audio without background noise</li>
                <li>• Include varied speech patterns and emotions</li>
                <li>• 3-5 minutes of content provides optimal voice cloning</li>
                <li>• Speak at your normal pace and volume</li>
              </ul>
            </div>

            {/* Navigation */}
            <div className="flex justify-between pt-4">
              <Button
                variant="outline"
                onClick={() => navigate("/onboarding/rss-feed")}
                className="flex items-center gap-2"
                disabled={state.isLoading}
              >
                <ArrowLeft className="w-4 h-4" />
                Back
              </Button>
              <div className="flex gap-3">
                <Button variant="outline" onClick={handleSkip} disabled={state.isLoading}>
                  Skip for now
                </Button>
                <Button
                  onClick={handleContinue}
                  disabled={!uploadedUrl && !state.isLoading}
                  className="bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 flex items-center gap-2"
                >
                  Continue
                  <ArrowRight className="w-4 h-4" />
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      </motion.div>
    </div>
  );
}