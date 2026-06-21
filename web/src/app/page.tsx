"use client";

import React, { useState, useEffect, useRef } from "react";
import { 
  Home, 
  FolderPlus, 
  Settings, 
  Search, 
  Upload, 
  RefreshCw, 
  Cpu, 
  AlertTriangle, 
  CheckCircle,
  HelpCircle,
  FileImage,
  Layers,
  ArrowRight,
  Menu,
  X
} from "lucide-react";

// API Base URL
const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

interface Stats {
  model_available: boolean;
  dataset_stats: {
    mentah: number;
    busuk: number;
    matang: number;
  };
  total_images: number;
  class_labels: string[];
}

interface PredictionResult {
  predicted_class: string;
  confidence: number;
  predictions: Record<string, number>;
  images: {
    original: string;
    grayscale: string;
    hsv_hue: string;
    canny_edges: string;
    resized: string;
  };
  activation_maps: string[];
}

export default function TomatoDetector() {
  const [activeTab, setActiveTab] = useState<"dashboard" | "generator" | "training" | "detection">("dashboard");
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  
  // API states
  const [stats, setStats] = useState<Stats | null>(null);
  const [statsLoading, setStatsLoading] = useState(true);
  
  // Dataset Generator states
  const [numGen, setNumGen] = useState(100);
  const [generating, setGenerating] = useState(false);
  const [genStatus, setGenStatus] = useState("");

  // Model Training states
  const [training, setTraining] = useState(false);
  const [trainLogs, setTrainLogs] = useState("");
  const [trainEpoch, setTrainEpoch] = useState(0);
  const [trainStatus, setTrainStatus] = useState("idle");
  const logContainerRef = useRef<HTMLPreElement>(null);

  // Prediction states
  const [selectedImage, setSelectedImage] = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [predicting, setPredicting] = useState(false);
  const [prediction, setPrediction] = useState<PredictionResult | null>(null);
  const [predictError, setPredictError] = useState<string | null>(null);
  const [randomImageCat, setRandomImageCat] = useState<string | null>(null);

  // Load stats on mount
  const fetchStats = async () => {
    try {
      setStatsLoading(true);
      const res = await fetch(`${API_URL}/api/stats`);
      const data = await res.json();
      setStats(data);
    } catch (err) {
      console.error("Gagal memuat statistik:", err);
    } finally {
      setStatsLoading(false);
    }
  };

  useEffect(() => {
    fetchStats();
  }, []);

  // Poll training status when training
  useEffect(() => {
    let intervalId: NodeJS.Timeout;
    if (training) {
      intervalId = setInterval(async () => {
        try {
          const res = await fetch(`${API_URL}/api/train-status`);
          const data = await res.json();
          setTrainLogs(data.logs);
          setTrainEpoch(data.epoch);
          setTrainStatus(data.status);
          
          if (data.status === "completed" || data.status === "failed") {
            setTraining(false);
            fetchStats(); // refresh model availability
          }
        } catch (err) {
          console.error("Gagal memantau pelatihan:", err);
        }
      }, 1500);
    }
    return () => clearInterval(intervalId);
  }, [training]);

  // Scroll to bottom of training logs
  useEffect(() => {
    if (logContainerRef.current) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
    }
  }, [trainLogs]);

  // Handle image upload selection
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setSelectedImage(file);
      setRandomImageCat(null);
      setPrediction(null);
      setPredictError(null);
      
      const reader = new FileReader();
      reader.onload = () => {
        setImagePreview(reader.result as string);
      };
      reader.readAsDataURL(file);
    }
  };

  // Run prediction
  const runPrediction = async (fileToPredict: File) => {
    setPredicting(true);
    setPrediction(null);
    setPredictError(null);
    
    const formData = new FormData();
    formData.append("file", fileToPredict);
    
    try {
      const res = await fetch(`${API_URL}/api/predict`, {
        method: "POST",
        body: formData,
      });
      
      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || "Gagal memproses gambar.");
      }
      
      const data = await res.json();
      setPrediction(data);
    } catch (err: any) {
      setPredictError(err.message || "Gagal menghubungi server backend.");
    } finally {
      setPredicting(false);
    }
  };

  const handlePredictSubmit = () => {
    if (selectedImage) {
      runPrediction(selectedImage);
    }
  };

  // Trigger dataset generation
  const handleGenerateDataset = async () => {
    setGenerating(true);
    setGenStatus("Memulai pembuatan dataset...");
    
    try {
      const res = await fetch(`${API_URL}/api/generate-dataset`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ num_images: numGen }),
      });
      const data = await res.json();
      setGenStatus(data.message);
      
      // wait a bit then refresh stats
      setTimeout(() => {
        fetchStats();
        setGenerating(false);
        setGenStatus("");
      }, 5000);
    } catch (err) {
      setGenStatus("Gagal memicu pembuatan dataset.");
      setGenerating(false);
    }
  };

  // Trigger model training
  const handleTrainModel = async () => {
    try {
      setTrainLogs("Menginisialisasi pelatihan model...");
      setTrainEpoch(0);
      setTrainStatus("training");
      setTraining(true);
      
      const res = await fetch(`${API_URL}/api/train-model`, { method: "POST" });
      const data = await res.json();
      setTrainLogs(prev => prev + "\n" + data.message + "\n");
    } catch (err) {
      setTrainLogs(prev => prev + "\nGagal memulai pelatihan model.\n");
      setTraining(false);
      setTrainStatus("failed");
    }
  };

  // Fetch random test image
  const handleRandomTest = async () => {
    try {
      setPredicting(true);
      setPrediction(null);
      setPredictError(null);
      
      const res = await fetch(`${API_URL}/api/random-test`);
      if (!res.ok) {
        throw new Error("Gagal mengambil gambar acak. Pastikan dataset telah ter-generate.");
      }
      const data = await res.json();
      
      // Set image preview from base64
      setImagePreview(`data:image/jpeg;base64,${data.image_base64}`);
      setRandomImageCat(data.real_class);
      
      // Convert base64 back to file to submit for prediction
      const base64Response = await fetch(`data:image/jpeg;base64,${data.image_base64}`);
      const blob = await base64Response.blob();
      const file = new File([blob], data.filename || "test.jpg", { type: "image/jpeg" });
      setSelectedImage(file);
      
      // Auto run prediction
      await runPrediction(file);
    } catch (err: any) {
      setPredictError(err.message || "Gagal mengambil gambar acak.");
      setPredicting(false);
    }
  };

  // Helper for predicted class colors
  const getClassBadgeStyle = (label: string) => {
    switch (label) {
      case "matang":
        return "bg-red-500/20 text-red-400 border-red-500/40";
      case "mentah":
        return "bg-emerald-500/20 text-emerald-400 border-emerald-500/40";
      case "busuk":
        return "bg-amber-600/20 text-amber-500 border-amber-600/40";
      default:
        return "bg-slate-500/20 text-slate-400 border-slate-500/40";
    }
  };

  return (
    <div className="flex flex-col lg:flex-row h-screen overflow-hidden bg-[#090b11] text-slate-200 font-sans">
      {/* Sidebar Navigation */}
      <aside className="w-full lg:w-80 bg-[#0f111a] border-b lg:border-r border-slate-800/80 p-4 lg:p-6 flex flex-col justify-between shrink-0 z-30 overflow-y-auto lg:overflow-y-visible">
        <div>
          {/* Brand Logo & Mobile Menu Toggle */}
          <div className="flex items-center justify-between lg:block mb-0 lg:mb-10">
            <div className="flex items-center space-x-3 px-2">
              <div className="bg-red-500/10 p-2 rounded-lg border border-red-500/30">
                <span className="text-2xl">🍅</span>
              </div>
              <div>
                <h2 className="font-extrabold text-xl text-slate-100 tracking-tight">TomatCNN</h2>
                <p className="text-xs text-slate-500 font-medium">Ripeness Detection System</p>
              </div>
            </div>

            {/* Mobile Hamburger Button */}
            <button 
              onClick={() => setIsMenuOpen(!isMenuOpen)}
              className="p-2 bg-slate-900 border border-slate-800 hover:bg-slate-800/80 rounded-xl text-slate-400 hover:text-slate-200 transition lg:hidden"
            >
              {isMenuOpen ? <X size={20} /> : <Menu size={20} />}
            </button>
          </div>

          {/* Nav Links & System Stats */}
          <div className={`${isMenuOpen ? "block" : "hidden"} lg:block mt-4 lg:mt-0 space-y-6`}>
            {/* Nav Links */}
            <nav className="space-y-1">
              <button
                onClick={() => { setActiveTab("dashboard"); setIsMenuOpen(false); }}
                className={`w-full flex items-center space-x-3 px-4 py-3 rounded-xl font-semibold text-sm transition-all duration-200 ${
                  activeTab === "dashboard"
                    ? "bg-gradient-to-r from-red-500/10 to-red-500/5 text-red-400 border-l-2 border-red-500 px-[14px]"
                    : "text-slate-400 hover:bg-slate-800/40 hover:text-slate-200"
                }`}
              >
                <Home size={18} />
                <span>Dashboard & Teori</span>
              </button>

              <button
                onClick={() => { setActiveTab("generator"); setIsMenuOpen(false); }}
                className={`w-full flex items-center space-x-3 px-4 py-3 rounded-xl font-semibold text-sm transition-all duration-200 ${
                  activeTab === "generator"
                    ? "bg-gradient-to-r from-red-500/10 to-red-500/5 text-red-400 border-l-2 border-red-500 px-[14px]"
                    : "text-slate-400 hover:bg-slate-800/40 hover:text-slate-200"
                }`}
              >
                <FolderPlus size={18} />
                <span>Dataset Generator</span>
              </button>

              <button
                onClick={() => { setActiveTab("training"); setIsMenuOpen(false); }}
                className={`w-full flex items-center space-x-3 px-4 py-3 rounded-xl font-semibold text-sm transition-all duration-200 ${
                  activeTab === "training"
                    ? "bg-gradient-to-r from-red-500/10 to-red-500/5 text-red-400 border-l-2 border-red-500 px-[14px]"
                    : "text-slate-400 hover:bg-slate-800/40 hover:text-slate-200"
                }`}
              >
                <Settings size={18} />
                <span>Pelatihan Model</span>
              </button>

              <button
                onClick={() => { setActiveTab("detection"); setIsMenuOpen(false); }}
                className={`w-full flex items-center space-x-3 px-4 py-3 rounded-xl font-semibold text-sm transition-all duration-200 ${
                  activeTab === "detection"
                    ? "bg-gradient-to-r from-red-500/10 to-red-500/5 text-red-400 border-l-2 border-red-500 px-[14px]"
                    : "text-slate-400 hover:bg-slate-800/40 hover:text-slate-200"
                }`}
              >
                <Search size={18} />
                <span>Deteksi Kematangan</span>
              </button>
            </nav>
          </div>
        </div>

        {/* Sidebar Footer Stats (collapsible as well) */}
        <div className={`${isMenuOpen ? "block" : "hidden"} lg:block mt-4 lg:mt-0 bg-slate-900/60 border border-slate-800/60 rounded-xl p-4 space-y-3`}>
          <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider">Status Sistem</h4>
          {statsLoading ? (
            <div className="flex items-center space-x-2 text-xs text-slate-500">
              <RefreshCw size={12} className="animate-spin" />
              <span>Memuat status...</span>
            </div>
          ) : (
            <div className="space-y-2 text-xs">
              <div className="flex justify-between items-center">
                <span className="text-slate-500">Model CNN:</span>
                {stats?.model_available ? (
                  <span className="text-emerald-400 font-bold flex items-center gap-1">
                    <CheckCircle size={12} /> TERSEDIA
                  </span>
                ) : (
                  <span className="text-amber-500 font-bold flex items-center gap-1">
                    <AlertTriangle size={12} /> BELUM ADA
                  </span>
                )}
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Total Dataset:</span>
                <span className="text-slate-300 font-semibold">{stats?.total_images || 0} citra</span>
              </div>
              {stats?.total_images ? (
                <div className="pt-2 border-t border-slate-800/60 grid grid-cols-3 gap-1 text-center text-[10px]">
                  <div className="bg-emerald-500/10 text-emerald-400 rounded py-1 border border-emerald-500/20">
                    <div className="font-bold">{stats.dataset_stats.mentah}</div>
                    <div className="text-[8px] text-slate-500 uppercase">Mentah</div>
                  </div>
                  <div className="bg-red-500/10 text-red-400 rounded py-1 border border-red-500/20">
                    <div className="font-bold">{stats.dataset_stats.matang}</div>
                    <div className="text-[8px] text-slate-500 uppercase">Matang</div>
                  </div>
                  <div className="bg-amber-600/10 text-amber-500 rounded py-1 border border-amber-600/20">
                    <div className="font-bold">{stats.dataset_stats.busuk}</div>
                    <div className="text-[8px] text-slate-500 uppercase">Busuk</div>
                  </div>
                </div>
              ) : null}
            </div>
          )}
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 p-4 md:p-10 overflow-y-auto">
        {/* Top Header Title */}
        <header className="mb-10 flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
          <div>
            <h1 className="text-3xl font-extrabold text-slate-100 tracking-tight bg-gradient-to-r from-red-500 to-amber-500 bg-clip-text text-transparent">
              Deteksi Kematangan Tomat
            </h1>
            <p className="text-slate-500 text-sm mt-1">Studi Kasus Grafika Komputer & Convolutional Neural Network (CNN)</p>
          </div>
          <button 
            onClick={fetchStats}
            className="p-3 bg-slate-900 border border-slate-800 hover:bg-slate-800/80 rounded-xl text-slate-400 hover:text-slate-200 transition shrink-0"
          >
            <RefreshCw size={18} />
          </button>
        </header>

        {/* ==================== TAB 1: DASHBOARD ==================== */}
        {activeTab === "dashboard" && (
          <div className="space-y-6">
            <div className="bg-slate-800/20 border border-slate-700/30 backdrop-blur-md rounded-2xl p-6">
              <h3 className="text-lg font-bold text-slate-200 mb-3 flex items-center gap-2">
                <FileImage size={18} className="text-red-500" /> Pendahuluan
              </h3>
              <p className="text-slate-400 text-sm leading-relaxed">
                Dalam bidang **Grafika Komputer** dan **Pengolahan Citra Digital**, warna dan bentuk gambar diwakili sebagai matriks nilai numerik (pixel). Proyek studi kasus ini menggabungkan pemrosesan citra digital klasik dengan metode modern **Convolutional Neural Networks (CNN)** untuk mendeteksi kematangan buah tomat secara otomatis.
              </p>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-6">
                <div className="bg-emerald-500/5 border border-emerald-500/10 rounded-xl p-4">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="text-lg">🟢</span>
                    <h4 className="font-bold text-emerald-400 text-sm">Kategori: Mentah</h4>
                  </div>
                  <p className="text-xs text-slate-500 leading-relaxed">
                    Tomat segar berwarna hijau pekat. Memiliki kandungan klorofil tinggi yang memberikan pantulan warna hijau kuat pada kanal Hue (HSV).
                  </p>
                </div>
                <div className="bg-red-500/5 border border-red-500/10 rounded-xl p-4">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="text-lg">🔴</span>
                    <h4 className="font-bold text-red-400 text-sm">Kategori: Matang</h4>
                  </div>
                  <p className="text-xs text-slate-500 leading-relaxed">
                    Tomat segar berwarna merah cerah. Kandungan likopen maksimal memberikan representasi nilai warna merah pekat yang dominan.
                  </p>
                </div>
                <div className="bg-amber-600/5 border border-amber-600/10 rounded-xl p-4">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="text-lg">🟤</span>
                    <h4 className="font-bold text-amber-500 text-sm">Kategori: Busuk</h4>
                  </div>
                  <p className="text-xs text-slate-500 leading-relaxed">
                    Tomat yang mengalami pembusukan, ditandai dengan perubahan warna cokelat kusam/gelap, pembentukan bercak-bercak pembusukan, dan hilangnya kilau pantulan permukaan.
                  </p>
                </div>
              </div>
            </div>

            <div className="bg-slate-800/20 border border-slate-700/30 backdrop-blur-md rounded-2xl p-6">
              <h3 className="text-lg font-bold text-slate-200 mb-3 flex items-center gap-2">
                <Cpu size={18} className="text-amber-500" /> Bagaimana CNN Bekerja (Aspek Grafika Komputer)
              </h3>
              <p className="text-slate-400 text-sm leading-relaxed mb-4">
                CNN bekerja dengan menerapkan filter konvolusi spasial (kernel) secara berlapis pada matriks citra input:
              </p>
              <div className="space-y-3 text-sm">
                <div className="flex items-start space-x-3">
                  <div className="bg-slate-900 border border-slate-800 font-bold px-3 py-1 rounded text-slate-300">1</div>
                  <div>
                    <h5 className="font-semibold text-slate-300">Lapisan Konvolusi (Convolutional Layer)</h5>
                    <p className="text-xs text-slate-500 mt-0.5">Menerapkan kernel filter (seperti filter Sobel untuk deteksi tepi atau filter segmentasi warna) untuk mengekstrak fitur visual seperti garis, kontur, dan gradasi warna.</p>
                  </div>
                </div>
                <div className="flex items-start space-x-3">
                  <div className="bg-slate-900 border border-slate-800 font-bold px-3 py-1 rounded text-slate-300">2</div>
                  <div>
                    <h5 className="font-semibold text-slate-300">Lapisan Pooling (Pooling Layer)</h5>
                    <p className="text-xs text-slate-500 mt-0.5">Mengurangi dimensi spasial gambar (downsampling) menggunakan Max Pooling untuk mempertahankan fitur terpenting dan menghemat beban komputasi.</p>
                  </div>
                </div>
                <div className="flex items-start space-x-3">
                  <div className="bg-slate-900 border border-slate-800 font-bold px-3 py-1 rounded text-slate-300">3</div>
                  <div>
                    <h5 className="font-semibold text-slate-300">Lapisan Flattening & Fully Connected</h5>
                    <p className="text-xs text-slate-500 mt-0.5">Mengubah matriks 2D fitur menjadi vektor 1D dan mengklasifikasikannya ke dalam kelas target (Mentah, Busuk, Matang) menggunakan fungsi probabilitas Softmax.</p>
                  </div>
                </div>
              </div>
              <div className="mt-6 bg-[#090b11] border border-slate-800/80 rounded-xl p-4">
                <div className="text-xs font-mono text-slate-500 uppercase tracking-widest mb-2">Arsitektur Alur CNN</div>
                <pre className="text-xs font-mono text-red-400 overflow-x-auto">
                  {`[Input Image 128x128x3] ➔ [Conv2D: 16 filters (conv_1)] ➔ [Max Pooling] ➔ [Conv2D: 32 filters] ➔ [Max Pooling] ➔ [Flatten] ➔ [Dense: 64] ➔ [Output Softmax: 3 Classes]`}
                </pre>
              </div>
            </div>

            {/* Academic & Developer Profile Card */}
            <div className="bg-slate-800/20 border border-slate-700/30 backdrop-blur-md rounded-2xl p-6">
              <h3 className="text-lg font-bold text-slate-200 mb-6 flex items-center gap-2">
                <span className="text-red-500">🎓</span> Profil Akademik & Tim Pengembang
              </h3>
              
              <div className="space-y-6">
                {/* Dosen Pengampu */}
                <div className="bg-[#0f111a]/60 border border-slate-800/60 rounded-xl p-5 flex items-center space-x-4 max-w-xl mx-auto">
                  <div className="w-20 h-20 rounded-full overflow-hidden border-2 border-red-500/30 shrink-0 bg-slate-900 flex items-center justify-center">
                    <img 
                      src="/dosen_pengampu.jpg" 
                      alt="Jeffry Andika Putra, S.T., M.M., M.Eng" 
                      className="w-full h-full object-cover"
                      onError={(e) => {
                        (e.target as HTMLImageElement).src = "https://placehold.co/150x150/0f111a/cbd5e1?text=Dosen";
                      }}
                    />
                  </div>
                  <div>
                    <span className="text-[10px] font-mono text-slate-500 uppercase tracking-wider block mb-1">Dosen Pengampu</span>
                    <h4 className="font-bold text-slate-200 text-sm leading-snug">Jeffry Andika Putra, S.T., M.M., M.Eng</h4>
                    <p className="text-xs text-slate-400 mt-1">Dosen Pengampu Grafika Komputer</p>
                  </div>
                </div>

                <div className="border-t border-slate-800/40 my-6"></div>

                {/* Tim Pengembang */}
                <div>
                  <h5 className="text-[10px] font-mono text-slate-500 uppercase tracking-wider mb-4 text-center">Tim Pengembang Sistem</h5>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    {/* Mahasiswa 1 */}
                    <div className="bg-[#0f111a]/60 border border-slate-800/60 rounded-xl p-5 flex items-center space-x-4">
                      <div className="w-20 h-20 rounded-full overflow-hidden border-2 border-red-500/30 shrink-0 bg-slate-900 flex items-center justify-center">
                        <img 
                          src="/yusuf.jpg" 
                          alt="Yusuf Mustofa" 
                          className="w-full h-full object-cover"
                          onError={(e) => {
                            (e.target as HTMLImageElement).src = "https://placehold.co/150x150/0f111a/cbd5e1?text=Yusuf";
                          }}
                        />
                      </div>
                      <div>
                        <span className="text-[10px] font-mono text-slate-500 uppercase tracking-wider block mb-1">Mahasiswa / Pengembang</span>
                        <h4 className="font-bold text-slate-200 text-sm leading-snug">Yusuf Mustofa</h4>
                        <p className="text-xs text-slate-400 mt-1">Mahasiswa & Pengembang</p>
                      </div>
                    </div>

                    {/* Mahasiswa 2 */}
                    <div className="bg-[#0f111a]/60 border border-slate-800/60 rounded-xl p-5 flex items-center space-x-4">
                      <div className="w-20 h-20 rounded-full overflow-hidden border-2 border-red-500/30 shrink-0 bg-slate-900 flex items-center justify-center">
                        <img 
                          src="/dicki_kusumah.jpeg" 
                          alt="Dicki Kusumah" 
                          className="w-full h-full object-cover"
                          onError={(e) => {
                            (e.target as HTMLImageElement).src = "https://placehold.co/150x150/0f111a/cbd5e1?text=Dicki";
                          }}
                        />
                      </div>
                      <div>
                        <span className="text-[10px] font-mono text-slate-500 uppercase tracking-wider block mb-1">Mahasiswa / Pengembang</span>
                        <h4 className="font-bold text-slate-200 text-sm leading-snug">Dicki Kusumah</h4>
                        <p className="text-xs text-slate-400 mt-1">Laporan & Dataset</p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ==================== TAB 2: DATASET GENERATOR ==================== */}
        {activeTab === "generator" && (
          <div className="space-y-6">
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Generator Settings Card */}
              <div className="bg-slate-800/20 border border-slate-700/30 backdrop-blur-md rounded-2xl p-6 flex flex-col justify-between">
                <div>
                  <h3 className="text-lg font-bold text-slate-200 mb-2 flex items-center gap-2">
                    <FolderPlus size={18} className="text-red-500" /> Generator Dataset Tomat Sintetis
                  </h3>
                  <p className="text-xs text-slate-500 leading-relaxed mb-6">
                    Membuat dataset buatan (sintetis) berkualitas tinggi menggunakan pustaka pengolah gambar Python (`Pillow` dan `NumPy`). Gambar tomat dirender secara prosedural dengan gradasi warna, kilau cahaya, bercak busuk, dan tangkai daun acak.
                  </p>

                  <div className="space-y-4">
                    <div>
                      <label className="text-xs font-bold text-slate-400 block mb-2">
                        Jumlah Gambar per Kategori: <span className="text-red-400">{numGen}</span>
                      </label>
                      <input 
                        type="range" 
                        min="10" 
                        max="200" 
                        step="10"
                        value={numGen} 
                        onChange={(e) => setNumGen(Number(e.target.value))}
                        className="w-full accent-red-500"
                        disabled={generating}
                      />
                      <div className="flex justify-between text-[10px] text-slate-600 mt-1 font-mono">
                        <span>10</span>
                        <span>100</span>
                        <span>200</span>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="mt-8 pt-4 border-t border-slate-800/60">
                  <button
                    onClick={handleGenerateDataset}
                    disabled={generating}
                    className="w-full flex items-center justify-center space-x-2 py-3 bg-red-600 hover:bg-red-500 text-white rounded-xl font-bold text-sm disabled:opacity-50 disabled:cursor-not-allowed transition"
                  >
                    {generating ? (
                      <>
                        <RefreshCw size={16} className="animate-spin" />
                        <span>Sedang Membuat Citra...</span>
                      </>
                    ) : (
                      <span>🚀 Generate Dataset Baru</span>
                    )}
                  </button>
                  {genStatus && (
                    <div className="mt-3 text-xs text-slate-500 text-center font-medium font-mono animate-pulse">
                      {genStatus}
                    </div>
                  )}
                </div>
              </div>

              {/* Sample Previews Card */}
              <div className="lg:col-span-2 bg-slate-800/20 border border-slate-700/30 backdrop-blur-md rounded-2xl p-6">
                <h3 className="text-lg font-bold text-slate-200 mb-6">Preview Sampel Dataset</h3>
                
                {stats?.total_images && stats.total_images > 0 ? (
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    {/* Raw Tomato Preview */}
                    <div className="bg-slate-900/40 border border-slate-800/80 rounded-xl p-4 flex flex-col items-center">
                      <span className="badge badge-mentah border px-3 py-1 rounded-full text-xs font-bold mb-4 bg-emerald-500/10 text-emerald-400 border-emerald-500/20">
                        MENTAH
                      </span>
                      <div className="w-full aspect-square bg-slate-950 rounded-lg flex items-center justify-center overflow-hidden border border-slate-800/40">
                        <img 
                          src={`${API_URL}/api/random-test?nocache=${Math.random()}`} 
                          alt="Tomato Mentah" 
                          className="w-full h-full object-cover"
                          onError={(e) => {
                            // fallback if random endpoint is slow
                            (e.target as HTMLImageElement).src = `https://placehold.co/128x128/050d09/10b981?text=Mentah`;
                          }}
                        />
                      </div>
                      <p className="text-[10px] text-slate-500 mt-2 font-mono">Contoh Citra Latih Mentah</p>
                    </div>

                    {/* Rotten Tomato Preview */}
                    <div className="bg-slate-900/40 border border-slate-800/80 rounded-xl p-4 flex flex-col items-center">
                      <span className="badge badge-busuk border px-3 py-1 rounded-full text-xs font-bold mb-4 bg-amber-600/10 text-amber-500 border-amber-600/20">
                        BUSUK
                      </span>
                      <div className="w-full aspect-square bg-slate-950 rounded-lg flex items-center justify-center overflow-hidden border border-slate-800/40">
                        <img 
                          src={`https://placehold.co/128x128/0d0a05/d97706?text=Busuk`} 
                          alt="Tomato Busuk" 
                          className="w-full h-full object-cover"
                        />
                      </div>
                      <p className="text-[10px] text-slate-500 mt-2 font-mono">Contoh Citra Latih Busuk</p>
                    </div>

                    {/* Ripe Tomato Preview */}
                    <div className="bg-slate-900/40 border border-slate-800/80 rounded-xl p-4 flex flex-col items-center">
                      <span className="badge badge-matang border px-3 py-1 rounded-full text-xs font-bold mb-4 bg-red-500/10 text-red-400 border-red-500/20">
                        MATANG
                      </span>
                      <div className="w-full aspect-square bg-slate-950 rounded-lg flex items-center justify-center overflow-hidden border border-slate-800/40">
                        <img 
                          src={`https://placehold.co/128x128/0d0505/ef4444?text=Matang`} 
                          alt="Tomato Matang" 
                          className="w-full h-full object-cover"
                        />
                      </div>
                      <p className="text-[10px] text-slate-500 mt-2 font-mono">Contoh Citra Latih Matang</p>
                    </div>
                  </div>
                ) : (
                  <div className="h-64 flex flex-col items-center justify-center border-2 border-dashed border-slate-800 rounded-xl text-slate-500">
                    <AlertTriangle size={32} className="text-amber-500 mb-2 animate-bounce" />
                    <span className="text-sm font-semibold">Dataset Belum Terbentuk</span>
                    <span className="text-xs text-slate-600 mt-1">Harap klik tombol 'Generate Dataset Baru' di sebelah kiri.</span>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* ==================== TAB 3: PELATIHAN MODEL ==================== */}
        {activeTab === "training" && (
          <div className="space-y-6">
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Training Control Card */}
              <div className="bg-slate-800/20 border border-slate-700/30 backdrop-blur-md rounded-2xl p-6 flex flex-col justify-between">
                <div>
                  <h3 className="text-lg font-bold text-slate-200 mb-2 flex items-center gap-2">
                    <Settings size={18} className="text-red-500" /> Pelatihan Model CNN
                  </h3>
                  <p className="text-xs text-slate-500 leading-relaxed mb-6">
                    Melakukan fitting data latih (80%) dan data validasi (20%) menggunakan TensorFlow. Inisiasi proses ini secara langsung dan pantau log kemajuan epoch secara real-time.
                  </p>

                  {/* Status Indicator */}
                  <div className="bg-slate-900/60 border border-slate-850 rounded-xl p-4 space-y-3">
                    <div className="flex justify-between items-center text-xs">
                      <span className="text-slate-500 font-semibold uppercase">Status Pelatihan</span>
                      {trainStatus === "training" ? (
                        <span className="text-amber-400 font-bold flex items-center gap-1 animate-pulse">
                          <RefreshCw size={12} className="animate-spin" /> RUNNING
                        </span>
                      ) : trainStatus === "completed" ? (
                        <span className="text-emerald-400 font-bold flex items-center gap-1">
                          <CheckCircle size={12} /> BERHASIL
                        </span>
                      ) : trainStatus === "failed" ? (
                        <span className="text-red-500 font-bold flex items-center gap-1">
                          <AlertTriangle size={12} /> GAGAL
                        </span>
                      ) : (
                        <span className="text-slate-400 font-bold">IDLE</span>
                      )}
                    </div>
                    
                    {trainStatus === "training" && (
                      <div className="space-y-1.5">
                        <div className="flex justify-between text-[10px] text-slate-400 font-mono">
                          <span>Progress Epoch</span>
                          <span>{trainEpoch}/10</span>
                        </div>
                        <div className="w-full bg-slate-950 h-2 rounded-full overflow-hidden border border-slate-800/80">
                          <div 
                            className="bg-red-500 h-full rounded-full transition-all duration-300"
                            style={{ width: `${(trainEpoch / 10) * 100}%` }}
                          ></div>
                        </div>
                      </div>
                    )}
                  </div>
                </div>

                <div className="mt-8 pt-4 border-t border-slate-800/60">
                  {stats?.total_images && stats.total_images > 0 ? (
                    <button
                      onClick={handleTrainModel}
                      disabled={training}
                      className="w-full flex items-center justify-center space-x-2 py-3 bg-red-600 hover:bg-red-500 text-white rounded-xl font-bold text-sm disabled:opacity-50 disabled:cursor-not-allowed transition"
                    >
                      {training ? (
                        <>
                          <RefreshCw size={16} className="animate-spin" />
                          <span>Menjalankan Pelatihan...</span>
                        </>
                      ) : (
                        <span>🏋️ Mulai Pelatihan Model</span>
                      )}
                    </button>
                  ) : (
                    <div className="bg-red-500/10 text-red-400 border border-red-500/20 text-xs p-3 rounded-lg text-center font-medium">
                      Harap isi dataset terlebih dahulu untuk melakukan pelatihan model.
                    </div>
                  )}
                </div>
              </div>

              {/* Logs Card */}
              <div className="lg:col-span-2 bg-slate-800/20 border border-slate-700/30 backdrop-blur-md rounded-2xl p-6 flex flex-col">
                <h3 className="text-lg font-bold text-slate-200 mb-4">Konsol Log Pelatihan</h3>
                <div className="flex-1 bg-slate-950 border border-slate-850 rounded-xl p-4 overflow-hidden flex flex-col h-72">
                  <pre 
                    ref={logContainerRef}
                    className="flex-1 font-mono text-xs text-emerald-400/90 overflow-y-auto leading-relaxed whitespace-pre-wrap select-text selection:bg-emerald-500/20"
                  >
                    {trainLogs || "Konsol log kosong. Mulai proses pelatihan untuk melihat output di sini."}
                  </pre>
                </div>
              </div>
            </div>
            
            {/* History Curves */}
            {trainStatus === "completed" && (
              <div className="bg-slate-800/20 border border-slate-700/30 backdrop-blur-md rounded-2xl p-6">
                <h3 className="text-lg font-bold text-slate-200 mb-4">Grafik Evaluasi Pelatihan</h3>
                <div className="bg-slate-950 border border-slate-850 rounded-xl p-4 flex justify-center">
                  <img 
                    src={`${API_URL}/training_history.png?nocache=${Math.random()}`} 
                    alt="Kurva Akurasi dan Loss" 
                    className="max-w-full h-auto rounded border border-slate-800"
                    onError={(e) => {
                      (e.target as HTMLImageElement).style.display = "none";
                    }}
                  />
                </div>
              </div>
            )}
          </div>
        )}

        {/* ==================== TAB 4: DETEKSI & ANALISIS ==================== */}
        {activeTab === "detection" && (
          <div className="space-y-6">
            {!stats?.model_available ? (
              <div className="bg-amber-600/10 border border-amber-600/20 rounded-2xl p-6 flex items-center gap-4 text-amber-500">
                <AlertTriangle size={24} className="shrink-0" />
                <div>
                  <h4 className="font-bold text-sm">Model CNN Belum Tersedia!</h4>
                  <p className="text-xs text-slate-400 mt-1">
                    Silakan pergi ke Tab **Pelatihan Model** untuk melatih model CNN terlebih dahulu sebelum mencoba deteksi kematangan tomat.
                  </p>
                </div>
              </div>
            ) : (
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Image Input Card */}
                <div className="bg-slate-800/20 border border-slate-700/30 backdrop-blur-md rounded-2xl p-6 flex flex-col justify-between">
                  <div>
                    <h3 className="text-lg font-bold text-slate-200 mb-4 flex items-center gap-2">
                      <Upload size={18} className="text-red-500" /> Input Citra Tomat
                    </h3>

                    {/* Image Selector Drop Area */}
                    <div className="space-y-4">
                      <div className="border-2 border-dashed border-slate-800 hover:border-slate-700 hover:bg-slate-900/20 rounded-xl p-6 transition text-center relative cursor-pointer group">
                        <input 
                          type="file" 
                          accept="image/*" 
                          onChange={handleFileChange}
                          className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                        />
                        <Upload size={24} className="text-slate-500 group-hover:text-slate-400 mx-auto mb-2 transition" />
                        <span className="text-xs font-semibold text-slate-400 block mb-1">Unggah Citra Tomat</span>
                        <span className="text-[10px] text-slate-600 font-mono">PNG, JPG, JPEG</span>
                      </div>

                      <div className="text-center font-bold text-slate-600 text-xs py-1">ATAU</div>

                      <button
                        onClick={handleRandomTest}
                        disabled={predicting}
                        className="w-full flex items-center justify-center space-x-2 py-2.5 bg-slate-900 hover:bg-slate-800 text-slate-300 border border-slate-800 rounded-xl text-xs font-bold transition disabled:opacity-50"
                      >
                        <RefreshCw size={12} className={predicting ? "animate-spin" : ""} />
                        <span>🎲 Uji Gambar Acak dari Dataset</span>
                      </button>
                    </div>
                  </div>

                  {/* Image Preview Container */}
                  <div className="mt-8 pt-6 border-t border-slate-800/60 flex-1 flex flex-col justify-center">
                    {imagePreview ? (
                      <div className="space-y-4">
                        <div className="w-full aspect-square bg-slate-950 rounded-xl overflow-hidden border border-slate-850 flex items-center justify-center">
                          <img src={imagePreview} alt="Pratinjau" className="max-w-full max-h-full object-contain" />
                        </div>
                        {randomImageCat && (
                          <div className="text-center">
                            <span className="text-[10px] font-mono text-slate-500 uppercase">Label Asli:</span>
                            <span className={`ml-2 badge text-xs font-bold border px-2 py-0.5 rounded-full ${getClassBadgeStyle(randomImageCat)}`}>
                              {randomImageCat.toUpperCase()}
                            </span>
                          </div>
                        )}
                        {!predicting && selectedImage && !prediction && (
                          <button
                            onClick={handlePredictSubmit}
                            className="w-full py-2.5 bg-red-600 hover:bg-red-500 text-white rounded-xl text-xs font-bold transition"
                          >
                            🎯 Jalankan Prediksi CNN
                          </button>
                        )}
                      </div>
                    ) : (
                      <div className="h-48 flex flex-col items-center justify-center border border-slate-850 rounded-xl bg-slate-950/40 text-slate-600">
                        <FileImage size={24} className="mb-2" />
                        <span className="text-xs">Belum ada gambar terpilih</span>
                      </div>
                    )}

                    {predictError && (
                      <div className="mt-4 p-3 bg-red-500/10 border border-red-500/20 text-red-400 rounded-lg text-xs leading-relaxed">
                        {predictError}
                      </div>
                    )}
                  </div>
                </div>

                {/* Analysis Results Cards */}
                <div className="lg:col-span-2 space-y-6">
                  {predicting ? (
                    <div className="bg-slate-800/20 border border-slate-700/30 backdrop-blur-md rounded-2xl p-6 h-96 flex flex-col items-center justify-center text-slate-500">
                      <RefreshCw size={36} className="animate-spin text-red-500 mb-4" />
                      <span className="text-sm font-semibold">Sedang Menganalisis Citra Tomat...</span>
                      <span className="text-xs text-slate-600 mt-1">Mengekstrak filter konvolusi dan menghitung klasifikasi CNN.</span>
                    </div>
                  ) : prediction ? (
                    <>
                      {/* Classification Score Card */}
                      <div className="bg-slate-800/20 border border-slate-700/30 backdrop-blur-md rounded-2xl p-6">
                        <h3 className="text-lg font-bold text-slate-200 mb-6 flex items-center gap-2">
                          <CheckCircle size={18} className="text-emerald-500" /> Hasil Klasifikasi CNN
                        </h3>
                        
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 items-center mb-6">
                          <div className="space-y-2">
                            <span className="text-slate-500 text-xs font-semibold uppercase tracking-wider block">Kategori Terprediksi</span>
                            <div className="flex items-center gap-3">
                              <span className={`badge border text-lg px-4 py-1.5 font-extrabold rounded-full tracking-wide shadow-glow ${getClassBadgeStyle(prediction.predicted_class)}`}>
                                {prediction.predicted_class.toUpperCase()}
                              </span>
                            </div>
                          </div>
                          <div className="space-y-1">
                            <span className="text-slate-500 text-xs font-semibold uppercase tracking-wider block">Tingkat Keyakinan</span>
                            <span className="text-3xl font-black text-slate-100 tracking-tight">
                              {(prediction.confidence * 100).toFixed(2)}%
                            </span>
                          </div>
                        </div>

                        <div className="space-y-4 pt-6 border-t border-slate-800/60">
                          <h5 className="text-xs font-bold text-slate-400 uppercase tracking-wider">Distribusi Probabilitas Kelas:</h5>
                          <div className="space-y-3">
                            {Object.entries(prediction.predictions).map(([label, prob]) => (
                              <div key={label} className="space-y-1">
                                <div className="flex justify-between text-xs font-semibold">
                                  <span className="text-slate-300 capitalize">{label}</span>
                                  <span className="text-slate-400">{(prob * 100).toFixed(2)}%</span>
                                </div>
                                <div className="w-full bg-slate-950 h-2.5 rounded-full overflow-hidden border border-slate-850">
                                  <div 
                                    className={`h-full rounded-full transition-all duration-300 ${
                                      label === "matang" ? "bg-red-500" : label === "mentah" ? "bg-emerald-500" : "bg-amber-500"
                                    }`}
                                    style={{ width: `${prob * 100}%` }}
                                  ></div>
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      </div>

                      {/* Computer Graphics Pipeline Card */}
                      <div className="bg-slate-800/20 border border-slate-700/30 backdrop-blur-md rounded-2xl p-6">
                        <h3 className="text-lg font-bold text-slate-200 mb-3 flex items-center gap-2">
                          <Layers size={18} className="text-red-500" /> Tahapan Pengolahan Citra Digital (Grafika Komputer)
                        </h3>
                        <p className="text-xs text-slate-500 mb-6 leading-relaxed">
                          Menampilkan proses ekstraksi representasi matriks citra piksel yang dibaca sebelum diumpankan ke model CNN.
                        </p>

                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                          <div className="bg-slate-900/60 border border-slate-850 p-3 rounded-xl flex flex-col items-center">
                            <span className="text-[10px] font-mono text-slate-500 uppercase mb-2">1. Grayscale</span>
                            <div className="w-full aspect-square bg-slate-950 rounded-lg overflow-hidden border border-slate-800/30">
                              <img src={`data:image/png;base64,${prediction.images.grayscale}`} alt="Grayscale" className="w-full h-full object-cover" />
                            </div>
                          </div>
                          <div className="bg-slate-900/60 border border-slate-850 p-3 rounded-xl flex flex-col items-center">
                            <span className="text-[10px] font-mono text-slate-500 uppercase mb-2">2. Hue (HSV)</span>
                            <div className="w-full aspect-square bg-slate-950 rounded-lg overflow-hidden border border-slate-800/30">
                              <img src={`data:image/png;base64,${prediction.images.hsv_hue}`} alt="HSV Hue" className="w-full h-full object-cover" />
                            </div>
                          </div>
                          <div className="bg-slate-900/60 border border-slate-850 p-3 rounded-xl flex flex-col items-center">
                            <span className="text-[10px] font-mono text-slate-500 uppercase mb-2">3. Canny Edge</span>
                            <div className="w-full aspect-square bg-slate-950 rounded-lg overflow-hidden border border-slate-800/30">
                              <img src={`data:image/png;base64,${prediction.images.canny_edges}`} alt="Edges" className="w-full h-full object-cover" />
                            </div>
                          </div>
                          <div className="bg-slate-900/60 border border-slate-850 p-3 rounded-xl flex flex-col items-center">
                            <span className="text-[10px] font-mono text-slate-500 uppercase mb-2">4. CNN Input</span>
                            <div className="w-full aspect-square bg-slate-950 rounded-lg overflow-hidden border border-slate-800/30">
                              <img src={`data:image/png;base64,${prediction.images.resized}`} alt="Resized" className="w-full h-full object-cover" />
                            </div>
                          </div>
                        </div>
                        <div className="mt-4 p-4 bg-slate-950/60 border border-slate-850 rounded-xl space-y-2 text-xs leading-relaxed text-slate-400">
                          <p>🔍 **Prosedur Grafika Komputer & Citra Digital:**</p>
                          <ul className="list-disc pl-4 space-y-1.5 text-slate-500">
                            <li>**Grayscale** mereduksi dimensi dengan memisahkan intensitas cahaya (luminositas) dari warna.</li>
                            <li>**Hue Channel (HSV)** mendeteksi spektrum warna murni (warna hijau mentah, merah matang, dan bercak kecokelatan berada di range Hue terpisah).</li>
                            <li>**Canny Edge Detection** mengkalkulasi gradien spasial matriks untuk menarik garis keliling/siluet tomat.</li>
                            <li>**CNN Input** menormalisasi resolusi target menjadi 128x128 piksel untuk dicocokkan oleh filter CNN.</li>
                          </ul>
                        </div>
                      </div>

                      {/* CNN Activation Maps Card */}
                      <div className="bg-slate-800/20 border border-slate-700/30 backdrop-blur-md rounded-2xl p-6">
                        <h3 className="text-lg font-bold text-slate-200 mb-2 flex items-center gap-2">
                          <Layers size={18} className="text-amber-500" /> Visualisasi Aktivasi Filter CNN (Feature Maps)
                        </h3>
                        <p className="text-xs text-slate-500 mb-6 leading-relaxed">
                          Menampilkan visualisasi output lapisan konvolusi pertama (`conv_1`) model CNN. Lapisan ini memfilter detail tepi, kontur, warna, dan bercak busuk pada tomat.
                        </p>

                        {prediction.activation_maps && prediction.activation_maps.length > 0 ? (
                          <div className="grid grid-cols-4 gap-3">
                            {prediction.activation_maps.map((map, idx) => (
                              <div key={idx} className="bg-slate-950 border border-slate-850 p-2 rounded-lg flex flex-col items-center">
                                <div className="w-full aspect-square rounded overflow-hidden">
                                  <img src={`data:image/png;base64,${map}`} alt={`Filter ${idx+1}`} className="w-full h-full object-cover" />
                                </div>
                                <span className="text-[9px] font-mono text-slate-500 mt-1.5">Filter {idx+1}</span>
                              </div>
                            ))}
                          </div>
                        ) : (
                          <div className="text-xs text-slate-600 text-center py-6">
                            Gagal mengekstrak peta aktivasi filter model.
                          </div>
                        )}
                      </div>
                    </>
                  ) : (
                    <div className="h-96 flex flex-col items-center justify-center border-2 border-dashed border-slate-800 rounded-2xl text-slate-500">
                      <HelpCircle size={32} className="mb-2 text-slate-600" />
                      <span className="text-sm font-semibold">Menunggu Input Citra Tomat</span>
                      <span className="text-xs text-slate-600 mt-1">Silakan unggah gambar tomat atau pilih gambar acak dari kolom kiri.</span>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}
