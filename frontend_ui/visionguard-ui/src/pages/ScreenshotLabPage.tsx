import React, { useRef, useEffect } from "react";
import { useMutation } from "@tanstack/react-query";
import { Upload, Image as ImageIcon, Send, Code, Sparkles, MessageSquare, AlertTriangle, CheckCircle, RefreshCw } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/Button";
import { Input, Textarea } from "@/components/ui/Input";
import { Badge } from "@/components/ui/Badge";
import { api, type ScreenshotAnalysisResponse, type ScreenshotFixResponse, type ScreenshotChatResponse } from "@/lib/api";
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

  const fileInputRef = useRef<HTMLInputElement>(null);
  const chatEndRef = useRef<HTMLDivElement>(null);

  // Scroll to bottom of chat when new message added
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
      
      // Reset state
      setAnalysisResult(null);
      setFixResult(null);
      setGeneratedCode("");
      setChatHistory([]);
    }
  };

  const analyzeMutation = useMutation({
    mutationFn: () => {
      if (!file) throw new Error("No file selected");
      return api.analyzeScreenshot(file, prompt);
    },
    onSuccess: (data) => {
      setAnalysisResult(data);
      toast.success("Analysis complete");
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
      toast.success("Fixed code generated");
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
      toast.success("Code refined");
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
    if (!file && !uploadedImage) return; // Allow running if uploadedImage is in store
    analyzeMutation.mutate();
  };

  const handleChatSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!chatMessage.trim()) return;
    
    // Add user message immediately
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

  return (
    <div className="max-w-6xl mx-auto space-y-8 pb-12">
      <div>
        <h2 className="text-xl font-semibold text-text-primary">Screenshot Lab</h2>
        <p className="text-sm text-text-secondary mt-1">
          Upload a screenshot to analyze for accessibility violations, generate fixed code, and chat with VisionGuard AI.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        
        {/* Left Column: Upload & Analysis */}
        <div className="space-y-6">
          <div className="bg-bg-surface border border-border p-5 rounded-lg shadow-sm">
            <h3 className="text-sm font-medium text-text-primary mb-4 flex items-center gap-2">
              <Upload size={16} className="text-accent" /> Upload Screenshot
            </h3>
            
            <form onSubmit={handleAnalyze} className="space-y-4">
              <div 
                className="border-2 border-dashed border-border rounded-lg p-6 text-center hover:border-accent transition-colors cursor-pointer"
                onClick={() => fileInputRef.current?.click()}
              >
                {previewUrl ? (
                  <div className="relative aspect-video w-full rounded overflow-hidden border border-border">
                    <img src={previewUrl} alt="Preview" className="object-contain w-full h-full bg-bg-subtle" />
                  </div>
                ) : (
                  <div className="py-8 flex flex-col items-center">
                    <ImageIcon size={32} className="text-text-tertiary mb-2" />
                    <p className="text-sm text-text-secondary">Click to upload or drag and drop</p>
                    <p className="text-xs text-text-tertiary mt-1">PNG, JPG up to 10MB</p>
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

              <Textarea 
                label="Instructions/Context (Optional)"
                placeholder="E.g., Focus on fixing contrast issues, or use specific brand colors..."
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                disabled={analyzeMutation.isPending}
                className="min-h-[80px]"
              />

              <Button 
                type="submit" 
                className="w-full" 
                loading={analyzeMutation.isPending} 
                disabled={!file && !previewUrl}
              >
                <Sparkles size={16} /> Analyze Screenshot
              </Button>
            </form>
          </div>

          {/* Analysis Results */}
          {analysisResult && (
            <div className="bg-bg-surface border border-border p-5 rounded-lg shadow-sm animate-fade-in space-y-5">
              <div className="flex justify-between items-center border-b border-border pb-3">
                <h3 className="text-sm font-medium text-text-primary flex items-center gap-2">
                  Analysis Results
                </h3>
                <div className="flex items-center gap-3">
                  <span className="text-sm font-mono bg-bg-subtle px-2 py-1 rounded border border-border">
                    Score: {analysisResult.overall_score}/100
                  </span>
                </div>
              </div>
              
              <p className="text-sm text-text-secondary">{analysisResult.summary}</p>

              {analysisResult.violations && analysisResult.violations.length > 0 && (
                <div className="space-y-3">
                  <h4 className="text-xs font-semibold text-text-primary uppercase tracking-wider text-danger flex items-center gap-1">
                    <AlertTriangle size={14} /> Violations ({analysisResult.violations.length})
                  </h4>
                  <ul className="space-y-3">
                    {analysisResult.violations.map((v: any, i: number) => (
                      <li key={i} className="text-sm bg-bg-subtle p-3 rounded border border-border">
                        <div className="flex items-center gap-2 mb-1">
                          <Badge variant={v.severity === 'critical' ? 'danger' : 'warning'}>{v.severity}</Badge>
                          <span className="font-medium text-text-primary">{v.type}</span>
                          <span className="text-xs text-text-tertiary">SC {v.wcag_criterion}</span>
                        </div>
                        <p className="text-text-secondary mt-1">{v.description}</p>
                        <p className="text-xs mt-2 text-accent">Fix: {v.suggestion}</p>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {analysisResult.positive_findings && analysisResult.positive_findings.length > 0 && (
                <div className="space-y-2 mt-4 pt-4 border-t border-border">
                  <h4 className="text-xs font-semibold text-text-primary uppercase tracking-wider text-success flex items-center gap-1">
                    <CheckCircle size={14} /> Positive Findings
                  </h4>
                  <ul className="list-disc list-inside text-sm text-text-secondary space-y-1">
                    {analysisResult.positive_findings.map((p: string, i: number) => <li key={i}>{p}</li>)}
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>


        {/* Right Column: Code Gen & Chat */}
        <div className="space-y-6">
          
          {/* Fix Generation */}
          <div className="bg-bg-surface border border-border p-5 rounded-lg shadow-sm">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-sm font-medium text-text-primary flex items-center gap-2">
                <Code size={16} className="text-accent" /> Accessible UI Generation
              </h3>
              <Button 
                size="sm" 
                onClick={() => fixMutation.mutate()} 
                loading={fixMutation.isPending}
                disabled={!analysisResult || refineMutation.isPending}
              >
                Generate Fix
              </Button>
            </div>

            {fixResult ? (
              <div className="space-y-4 animate-fade-in">
                {fixResult.fixed_screenshot_path && (
                  <div className="space-y-1.5">
                    <p className="text-xs font-medium text-text-secondary">Fixed UI Preview (Rendered)</p>
                    <div className="bg-bg-subtle border border-border rounded-lg h-48 flex items-center justify-center overflow-hidden">
                      <img src={`http://localhost:8001/${fixResult.fixed_screenshot_path}`} alt="Fixed UI Preview" className="max-h-full max-w-full object-contain" />
                    </div>
                  </div>
                )}
                {fixResult.html ? (
                  <div className="relative rounded overflow-hidden border border-border mt-4">
                    <div className="bg-bg-subtle px-3 py-1.5 text-xs text-text-tertiary font-mono border-b border-border flex justify-between">
                      <span>fixed_accessible_ui.html</span>
                      <button 
                        onClick={() => {
                          navigator.clipboard.writeText(fixResult.html!);
                          toast.success("Copied to clipboard");
                        }}
                        className="hover:text-text-primary transition-colors"
                      >
                        Copy
                      </button>
                    </div>
                    <pre className="p-4 text-xs font-mono overflow-auto max-h-[300px] bg-bg-surface text-text-secondary">
                      <code>{fixResult.html}</code>
                    </pre>
                  </div>
                ) : (
                  <p className="text-sm text-danger">{fixResult.error || "Failed to generate code."}</p>
                )}

                {/* Refinement Form */}
                <form onSubmit={handleRefineSubmit} className="flex gap-2 pt-2 border-t border-border mt-4">
                  <div className="flex-1">
                    <Input 
                      placeholder="E.g., Make the background darker, or change the font..."
                      value={prompt}
                      onChange={e => setPrompt(e.target.value)}
                    />
                  </div>
                  <Button type="submit" loading={refineMutation.isPending} disabled={!prompt.trim() || fixMutation.isPending}>
                    <RefreshCw size={15} /> Refine
                  </Button>
                </form>
              </div>
            ) : (
              <div className="text-center py-10 border border-dashed border-border rounded bg-bg-subtle">
                <p className="text-sm text-text-secondary">Run analysis and click "Generate Fix" to get accessible HTML code.</p>
              </div>
            )}
          </div>

          {/* AI Chat Suggestions */}
          <div className="bg-bg-surface border border-border rounded-lg shadow-sm flex flex-col h-[400px]">
            <div className="p-3 border-b border-border bg-bg-subtle flex items-center gap-2">
              <MessageSquare size={16} className="text-accent" />
              <h3 className="text-sm font-medium text-text-primary">AI Accessibility Consultant</h3>
            </div>
            
            <div className="flex-1 p-4 overflow-y-auto space-y-4">
              {chatHistory.length === 0 ? (
                <div className="text-center mt-10">
                  <MessageSquare size={24} className="text-text-tertiary mx-auto mb-2" />
                  <p className="text-sm text-text-secondary">Ask for suggestions or explanations about WCAG guidelines.</p>
                </div>
              ) : (
                chatHistory.map((msg, i) => (
                  <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                    <div 
                      className={`max-w-[85%] rounded-lg p-3 text-sm ${
                        msg.role === 'user' 
                          ? 'bg-accent text-white rounded-tr-none' 
                          : 'bg-bg-subtle border border-border text-text-primary rounded-tl-none'
                      }`}
                    >
                      {/* Simple markdown rendering placeholder - a real app would use react-markdown */}
                      <div className="whitespace-pre-wrap">{msg.content}</div>
                    </div>
                  </div>
                ))
              )}
              {chatMutation.isPending && (
                <div className="flex justify-start">
                  <div className="max-w-[85%] rounded-lg p-3 text-sm bg-bg-subtle border border-border rounded-tl-none flex items-center gap-2">
                    <div className="w-2 h-2 rounded-full bg-text-tertiary animate-pulse"></div>
                    <div className="w-2 h-2 rounded-full bg-text-tertiary animate-pulse delay-75"></div>
                    <div className="w-2 h-2 rounded-full bg-text-tertiary animate-pulse delay-150"></div>
                  </div>
                </div>
              )}
              <div ref={chatEndRef} />
            </div>

            <div className="p-3 border-t border-border bg-bg-subtle">
              <form onSubmit={handleChatSubmit} className="flex gap-2">
                <Input 
                  placeholder="Ask a question about accessibility..."
                  value={chatMessage}
                  onChange={(e) => setChatMessage(e.target.value)}
                  className="flex-1"
                />
                <Button type="submit" loading={chatMutation.isPending} disabled={!chatMessage.trim()}>
                  <Send size={15} />
                </Button>
              </form>
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}
