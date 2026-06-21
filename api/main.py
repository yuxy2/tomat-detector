import os
import io
import json
import base64
import random
import numpy as np
from PIL import Image
import cv2
from fastapi import FastAPI, UploadFile, File, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="Tomato CNN API")

# Enable CORS for Next.js frontend
allowed_origins_str = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")
allowed_origins = [origin.strip() for origin in allowed_origins_str.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables for model and state
model = None
class_labels = ["busuk", "matang", "mentah"]
training_state = {
    "status": "idle", # idle, training, completed, failed
    "epoch": 0,
    "total_epochs": 10,
    "logs": "",
    "history": None
}

# Load model and class mapping on startup
def load_model_at_startup():
    global model, class_labels
    import tensorflow as tf
    
    model_path = "model_tomat.h5"
    if os.path.exists(model_path):
        try:
            model = tf.keras.models.load_model(model_path)
            print("Model CNN loaded successfully!")
        except Exception as e:
            print(f"Error loading model: {str(e)}")
            
    if os.path.exists("class_mapping.json"):
        try:
            with open("class_mapping.json", "r") as f:
                mapping = json.load(f)
                class_labels = [mapping[str(i)] for i in range(len(mapping))]
            print(f"Class labels loaded: {class_labels}")
        except Exception as e:
            print(f"Error loading class mapping: {str(e)}")

# Run model loading
try:
    load_model_at_startup()
except Exception as e:
    print(f"TensorFlow not loaded: {str(e)}")

def to_base64_png(img_np):
    """Convert numpy array image to base64 PNG string."""
    # Convert RGB to BGR for OpenCV encoding
    if len(img_np.shape) == 3 and img_np.shape[2] == 3:
        img_bgr = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
    else:
        img_bgr = img_np
    _, buffer = cv2.imencode('.png', img_bgr)
    return base64.b64encode(buffer).decode('utf-8')

class GenerateDatasetRequest(BaseModel):
    num_images: int = 100

@app.get("/api/stats")
def get_stats():
    base_dir = "dataset"
    categories = ["mentah", "busuk", "matang"]
    stats = {}
    
    for cat in categories:
        cat_path = os.path.join(base_dir, cat)
        if os.path.exists(cat_path):
            stats[cat] = len([f for f in os.listdir(cat_path) if f.lower().endswith(('.jpg', '.png', '.jpeg'))])
        else:
            stats[cat] = 0
            
    return {
        "model_available": model is not None,
        "dataset_stats": stats,
        "total_images": sum(stats.values()),
        "class_labels": class_labels
    }

@app.post("/api/predict")
async def predict(file: UploadFile = File(...)):
    global model, class_labels
    if model is None:
        # Try loading model again just in case
        load_model_at_startup()
        if model is None:
            raise HTTPException(status_code=400, detail="Model CNN belum tersedia. Harap latih model terlebih dahulu.")
            
    try:
        contents = await file.read()
        image = Image.open(io.BytesIO(contents)).convert("RGB")
        img_np = np.array(image)
        
        # 1. Image Pre-processing for CG aspect
        gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
        hsv = cv2.cvtColor(img_np, cv2.COLOR_RGB2HSV)
        h_channel = hsv[:, :, 0]
        edges = cv2.Canny(gray, 50, 150)
        
        # Resize for CNN input
        img_resized = image.resize((128, 128))
        img_resized_np = np.array(img_resized)
        
        # 2. Run CNN Inference
        img_batch = np.expand_dims(img_resized_np, axis=0) # shape (1, 128, 128, 3)
        preds = model.predict(img_batch)[0]
        
        pred_idx = np.argmax(preds)
        pred_label = class_labels[pred_idx]
        confidence = float(preds[pred_idx])
        
        # 3. Extract CNN Activation Maps
        activation_maps = []
        try:
            import tensorflow as tf
            from tensorflow.keras.models import Model
            conv1_layer = model.get_layer('conv_1')
            activation_model = Model(inputs=model.inputs, outputs=conv1_layer.output)
            activations = activation_model.predict(img_batch)[0] # shape (128, 128, 16)
            
            # Extract first 8 filters
            for idx in range(8):
                f_map = activations[:, :, idx]
                f_min, f_max = f_map.min(), f_map.max()
                if f_max > f_min:
                    f_map = (f_map - f_min) / (f_max - f_min)
                f_map = (f_map * 255).astype(np.uint8)
                
                # Apply viridis colormap
                f_map_colored = cv2.applyColorMap(f_map, cv2.COLORMAP_VIRIDIS)
                activation_maps.append(to_base64_png(f_map_colored))
        except Exception as e:
            print(f"Error generating activation maps: {str(e)}")
            
        # Compile response
        predictions_dict = {class_labels[i]: float(preds[i]) for i in range(len(class_labels))}
        
        return {
            "predicted_class": pred_label,
            "confidence": confidence,
            "predictions": predictions_dict,
            "images": {
                "original": to_base64_png(img_np),
                "grayscale": to_base64_png(gray),
                "hsv_hue": to_base64_png(h_channel),
                "canny_edges": to_base64_png(edges),
                "resized": to_base64_png(img_resized_np)
            },
            "activation_maps": activation_maps
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal memproses gambar: {str(e)}")

@app.post("/api/generate-dataset")
def generate_dataset(payload: GenerateDatasetRequest, background_tasks: BackgroundTasks):
    # Run dataset generator in background task
    import generate_dataset
    
    def run_generator():
        try:
            generate_dataset.main(num_images=payload.num_images)
        except Exception as e:
            print(f"Dataset generation failed: {str(e)}")
            
    background_tasks.add_task(run_generator)
    return {"status": "started", "message": f"Pembuatan dataset ({payload.num_images} gambar/kategori) dimulai di background."}

# Background training runner
def run_model_training():
    global training_state, model, class_labels
    import tensorflow as tf
    from tensorflow.keras import layers, models
    
    training_state["status"] = "training"
    training_state["epoch"] = 0
    training_state["logs"] = "Memulai proses pelatihan CNN...\n"
    
    base_dir = "dataset"
    if not os.path.exists(base_dir) or len(os.listdir(base_dir)) == 0:
        training_state["status"] = "failed"
        training_state["logs"] += "Error: Folder dataset kosong atau tidak ditemukan.\n"
        return
        
    try:
        img_height, img_width = 128, 128
        batch_size = 16
        
        training_state["logs"] += "Membaca data dari direktori...\n"
        train_ds = tf.keras.utils.image_dataset_from_directory(
            base_dir,
            validation_split=0.2,
            subset="training",
            seed=123,
            image_size=(img_height, img_width),
            batch_size=batch_size,
            verbose=False
        )
        
        val_ds = tf.keras.utils.image_dataset_from_directory(
            base_dir,
            validation_split=0.2,
            subset="validation",
            seed=123,
            image_size=(img_height, img_width),
            batch_size=batch_size,
            verbose=False
        )
        
        current_class_names = train_ds.class_names
        training_state["logs"] += f"Kategori yang ditemukan: {current_class_names}\n"
        
        # Save mapping
        class_mapping = {i: name for i, name in enumerate(current_class_names)}
        with open("class_mapping.json", "w") as f:
            json.dump(class_mapping, f)
            
        model = models.Sequential([
            layers.Rescaling(1./255, input_shape=(img_height, img_width, 3)),
            # Augmentasi Data (hanya berjalan saat pelatihan/training)
            layers.RandomFlip("horizontal_and_vertical"),
            layers.RandomRotation(0.15),
            layers.RandomTranslation(0.1, 0.1),
            layers.RandomZoom(0.15),
            
            layers.Conv2D(16, (3, 3), padding='same', activation='relu', name='conv_1'),
            layers.MaxPooling2D((2, 2)),
            layers.Conv2D(32, (3, 3), padding='same', activation='relu', name='conv_2'),
            layers.MaxPooling2D((2, 2)),
            layers.Conv2D(64, (3, 3), padding='same', activation='relu', name='conv_3'),
            layers.MaxPooling2D((2, 2)),
            layers.Flatten(),
            layers.Dense(64, activation='relu'),
            layers.Dropout(0.2),
            layers.Dense(len(current_class_names), activation='softmax')
        ])
        
        model.compile(
            optimizer='adam',
            loss='sparse_categorical_crossentropy',
            metrics=['accuracy']
        )
        
        # Custom Callback for training progress
        class NextJSCallback(tf.keras.callbacks.Callback):
            def on_epoch_begin(self, epoch, logs=None):
                global training_state
                training_state["epoch"] = epoch + 1
                training_state["logs"] += f"Memulai Epoch {epoch+1}/10...\n"
                
            def on_epoch_end(self, epoch, logs=None):
                global training_state
                acc = logs.get('accuracy', 0)
                val_acc = logs.get('val_accuracy', 0)
                loss = logs.get('loss', 0)
                val_loss = logs.get('val_loss', 0)
                training_state["logs"] += f"Selesai Epoch {epoch+1}/10 - Akurasi: {acc:.4f} (Val Akurasi: {val_acc:.4f}) - Loss: {loss:.4f}\n"
                
        # Fit model
        history = model.fit(
            train_ds,
            validation_data=val_ds,
            epochs=10,
            callbacks=[NextJSCallback()],
            verbose=0
        )
        
        # Save model
        model.save("model_tomat.h5")
        training_state["status"] = "completed"
        training_state["logs"] += "Model berhasil disimpan ke: model_tomat.h5\n"
        training_state["logs"] += "Proses pelatihan selesai dengan sukses!\n"
        
        # Save training history curves
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        
        acc = history.history['accuracy']
        val_acc = history.history['val_accuracy']
        loss = history.history['loss']
        val_loss = history.history['val_loss']
        epochs_range = range(10)
        
        plt.figure(figsize=(12, 5))
        plt.subplot(1, 2, 1)
        plt.plot(epochs_range, acc, label='Training Accuracy', color='#1f77b4', linewidth=2)
        plt.plot(epochs_range, val_acc, label='Validation Accuracy', color='#ff7f0e', linewidth=2)
        plt.legend(loc='lower right')
        plt.title('Akurasi Model')
        plt.grid(True, linestyle='--', alpha=0.6)
        
        plt.subplot(1, 2, 2)
        plt.plot(epochs_range, loss, label='Training Loss', color='#d62728', linewidth=2)
        plt.plot(epochs_range, val_loss, label='Validation Loss', color='#2ca02c', linewidth=2)
        plt.legend(loc='upper right')
        plt.title('Loss Model')
        plt.grid(True, linestyle='--', alpha=0.6)
        
        plt.tight_layout()
        plt.savefig('training_history.png', dpi=150)
        plt.close()
        
        # Reload global configs
        load_model_at_startup()
        
    except Exception as e:
        training_state["status"] = "failed"
        training_state["logs"] += f"Terjadi kesalahan saat pelatihan: {str(e)}\n"

@app.post("/api/train-model")
def train_model(background_tasks: BackgroundTasks):
    global training_state
    if training_state["status"] == "training":
        return {"status": "running", "message": "Pelatihan model sedang berjalan."}
        
    background_tasks.add_task(run_model_training)
    return {"status": "started", "message": "Proses pelatihan model dimulai di background."}

@app.get("/api/train-status")
def get_train_status():
    global training_state
    return training_state

@app.get("/api/random-test")
def get_random_test_image():
    base_dir = "dataset"
    categories = ["mentah", "busuk", "matang"]
    
    # Pick a random non-empty category
    available_cats = []
    for cat in categories:
        cat_path = os.path.join(base_dir, cat)
        if os.path.exists(cat_path) and len([f for f in os.listdir(cat_path) if f.lower().endswith(('.jpg', '.png'))]) > 0:
            available_cats.append(cat)
            
    if not available_cats:
        raise HTTPException(status_code=400, detail="Dataset kosong. Harap generate dataset terlebih dahulu.")
        
    random_cat = random.choice(available_cats)
    cat_dir = os.path.join(base_dir, random_cat)
    all_imgs = [f for f in os.listdir(cat_dir) if f.lower().endswith(('.jpg', '.png'))]
    random_img_name = random.choice(all_imgs)
    img_path = os.path.join(cat_dir, random_img_name)
    
    try:
        image = Image.open(img_path)
        img_np = np.array(image)
        return {
            "image_base64": to_base64_png(img_np),
            "real_class": random_cat,
            "filename": random_img_name
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal membaca gambar: {str(e)}")
