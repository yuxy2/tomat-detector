import streamlit as st
import os
import sys
import json
import random
import time
import subprocess
import numpy as np
from PIL import Image
import cv2
import matplotlib.pyplot as plt

# Set page config
st.set_page_config(
    page_title="Tomato Ripeness Detector - CNN",
    page_icon="🍅",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling (Dark Glassmorphism Theme)
st.markdown("""
<style>
    /* Main Background & Fonts */
    .stApp {
        background-color: #0f111a;
        color: #e2e8f0;
    }
    
    /* Header styling */
    .main-title {
        font-size: 2.8rem;
        font-weight: 800;
        background: linear-gradient(45deg, #ff4e50, #f9d423);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
        text-align: center;
    }
    .sub-title {
        font-size: 1.2rem;
        color: #94a3b8;
        margin-bottom: 2rem;
        text-align: center;
    }
    
    /* Card design */
    .custom-card {
        background: rgba(30, 41, 59, 0.45);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        backdrop-filter: blur(8px);
    }
    
    /* Status Badges */
    .badge {
        padding: 6px 12px;
        border-radius: 20px;
        font-weight: bold;
        font-size: 0.85rem;
        display: inline-block;
        text-align: center;
    }
    .badge-matang {
        background-color: rgba(220, 38, 38, 0.2);
        color: #f87171;
        border: 1px solid rgba(220, 38, 38, 0.4);
    }
    .badge-busuk {
        background-color: rgba(139, 92, 26, 0.2);
        color: #d97706;
        border: 1px solid rgba(139, 92, 26, 0.4);
    }
    .badge-mentah {
        background-color: rgba(16, 185, 129, 0.2);
        color: #34d399;
        border: 1px solid rgba(16, 185, 129, 0.4);
    }
    
    /* Center align block */
    .center-text {
        text-align: center;
    }
    
    /* Metric Card */
    .metric-value {
        font-size: 2rem;
        font-weight: 700;
        color: #f8fafc;
    }
</style>
""", unsafe_allow_html=True)

# Helper function to load TensorFlow only when needed to speed up initial app load
@st.cache_resource
def load_tf_and_model():
    try:
        import tensorflow as tf
        model_path = "model_tomat.h5"
        if os.path.exists(model_path):
            model = tf.keras.models.load_model(model_path)
            return tf, model, None
        return tf, None, "Model file 'model_tomat.h5' belum ditemukan. Silakan latih model terlebih dahulu!"
    except Exception as e:
        return None, None, f"Gagal memuat TensorFlow / Model: {str(e)}"

# Load class mapping
def get_class_labels():
    if os.path.exists("class_mapping.json"):
        with open("class_mapping.json", "r") as f:
            mapping = json.load(f)
            # return classes sorted by their index keys
            return [mapping[str(i)] for i in range(len(mapping))]
    return ["busuk", "matang", "mentah"] # alphabet default

# Main layout
st.markdown("<h1 class='main-title'>🍅 Deteksi Kematangan Tomat menggunakan CNN</h1>", unsafe_allow_html=True)
st.markdown("<p class='sub-title'>Studi Kasus Grafika Komputer & Pengolahan Citra Digital</p>", unsafe_allow_html=True)

# Check datasets status
base_dataset_dir = "dataset"
categories = ["mentah", "busuk", "matang"]
dataset_stats = {}
dataset_exists = True

for cat in categories:
    cat_path = os.path.join(base_dataset_dir, cat)
    if os.path.exists(cat_path):
        dataset_stats[cat] = len([f for f in os.listdir(cat_path) if f.lower().endswith(('.jpg', '.png', '.jpeg'))])
    else:
        dataset_stats[cat] = 0
        dataset_exists = False

total_images = sum(dataset_stats.values())

# Sidebar
st.sidebar.markdown("### 📊 Status Sistem")
st.sidebar.markdown(f"**Python Version:** {sys.version.split()[0]}")

# Model Status check
model_path = "model_tomat.h5"
if os.path.exists(model_path):
    st.sidebar.success("🤖 Model CNN: TERSEDIA")
else:
    st.sidebar.warning("🤖 Model CNN: BELUM TERSEDIA")

# Dataset Status check
if total_images > 0:
    st.sidebar.success(f"📁 Dataset: {total_images} Citra")
    for cat, count in dataset_stats.items():
        st.sidebar.markdown(f"- **{cat.replace('_', ' ').capitalize()}:** {count} gambar")
else:
    st.sidebar.error("📁 Dataset: KOSONG")

# Create Streamlit Tabs
tab1, tab2, tab3, tab4 = st.tabs([
    "🏠 Dashboard & Teori", 
    "📁 Dataset Generator", 
    "⚙️ Pelatihan Model", 
    "🔍 Deteksi & Analisis Citra"
])

# ==================== TAB 1: DASHBOARD & TEORI ====================
with tab1:
    st.markdown("<div class='custom-card'>", unsafe_allow_html=True)
    st.markdown("### 📝 Pendahuluan")
    st.write("""
    Dalam bidang **Grafika Komputer** dan **Pengolahan Citra Digital**, warna dan bentuk gambar diwakili sebagai matriks nilai numerik (pixel). Proyek studi kasus ini menggabungkan pemrosesan citra digital klasik dengan metode modern **Convolutional Neural Networks (CNN)** untuk mendeteksi kematangan buah tomat secara otomatis.
    
    Tingkat kematangan dan kondisi tomat dibagi menjadi 3 kategori utama:
    - **Mentah**: Tomat berwarna dominan hijau (kandungan klorofil tinggi).
    - **Matang**: Tomat berwarna merah pekat (kandungan likopen maksimal).
    - **Busuk**: Tomat yang mengalami pembusukan ditandai dengan bercak cokelat/hitam, tekstur lembek, dan permukaan kusam.
    """)
    st.markdown("</div>", unsafe_allow_html=True)
    
    st.markdown("<div class='custom-card'>", unsafe_allow_html=True)
    st.markdown("### 🧬 Bagaimana CNN Bekerja (Aspek Grafika Komputer)")
    st.write("""
    CNN bekerja dengan menerapkan filter konvolusi spasial (kernel) secara berlapis pada matriks citra input:
    1. **Lapisan Konvolusi (Convolutional Layer)**: Menerapkan kernel filter (seperti filter Sobel untuk deteksi tepi atau deteksi warna) untuk mengekstrak fitur visual seperti garis, tekstur, dan gradasi warna.
    2. **Lapisan Pooling (Pooling Layer)**: Mengurangi dimensi spasial gambar (downsampling) untuk mempertahankan fitur terpenting dan menghemat komputasi.
    3. **Lapisan Flattening & Fully Connected**: Mengubah matriks 2D fitur menjadi vektor 1D dan mengklasifikasikannya ke dalam kelas target (Mentah, Busuk, Matang) menggunakan fungsi probabilitas Softmax.
    """)
    
    # Simple diagram using markdown
    st.code("""
    [Input Image 128x128x3] -> [Conv2D: 16 filters] -> [Max Pooling] -> [Conv2D: 32 filters] -> [Max Pooling] -> [Flatten] -> [Dense: 64] -> [Output Softmax: 3 Classes]
    """, language="text")
    st.markdown("</div>", unsafe_allow_html=True)

# ==================== TAB 2: DATASET GENERATOR ====================
with tab2:
    st.markdown("### 📁 Generator Dataset Tomat Sintetis")
    st.write("""
    Karena tidak ada dataset tomat fisik bawaan, tab ini memungkinkan Anda membuat dataset buatan (sintetis) menggunakan pustaka pengolah gambar Python (`Pillow` dan `NumPy`). 
    Setiap gambar tomat dibuat dengan merender lingkaran 3D (gradasi bayangan), kilauan cahaya (specular reflection), tangkai daun acak, dan noise sensor kamera.
    """)
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.markdown("<div class='custom-card'>", unsafe_allow_html=True)
        st.markdown("#### Pengaturan Generator")
        num_gen = st.slider("Jumlah gambar per kategori", min_value=10, max_value=200, value=100, step=10)
        
        btn_generate = st.button("🚀 Generate Dataset Baru", use_container_width=True)
        if btn_generate:
            with st.spinner("Sedang memproses pembuatan citra tomat buatan..."):
                try:
                    # Run generate_dataset.py using subprocess or directly import
                    import generate_dataset
                    generate_dataset.main(num_images=num_gen)
                    st.success(f"Berhasil membuat {num_gen * 3} gambar tomat sintetis!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Gagal men-generate dataset: {str(e)}")
        st.markdown("</div>", unsafe_allow_html=True)
        
    with col2:
        st.markdown("<div class='custom-card'>", unsafe_allow_html=True)
        st.markdown("#### Preview Sampel Dataset")
        
        if total_images > 0:
            sub_col1, sub_col2, sub_col3 = st.columns(3)
            
            # Show random Mentah
            with sub_col1:
                st.markdown("<div class='center-text'><span class='badge badge-mentah'>MENTAH</span></div>", unsafe_allow_html=True)
                mentah_dir = os.path.join(base_dataset_dir, "mentah")
                m_imgs = [f for f in os.listdir(mentah_dir) if f.lower().endswith('.jpg')]
                if m_imgs:
                    m_img = Image.open(os.path.join(mentah_dir, random.choice(m_imgs)))
                    st.image(m_img, use_container_width=True)
                    
            # Show random Busuk
            with sub_col2:
                st.markdown("<div class='center-text'><span class='badge badge-busuk'>BUSUK</span></div>", unsafe_allow_html=True)
                busuk_dir = os.path.join(base_dataset_dir, "busuk")
                s_imgs = [f for f in os.listdir(busuk_dir) if f.lower().endswith('.jpg')]
                if s_imgs:
                    s_img = Image.open(os.path.join(busuk_dir, random.choice(s_imgs)))
                    st.image(s_img, use_container_width=True)
                    
            # Show random Matang
            with sub_col3:
                st.markdown("<div class='center-text'><span class='badge badge-matang'>MATANG</span></div>", unsafe_allow_html=True)
                matang_dir = os.path.join(base_dataset_dir, "matang")
                r_imgs = [f for f in os.listdir(matang_dir) if f.lower().endswith('.jpg')]
                if r_imgs:
                    r_img = Image.open(os.path.join(matang_dir, random.choice(r_imgs)))
                    st.image(r_img, use_container_width=True)
        else:
            st.warning("Dataset belum di-generate. Klik tombol 'Generate Dataset Baru' untuk memulai!")
        st.markdown("</div>", unsafe_allow_html=True)

# ==================== TAB 3: PELATIHAN MODEL ====================
with tab3:
    st.markdown("### ⚙️ Pelatihan Model CNN")
    st.write("""
    Gunakan tab ini untuk melatih model Convolutional Neural Network secara langsung. Proses ini akan membaca gambar di folder `dataset/`, melatih arsitektur model, dan menyimpan hasilnya menjadi `model_tomat.h5`.
    """)
    
    col_t1, col_t2 = st.columns([1, 2])
    
    with col_t1:
        st.markdown("<div class='custom-card'>", unsafe_allow_html=True)
        st.markdown("#### Kontrol Pelatihan")
        
        if total_images == 0:
            st.error("Dataset kosong! Silakan generate dataset terlebih dahulu di Tab 'Dataset Generator'.")
        else:
            btn_train = st.button("🏋️ Mulai Pelatihan Model", use_container_width=True)
            if btn_train:
                status_box = st.empty()
                log_box = st.empty()
                
                status_box.info("Sedang melatih model CNN. Proses ini memakan waktu sekitar 15-30 detik...")
                
                # We can run train.py using subprocess and print the logs live
                # Using the python executable from the virtual environment
                python_exec = os.path.join(".venv", "Scripts", "python")
                if not os.path.exists(python_exec):
                    python_exec = "python" # fallback
                    
                process = subprocess.Popen(
                    [python_exec, "train.py"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    shell=True
                )
                
                log_output = ""
                while True:
                    line = process.stdout.readline()
                    if not line:
                        break
                    log_output += line
                    log_box.code(log_output, language="text")
                    
                process.wait()
                if process.returncode == 0:
                    status_box.success("Pelatihan selesai! Model berhasil disimpan ke 'model_tomat.h5'.")
                    st.rerun()
                else:
                    status_box.error(f"Terjadi kesalahan saat melatih model! Kode keluar: {process.returncode}")
        st.markdown("</div>", unsafe_allow_html=True)
        
    with col_t2:
        st.markdown("<div class='custom-card'>", unsafe_allow_html=True)
        st.markdown("#### Hasil Pelatihan")
        
        if os.path.exists("training_history.png"):
            st.image("training_history.png", caption="Kurva Akurasi dan Loss Hasil Pelatihan Terakhir", use_container_width=True)
        else:
            st.info("Belum ada riwayat pelatihan. Jalankan pelatihan model untuk melihat grafik hasil.")
        st.markdown("</div>", unsafe_allow_html=True)

# ==================== TAB 4: DETEKSI & ANALISIS CITRA ====================
with tab4:
    st.markdown("### 🔍 Pengujian Deteksi Kematangan Tomat")
    
    # Load model and tensorflow
    tf, model, model_err = load_tf_and_model()
    
    if model_err:
        st.warning(model_err)
    else:
        st.write("Unggah gambar tomat Anda sendiri atau pilih salah satu gambar uji dari dataset untuk melihat visualisasi pengolahan citra dan prediksi CNN.")
        
        col_d1, col_d2 = st.columns([1, 2])
        
        selected_img = None
        
        with col_d1:
            st.markdown("<div class='custom-card'>", unsafe_allow_html=True)
            st.markdown("#### 📤 Input Citra")
            
            source_option = st.radio("Pilih sumber gambar:", ["Unggah File (Upload)", "Gunakan Gambar dari Dataset"])
            
            if source_option == "Unggah File (Upload)":
                uploaded_file = st.file_uploader("Pilih file citra tomat...", type=["jpg", "jpeg", "png"])
                if uploaded_file is not None:
                    selected_img = Image.open(uploaded_file).convert("RGB")
                    
            else: # Use dataset image
                if total_images > 0:
                    # Pick a random category and random image
                    if 'random_test_img' not in st.session_state or st.button("🔄 Pilih Gambar Acak Baru"):
                        random_cat = random.choice(categories)
                        cat_dir = os.path.join(base_dataset_dir, random_cat)
                        all_imgs = [f for f in os.listdir(cat_dir) if f.lower().endswith(('.jpg', '.png'))]
                        if all_imgs:
                            chosen_file = random.choice(all_imgs)
                            st.session_state.random_test_img = os.path.join(cat_dir, chosen_file)
                            st.session_state.random_test_cat = random_cat
                            
                    if 'random_test_img' in st.session_state and os.path.exists(st.session_state.random_test_img):
                        st.markdown(f"Gambar terpilih dari folder: **dataset/{st.session_state.random_test_cat}**")
                        selected_img = Image.open(st.session_state.random_test_img).convert("RGB")
                else:
                    st.warning("Dataset kosong! Silakan buat dataset terlebih dahulu.")
            
            if selected_img is not None:
                st.image(selected_img, caption="Citra Input", use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)
            
        with col_d2:
            if selected_img is not None:
                st.markdown("<div class='custom-card'>", unsafe_allow_html=True)
                st.markdown("#### 🎯 Hasil Klasifikasi Model CNN")
                
                # Preprocess for model prediction
                img_resized = selected_img.resize((128, 128))
                img_array = np.array(img_resized)
                # Expand dimensions to create batch: (1, 128, 128, 3)
                img_batch = np.expand_dims(img_array, axis=0)
                
                # Make prediction
                with st.spinner("Model sedang menganalisis gambar..."):
                    preds = model.predict(img_batch)[0]
                    
                class_labels = get_class_labels()
                pred_class_idx = np.argmax(preds)
                pred_class_label = class_labels[pred_class_idx]
                confidence = preds[pred_class_idx] * 100
                
                # Display Badge based on category
                badge_html = ""
                if pred_class_label == "matang":
                    badge_html = "<span class='badge badge-matang'>MATANG</span>"
                elif pred_class_label == "busuk":
                    badge_html = "<span class='badge badge-busuk'>BUSUK</span>"
                else:
                    badge_html = "<span class='badge badge-mentah'>MENTAH</span>"
                    
                c_col1, c_col2 = st.columns(2)
                with c_col1:
                    st.write(f"Kelas Terprediksi:")
                    st.markdown(f"<h3>{badge_html}</h3>", unsafe_allow_html=True)
                with c_col2:
                    st.write(f"Tingkat Keyakinan:")
                    st.markdown(f"<p class='metric-value'>{confidence:.2f}%</p>", unsafe_allow_html=True)
                
                # Progress bars for each class
                st.markdown("##### Distribusi Probabilitas Kelas:")
                for i, label in enumerate(class_labels):
                    label_clean = label.replace('_', ' ').capitalize()
                    st.write(f"**{label_clean}** ({preds[i]*100:.2f}%)")
                    st.progress(float(preds[i]))
                    
                st.markdown("</div>", unsafe_allow_html=True)
                
                # --- Preprocessing Visualization (Computer Graphics aspect) ---
                st.markdown("<div class='custom-card'>", unsafe_allow_html=True)
                st.markdown("#### 🎨 Tahapan Pengolahan Citra Digital (Grafika Komputer)")
                
                img_np = np.array(selected_img)
                
                # 1. Grayscale
                gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
                
                # 2. HSV Channel Visualization (Hue & Saturation are key in color segmentation)
                hsv = cv2.cvtColor(img_np, cv2.COLOR_RGB2HSV)
                h_channel = hsv[:, :, 0]
                s_channel = hsv[:, :, 1]
                
                # 3. Edge Detection (Canny)
                edges = cv2.Canny(gray, 50, 150)
                
                col_cg1, col_cg2, col_cg3, col_cg4 = st.columns(4)
                with col_cg1:
                    st.image(gray, caption="1. Grayscale (Luminositas)", use_container_width=True)
                with col_cg2:
                    st.image(h_channel, caption="2. Hue Channel (Warna)", use_container_width=True)
                with col_cg3:
                    st.image(edges, caption="3. Canny Edge (Kontur)", use_container_width=True)
                with col_cg4:
                    st.image(img_resized, caption="4. CNN Input (128x128)", use_container_width=True)
                    
                st.write("""
                *Keterangan Proses:*
                1. **Grayscale** memisahkan intensitas cahaya (luminositas) dari warna.
                2. **Hue Channel (HSV)** memetakan spektrum warna murni tomat (warna hijau, kuning/orange, dan merah berada di range hue yang berbeda).
                3. **Canny Edge Detection** mendeteksi perubahan kontras tajam untuk mengisolasi batas keliling (siluet) tomat.
                4. **CNN Input** merupakan resolusi target normalisasi 128x128 piksel yang dibaca oleh filter neural network.
                """)
                st.markdown("</div>", unsafe_allow_html=True)
                
                # --- CNN Activation Map Visualization ---
                st.markdown("<div class='custom-card'>", unsafe_allow_html=True)
                st.markdown("#### 🔬 Visualisasi Aktivasi Filter CNN (Feature Maps)")
                st.write("Bagaimana lapisan konvolusi pertama (`conv_1`) melihat gambar tomat Anda. Filter konvolusi menyaring detail warna, tepi, dan kilauan cahaya:")
                
                try:
                    # Extract activation output from the first Conv2D layer
                    conv1_layer = model.get_layer('conv_1')
                    from tensorflow.keras.models import Model
                    activation_model = Model(inputs=model.inputs, outputs=conv1_layer.output)
                    
                    # Normalize image array for prediction input
                    # Note: model contains Rescaling(1./255) layer internally as layers[0]
                    # We pass the raw [0, 255] batch directly since input_shape handles rescaling inside the model
                    activations = activation_model.predict(img_batch)[0]
                    
                    # Number of filters in conv_1 is 16. Let's display first 8.
                    num_filters_to_show = 8
                    fig, axes = plt.subplots(2, 4, figsize=(10, 5))
                    fig.patch.set_facecolor('#0f111a') # Match theme
                    
                    for idx in range(num_filters_to_show):
                        ax = axes[idx // 4, idx % 4]
                        f_map = activations[:, :, idx]
                        
                        # Normalize filter map to [0, 1] for visualization
                        f_min, f_max = f_map.min(), f_map.max()
                        if f_max > f_min:
                            f_map = (f_map - f_min) / (f_max - f_min)
                        
                        ax.imshow(f_map, cmap='viridis')
                        ax.axis('off')
                        ax.set_title(f"Filter {idx+1}", color='#e2e8f0', fontsize=10)
                        
                    plt.tight_layout()
                    st.pyplot(fig)
                    
                except Exception as e:
                    st.error(f"Gagal memvisualisasikan fitur aktivasi: {str(e)}")
                
                st.markdown("</div>", unsafe_allow_html=True)
            else:
                st.info("Pilih gambar dari dataset atau unggah file Anda sendiri pada kolom sebelah kiri.")
