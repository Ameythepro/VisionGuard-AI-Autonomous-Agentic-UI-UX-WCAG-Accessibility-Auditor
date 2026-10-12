import { create } from 'zustand';

interface WorkspaceState {
  auditUrl: string;
  setAuditUrl: (url: string) => void;
  
  patchUrl: string;
  setPatchUrl: (url: string) => void;
  
  cssPatch: string;
  setCssPatch: (css: string) => void;

  uploadedImage: string | null;
  setUploadedImage: (image: string | null) => void;
  
  analysisResult: any | null;
  setAnalysisResult: (result: any | null) => void;
  
  chatHistory: any[];
  setChatHistory: (history: any[]) => void;
  addChatMessage: (msg: any) => void;
  
  generatedCode: string;
  setGeneratedCode: (code: string) => void;
}

export const useWorkspaceStore = create<WorkspaceState>((set) => ({
  auditUrl: '',
  setAuditUrl: (url) => set({ auditUrl: url }),

  patchUrl: '',
  setPatchUrl: (url) => set({ patchUrl: url }),

  cssPatch: '',
  setCssPatch: (css) => set({ cssPatch: css }),
  
  uploadedImage: null,
  setUploadedImage: (image) => set({ uploadedImage: image }),
  
  analysisResult: null,
  setAnalysisResult: (result) => set({ analysisResult: result }),
  
  chatHistory: [],
  setChatHistory: (history) => set({ chatHistory: history }),
  addChatMessage: (msg) => set((state) => ({ chatHistory: [...state.chatHistory, msg] })),
  
  generatedCode: '',
  setGeneratedCode: (code) => set({ generatedCode: code }),
}));
