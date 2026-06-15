import os
import tensorflow as tf
from tensorflow.keras import layers, models
import matplotlib.pyplot as plt
import json

def main():
    print("Memulai proses pelatihan CNN...")
    
    # 1. Load dataset
    base_dir = "dataset"
    if not os.path.exists(base_dir) or len(os.listdir(base_dir)) == 0:
        print("Error: Folder dataset kosong atau tidak ditemukan. Jalankan generate_dataset.py terlebih dahulu!")
        return
        
    img_height, img_width = 128, 128
    batch_size = 16
    
    print("Membaca data dari direktori...")
    train_ds = tf.keras.utils.image_dataset_from_directory(
        base_dir,
        validation_split=0.2,
        subset="training",
        seed=123,
        image_size=(img_height, img_width),
        batch_size=batch_size
    )
    
    val_ds = tf.keras.utils.image_dataset_from_directory(
        base_dir,
        validation_split=0.2,
        subset="validation",
        seed=123,
        image_size=(img_height, img_width),
        batch_size=batch_size
    )
    
    class_names = train_ds.class_names
    print(f"Kategori yang ditemukan: {class_names}")
    
    # Simpan mapping kelas agar bisa dibaca oleh app.py
    class_mapping = {i: name for i, name in enumerate(class_names)}
    with open("class_mapping.json", "w") as f:
        json.dump(class_mapping, f)
    print("Mapping kelas berhasil disimpan ke class_mapping.json")
    
    model = models.Sequential([
        # Normalisasi piksel gambar ke rentang [0, 1]
        layers.Rescaling(1./255, input_shape=(img_height, img_width, 3)),
        
        # Augmentasi Data (hanya berjalan saat pelatihan/training)
        layers.RandomFlip("horizontal_and_vertical"),
        layers.RandomRotation(0.15),
        layers.RandomTranslation(0.1, 0.1),
        layers.RandomZoom(0.15),
        
        # Blok Konvolusi 1
        layers.Conv2D(16, (3, 3), padding='same', activation='relu', name='conv_1'),
        layers.MaxPooling2D((2, 2)),
        
        # Blok Konvolusi 2
        layers.Conv2D(32, (3, 3), padding='same', activation='relu', name='conv_2'),
        layers.MaxPooling2D((2, 2)),
        
        # Blok Konvolusi 3
        layers.Conv2D(64, (3, 3), padding='same', activation='relu', name='conv_3'),
        layers.MaxPooling2D((2, 2)),
        
        # Flattening dan Fully Connected Layers
        layers.Flatten(),
        layers.Dense(64, activation='relu'),
        layers.Dropout(0.2),
        layers.Dense(len(class_names), activation='softmax')
    ])
    
    # Compile Model
    model.compile(
        optimizer='adam',
        loss='sparse_categorical_crossentropy',
        metrics=['accuracy']
    )
    
    model.summary()
    
    # 3. Latih Model
    epochs = 10
    print(f"Melatih model selama {epochs} epoch...")
    history = model.fit(
        train_ds,
        validation_data=val_ds,
        epochs=epochs
    )
    
    # 4. Simpan Model
    model_path = "model_tomat.h5"
    model.save(model_path)
    print(f"Model berhasil disimpan ke: {model_path}")
    
    # 5. Visualisasi Hasil Pelatihan
    print("Membuat grafik evaluasi pelatihan...")
    acc = history.history['accuracy']
    val_acc = history.history['val_accuracy']
    loss = history.history['loss']
    val_loss = history.history['val_loss']
    
    epochs_range = range(epochs)
    
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
    print("Grafik pelatihan berhasil disimpan ke: training_history.png")
    print("Proses pelatihan selesai!")

if __name__ == "__main__":
    main()
