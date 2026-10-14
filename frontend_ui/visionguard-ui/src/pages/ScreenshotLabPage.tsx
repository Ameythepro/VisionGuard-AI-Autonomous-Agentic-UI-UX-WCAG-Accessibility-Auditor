import React, { useRef, useEffect } from "react";
import { useMutation } from "@tanstack/react-query";
import { Upload, Image as ImageIcon, Send, Code, Sparkles, MessageSquare, AlertTriangle, CheckCircle, RefreshCw, Copy, Check, Download, Zap } from "lucide-react";
import { toast } from "sonner";
import { api, API_BASE, type ScreenshotFixResponse } from "@/lib/api";
import { useWorkspaceStore } from "@/store/workspaceStore";

export default function ScreenshotLabPage() {
  const { 
    uploadedImage, setUploadedImage,
    analysisResult, setAnalysisResult,
    chatHistory, setChatHistory, addChatMessage,
    generatedCode, setGeneratedCode
  } = useWorkspaceStore();

  const [file, setFile] = React.useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = React.useState<string | null>(uploadedImage);
  const [prompt, setPrompt] = React.useState("");
  const [fixResult, setFixResult] = React.useState<ScreenshotFixResponse | null>(
    generatedCode ? { html: generatedCode } : null
  );
  const [chatMessage, setChatMessage] = React.useState("");
  const [copied, setCopied] = React.useState(false);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const chatEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatHistory]);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const selectedFile = e.target.files[0];
      setFile(selectedFile);
      const url = URL.createObjectURL(selectedFile);
      setPreviewUrl(url);
      setUploadedImage(url);
      
      setAnalysisResult(null);
      setFixResult(null);
      setGeneratedCode("");
      setChatHistory([]);
    }
  };

  const handleLoadSample = () => {
    const canvas = document.createElement("canvas");
    canvas.width = 600;
    canvas.height = 360;
    const ctx = canvas.getContext("2d");
    if (ctx) {
      ctx.fillStyle = "#f8fafc";
      ctx.fillRect(0, 0, 600, 360);
      
      ctx.fillStyle = "#ffffff";
      ctx.strokeStyle = "#e2e8f0";
      ctx.lineWidth = 1;
      ctx.roundRect ? ctx.roundRect(40, 40, 520, 280, 16) : ctx.fillRect(40, 40, 520, 280);
      ctx.fill();
      ctx.stroke();

      ctx.fillStyle = "#94a3b8"; // Low contrast gray on white
      ctx.font = "bold 22px sans-serif";
      ctx.fillText("User Profile Settings", 70, 90);

      ctx.fillStyle = "#cbd5e1"; // Very low contrast
      ctx.font = "14px sans-serif";
      ctx.fillText("Update your contact information and preferences.", 70, 125);

      ctx.fillStyle = "#f8fafc";
      ctx.strokeStyle = "#e2e8f0";
      ctx.fillRect(70, 150, 460, 44);
      ctx.strokeRect(70, 150, 460, 44);

      ctx.fillStyle = "#94a3b8";
      ctx.font = "14px sans-serif";
      ctx.fillText("Enter recovery email...", 85, 178);

      ctx.fillStyle = "#38bdf8"; // Poor contrast cyan
      ctx.fillRect(70, 220, 160, 44);
      ctx.fillStyle = "#ffffff";
      ctx.font = "bold 14px sans-serif";
      ctx.fillText("Save Changes", 95, 248);

      canvas.toBlob((blob) => {
        if (blob) {
          const sampleFile = new File([blob], "sample_accessibility_mockup.png", { type: "image/png" });
          setFile(sampleFile);
          const url = URL.createObjectURL(sampleFile);
          setPreviewUrl(url);
          setUploadedImage(url);
          setAnalysisResult(null);
          setFixResult(null);
          setGeneratedCode("");
          toast.success("Loaded sample UI mockup with intentional contrast flaws");
        }
      });
    }
  };

  const analyzeMutation = useMutation({
    mutationFn: () => {
      if (!file) throw new Error("No file selected");
      return api.analyzeScreenshot(file, prompt);
    },
    onSuccess: (data) => {
      setAnalysisResult(data);
      toast.success("AI Vision analysis complete");
    },
    onError: (err: Error) => {
      toast.error("Analysis failed", { description: err.message });
    }
  });

  const fixMutation = useMutation({
    mutationFn: () => {
      if (!analysisResult) throw new Error("No analysis available");
      return api.generateFix(analysisResult.analysis_id, prompt);
    },
    onSuccess: (data) => {
      setFixResult(data);
      if (data.html) setGeneratedCode(data.html);
      toast.success("Accessible UI code synthesized successfully");
    },
    onError: (err: Error) => {
      toast.error("Code generation failed", { description: err.message });
    }
  });

  const refineMutation = useMutation({
    mutationFn: (refinePrompt: string) => {
      if (!analysisResult) throw new Error("No analysis available");
      return api.refineCode(analysisResult.analysis_id, refinePrompt);
    },
    onSuccess: (data) => {
      setFixResult(data);
      if (data.html) setGeneratedCode(data.html);
      toast.success("Code refined with your instructions");
    },
    onError: (err: Error) => {
      toast.error("Refinement failed", { description: err.message });
    }
  });

  const chatMutation = useMutation({
    mutationFn: (msg: string) => {
      return api.chatScreenshot(analysisResult?.analysis_id ?? "general", msg);
    },
    onSuccess: (data) => {
      addChatMessage({ role: "assistant", content: data.response });
    },
    onError: (err: Error) => {
      toast.error("Chat failed", { description: err.message });
    }
  });

  const handleAnalyze = (e: React.FormEvent) => {
    e.preventDefault();
    if (!file && !uploadedImage) return;
    analyzeMutation.mutate();
  };

  const handleChatSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!chatMessage.trim()) return;
    const userMsg = chatMessage.trim();
    addChatMessage({ role: "user", content: userMsg });
    setChatMessage("");
    chatMutation.mutate(userMsg);
  };

  const handleRefineSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!prompt.trim()) return;
    refineMutation.mutate(prompt);
  };

  const handleCopyCode = () => {
    if (fixResult?.html) {
      navigator.clipboard.writeText(fixResult.html);
      setCopied(true);
      toast.success("HTML copied to clipboard");
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleDownloadCode = () => {
    if (fixResult?.html) {
      const blob = new Blob([fixResult.html], { type: "text/html" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `accessible_ui_${analysisResult?.analysis_id ?? "fixed"}.html`;
      a.click();
      URL.revokeObjectURL(url);
    }
  };

  return (
    <div className="space-y-8 pb-12">
      {/* ── Page Header ── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-6 sm:p-8 rounded-2xl bg-white border border-slate-200 shadow-sm">
        <div className="space-y-1">
          <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-purple-50 text-purple-700 border border-purple-200 text-xs font-bold uppercase tracking-wider">
            <Sparkles size={12} className="text-purple-600" />
            <span>Shift-Left Design Auditor</span>
          </div>
          <h2 className="text-2xl font-bold text-slate-900 tracking-tight">
            AI Vision Screenshot Lab
          </h2>
          <p className="text-xs sm:text-sm text-slate-600">
            Upload Figma mockups, raw wireframes, or app screenshots. Gemini 3.5 Flash inspects visual rasters and synthesizes compliant code.
          </p>
        </div>

        <button
          onClick={handleLoadSample}
          className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-slate-100 hover:bg-slate-200 border border-slate-300 text-xs font-semibold text-slate-800 transition-colors shadow-xs shrink-0"
        >
          <Zap size={14} className="text-amber-600" />
          <span>Load Test Sample UI</span>
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        
        {/* ── Left Column: Upload & Multimodal Analysis ── */}
        <div className="space-y-6">
          <div className="bg-white p-6 sm:p-8 rounded-2xl border border-slate-200 shadow-sm space-y-5">
            <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
              <Upload size={16} className="text-blue-600" />
              <span>Upload UI Visual Raster</span>
            </h3>
            
            <form onSubmit={handleAnalyze} className="space-y-4">
              <div 
                className="group border-2 border-dashed border-slate-300 hover:border-blue-500 rounded-xl p-6 text-center transition-colors cursor-pointer bg-slate-50/60 hover:bg-slate-50"
                onClick={() => fileInputRef.current?.click()}
              >
                {previewUrl ? (
                  <div className="relative aspect-video w-full rounded-lg overflow-hidden border border-slate-200 shadow-inner bg-slate-100">
                    <img src={previewUrl} alt="Preview" className="object-contain w-full h-full" />
                    <div className="absolute inset-0 bg-slate-900/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center text-xs font-semibold text-white">
                      Click to change image
                    </div>
                  </div>
                ) : (
                  <div className="py-8 flex flex-col items-center">
                    <div className="w-12 h-12 rounded-xl bg-blue-50 border border-blue-200 flex items-center justify-center text-blue-600 mb-3">
                      <ImageIcon size={24} />
                    </div>
                    <p className="text-sm font-bold text-slate-800">Drop your UI mockup or screenshot here</p>
                    <p className="text-xs text-slate-500 mt-1">PNG, JPG, WebP up to 15MB</p>
                  </div>
                )}
                <input 
                  type="file" 
                  ref={fileInputRef} 
                  className="hidden" 
                  accept="image/*" 
                  onChange={handleFileChange} 
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                  AI Context / Styling Directives (Optional)
                </label>
                <textarea
                  placeholder="E.g., Preserve our brand palette, enforce 4.5:1 text contrast, or enlarge touch targets to 44px..."
                  value={prompt}
                  onChange={(e) => setPrompt(e.target.value)}
                  disabled={analyzeMutation.isPending}
                  className="w-full min-h-[75px] p-3 text-xs rounded-xl bg-slate-50 border border-slate-300 text-slate-900 placeholder-slate-400 focus:outline-none focus:border-blue-600 focus:bg-white transition-all font-sans"
                />
              </div>

              <button 
                type="submit" 
                disabled={(!file && !previewUrl) || analyzeMutation.isPending}
                className="w-full inline-flex items-center justify-center gap-2 py-3 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold shadow-sm disabled:opacity-50 disabled:cursor-not-allowed transition-all"
              >
                {analyzeMutation.isPending ? (
                  <>
                    <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    <span>Analyzing Visual Rasters...</span>
                  </>
                ) : (
                  <>
                    <Sparkles size={16} />
                    <span>Analyze Screenshot with Gemini 3.5</span>
                  </>
                )}
              </button>
            </form>
          </div>

          {/* Analysis Results Card */}
          {analysisResult && (
            <div className="bg-white p-6 sm:p-8 rounded-2xl border border-slate-200 shadow-sm animate-fade-in space-y-5">
              <div className="flex justify-between items-center border-b border-slate-200 pb-4">
                <div>
                  <h3 className="text-base font-bold text-slate-900">
                    WCAG Visual Diagnosis
                  </h3>
                  <p className="text-2xs text-slate-500">Analysis ID: {analysisResult.analysis_id}</p>
                </div>
                <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-slate-100 border border-slate-200">
                  <span className="text-2xs uppercase text-slate-500 font-bold">Score:</span>
                  <span className="text-base font-extrabold text-slate-900 font-mono">
                    {analysisResult.overall_score}/100
                  </span>
                </div>
              </div>
              
              {analysisResult.error && (
                <div className="p-3.5 rounded-xl bg-amber-50 border border-amber-200 text-amber-900 text-xs flex items-start gap-2.5">
                  <AlertTriangle size={16} className="text-amber-600 shrink-0 mt-0.5" />
                  <div>
                    <span className="font-bold">API Warning:</span> {analysisResult.error}
                  </div>
                </div>
              )}

              <p className="text-sm text-slate-700 leading-relaxed">{analysisResult.summary}</p>

              {analysisResult.violations && analysisResult.violations.length > 0 && (
                <div className="space-y-3">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-rose-600 flex items-center gap-1.5">
                    <AlertTriangle size={15} /> 
                    <span>Detected Violations ({analysisResult.violations.length})</span>
                  </h4>
                  <ul className="space-y-2.5">
                    {analysisResult.violations.map((v: any, i: number) => (
                      <li key={i} className="text-xs p-3.5 rounded-xl bg-slate-50 border border-slate-200 space-y-1.5">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${v.severity === 'critical' ? 'bg-rose-100 text-rose-800 border border-rose-200' : 'bg-amber-100 text-amber-800 border border-amber-200'}`}>
                            {v.severity}
                          </span>
                          <span className="font-semibold text-slate-900">{v.type}</span>
                          <span className="text-slate-500 font-mono">SC {v.wcag_criterion}</span>
                        </div>
                        <p className="text-slate-700">{v.description}</p>
                        <p className="text-blue-700 font-semibold">💡 Suggestion: {v.suggestion}</p>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {analysisResult.positive_findings && analysisResult.positive_findings.length > 0 && (
                <div className="space-y-2 pt-3 border-t border-slate-200">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-emerald-700 flex items-center gap-1.5">
                    <CheckCircle size={15} /> 
                    <span>Compliant Findings</span>
                  </h4>
                  <ul className="list-disc list-inside text-xs text-slate-700 space-y-1">
                    {analysisResult.positive_findings.map((p: string, i: number) => <li key={i}>{p}</li>)}
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>


        {/* ── Right Column: Accessible Code Synthesis & Consultant Chat ── */}
        <div className="space-y-6">
          
          {/* Accessible Code Synthesis Card */}
          <div className="bg-white p-6 sm:p-8 rounded-2xl border border-slate-200 shadow-sm space-y-5">
            <div className="flex justify-between items-center">
              <div>
                <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                  <Code size={16} className="text-blue-600" /> 
                  <span>Autonomous UI Reconstruction</span>
                </h3>
                <p className="text-xs text-slate-500">Synthesizes compliant HTML/CSS from visual rasters</p>
              </div>

              <button 
                onClick={() => fixMutation.mutate()} 
                disabled={!analysisResult || fixMutation.isPending}
                className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed text-white text-xs font-semibold shadow-sm transition-all"
              >
                {fixMutation.isPending ? (
                  <>
                    <span className="w-3 h-3 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    <span>Synthesizing...</span>
                  </>
                ) : (
                  <>
                    <Sparkles size={14} />
                    <span>Generate Fix</span>
                  </>
                )}
              </button>
            </div>

            {fixResult ? (
              <div className="space-y-4 animate-fade-in">
                {fixResult.warning && (
                  <div className="p-3.5 rounded-xl bg-amber-50 border border-amber-200 text-amber-900 text-xs flex items-start gap-2.5">
                    <AlertTriangle size={16} className="text-amber-600 shrink-0 mt-0.5" />
                    <div>
                      <span className="font-bold">API Warning:</span> {fixResult.warning}
                    </div>
                  </div>
                )}
                {fixResult.fixed_screenshot_path && (
                  <div className="space-y-2">
                    <p className="text-xs font-semibold text-slate-700">Patched Visual Preview (Rendered)</p>
                    <div className="bg-slate-100 border border-slate-200 rounded-xl h-56 flex items-center justify-center overflow-hidden p-2">
                      <img 
                        src={`${API_BASE}/${fixResult.fixed_screenshot_path}`} 
                        alt="Fixed UI Preview" 
                        className="max-h-full max-w-full object-contain rounded" 
                      />
                    </div>
                  </div>
                )}

                {fixResult.html ? (
                  <div className="relative rounded-xl overflow-hidden border border-slate-300 bg-slate-900">
                    <div className="px-4 py-2 bg-slate-800 border-b border-slate-700 flex items-center justify-between text-xs text-slate-300 font-mono">
                      <span>accessible_ui_reconstructed.html</span>
                      <div className="flex items-center gap-2">
                        <button 
                          onClick={handleCopyCode}
                          className="hover:text-white transition-colors flex items-center gap-1 text-slate-300"
                        >
                          {copied ? <Check size={12} className="text-emerald-400" /> : <Copy size={12} />}
                          <span>{copied ? "Copied" : "Copy"}</span>
                        </button>
                        <button 
                          onClick={handleDownloadCode}
                          className="hover:text-white transition-colors flex items-center gap-1 ml-2 text-slate-300"
                        >
                          <Download size={12} />
                          <span>Download</span>
                        </button>
                      </div>
                    </div>
                    <pre className="p-4 text-xs font-mono overflow-auto max-h-[260px] text-slate-200 leading-relaxed">
                      <code>{fixResult.html}</code>
                    </pre>
                  </div>
                ) : (
                  <p className="text-xs text-rose-600">{fixResult.error || "Failed to generate code."}</p>
                )}

                {/* Refinement Form */}
                <form onSubmit={handleRefineSubmit} className="flex gap-2 pt-2 border-t border-slate-200">
                  <input 
                    placeholder="Refine styling: e.g. Make buttons rounded, use navy blue..."
                    value={prompt}
                    onChange={e => setPrompt(e.target.value)}
                    className="flex-1 px-3 py-2 text-xs rounded-xl bg-slate-50 border border-slate-300 text-slate-900 placeholder-slate-400 focus:outline-none focus:border-blue-600 focus:bg-white"
                  />
                  <button 
                    type="submit" 
                    disabled={!prompt.trim() || refineMutation.isPending}
                    className="px-4 py-2 rounded-xl bg-slate-100 hover:bg-slate-200 border border-slate-300 text-slate-700 text-xs font-semibold disabled:opacity-50 transition-colors shrink-0"
                  >
                    {refineMutation.isPending ? "Refining..." : "Refine"}
                  </button>
                </form>
              </div>
            ) : (
              <div className="text-center py-12 border border-dashed border-slate-300 rounded-xl bg-slate-50">
                <Code size={24} className="text-slate-400 mx-auto mb-2" />
                <p className="text-xs text-slate-500">Click "Generate Fix" after analysis to synthesize clean accessible code.</p>
              </div>
            )}
          </div>

          {/* AI Accessibility Consultant Chat */}
          <div className="bg-white border border-slate-200 rounded-2xl shadow-sm flex flex-col h-[400px] overflow-hidden">
            <div className="p-4 border-b border-slate-200 bg-slate-50 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <MessageSquare size={16} className="text-blue-600" />
                <h3 className="text-xs font-bold text-slate-800 uppercase tracking-wider">AI Accessibility Consultant</h3>
              </div>
              <span className="text-[10px] text-emerald-700 bg-emerald-50 border border-emerald-200 px-2 py-0.5 rounded-full font-mono font-semibold">Gemini 3.5 Active</span>
            </div>
            
            <div className="flex-1 p-4 overflow-y-auto space-y-3 bg-slate-50/50">
              {chatHistory.length === 0 ? (
                <div className="text-center py-12 text-slate-500 space-y-2">
                  <MessageSquare size={24} className="text-slate-400 mx-auto" />
                  <p className="text-xs">Ask questions about WCAG compliance, ARIA standards, or color math.</p>
                  <div className="flex flex-wrap justify-center gap-1.5 pt-2">
                    {["Why 4.5:1 ratio?", "Explain WCAG 1.4.3", "How to fix contrast?"].map(q => (
                      <button 
                        key={q} 
                        onClick={() => { setChatMessage(q); }} 
                        className="text-[11px] px-2.5 py-1 rounded-full bg-white hover:bg-slate-100 text-slate-700 border border-slate-200 transition-colors"
                      >
                        {q}
                      </button>
                    ))}
                  </div>
                </div>
              ) : (
                chatHistory.map((msg, i) => (
                  <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                    <div 
                      className={`max-w-[85%] rounded-2xl px-3.5 py-2.5 text-xs ${
                        msg.role === 'user' 
                          ? 'bg-blue-600 text-white rounded-br-none shadow-xs' 
                          : 'bg-white border border-slate-200 text-slate-800 rounded-bl-none shadow-xs'
                      }`}
                    >
                      <div className="whitespace-pre-wrap leading-relaxed">{msg.content}</div>
                    </div>
                  </div>
                ))
              )}
              {chatMutation.isPending && (
                <div className="flex justify-start">
                  <div className="rounded-2xl px-4 py-2.5 bg-white border border-slate-200 flex items-center gap-1.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-blue-600 animate-pulse" />
                    <span className="w-1.5 h-1.5 rounded-full bg-blue-600 animate-pulse delay-100" />
                    <span className="w-1.5 h-1.5 rounded-full bg-blue-600 animate-pulse delay-200" />
                  </div>
                </div>
              )}
              <div ref={chatEndRef} />
            </div>

            <div className="p-3 border-t border-slate-200 bg-white">
              <form onSubmit={handleChatSubmit} className="flex gap-2">
                <input 
                  placeholder="Ask a question about accessibility..."
                  value={chatMessage}
                  onChange={(e) => setChatMessage(e.target.value)}
                  className="flex-1 px-3 py-2 text-xs rounded-xl bg-slate-50 border border-slate-300 text-slate-900 placeholder-slate-400 focus:outline-none focus:border-blue-600 focus:bg-white"
                />
                <button 
                  type="submit" 
                  disabled={!chatMessage.trim() || chatMutation.isPending}
                  className="p-2.5 rounded-xl bg-blue-600 hover:bg-blue-700 text-white disabled:opacity-50 transition-colors shrink-0 shadow-xs"
                >
                  <Send size={14} />
                </button>
              </form>
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}
