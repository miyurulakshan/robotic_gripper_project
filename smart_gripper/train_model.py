# filename: train_model.py
import matplotlib.pyplot as plt
import numpy as np
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers
from tensorflow.keras.models import Sequential
import pathlib

# --- CONFIGURATION ---
DATASET_PATH = "dataset"
IMG_HEIGHT = 224
IMG_WIDTH = 224
BATCH_SIZE = 32
EPOCHS = 15

# --- 1. LOAD THE DATASET ---
data_dir = pathlib.Path(DATASET_PATH)
image_count = len(list(data_dir.glob('*/*.jpg')))
print(f"Found {image_count} images.")

# Create a training dataset (80%)
train_ds = tf.keras.utils.image_dataset_from_directory(
  data_dir,
  validation_split=0.2,
  subset="training",
  seed=123,
  image_size=(IMG_HEIGHT, IMG_WIDTH),
  batch_size=BATCH_SIZE)

# Create a validation dataset (20%)
val_ds = tf.keras.utils.image_dataset_from_directory(
  data_dir,
  validation_split=0.2,
  subset="validation",
  seed=123,
  image_size=(IMG_HEIGHT, IMG_WIDTH),
  batch_size=BATCH_SIZE)

CLASS_NAMES = train_ds.class_names
print("Class Names Found:", CLASS_NAMES)

AUTOTUNE = tf.data.AUTOTUNE
train_ds = train_ds.cache().shuffle(1000).prefetch(buffer_size=AUTOTUNE)
val_ds = val_ds.cache().prefetch(buffer_size=AUTOTUNE)

# --- 2. CREATE THE MODEL ---
num_classes = len(CLASS_NAMES)
data_augmentation = keras.Sequential([
  layers.RandomFlip("horizontal", input_shape=(IMG_HEIGHT, IMG_WIDTH, 3)),
  layers.RandomRotation(0.1),
  layers.RandomZoom(0.1),
])

base_model = tf.keras.applications.MobileNetV2(
    input_shape=(IMG_HEIGHT, IMG_WIDTH, 3),
    include_top=False,
    weights='imagenet'
)
base_model.trainable = False

model = Sequential([
  data_augmentation,
  tf.keras.layers.Rescaling(1./255),
  base_model,
  layers.GlobalAveragePooling2D(),
  layers.Dropout(0.2),
  layers.Dense(num_classes)
])

# --- 3. COMPILE THE MODEL ---
model.compile(optimizer='adam',
              loss=tf.keras.losses.SparseCategoricalCrossentropy(from_logits=True),
              metrics=['accuracy'])
model.summary()

# --- 4. TRAIN THE MODEL ---
print("\n--- STARTING TRAINING ---")
history = model.fit(
  train_ds,
  validation_data=val_ds,
  epochs=EPOCHS
)
print("--- TRAINING COMPLETE ---\n")

# --- 5. SAVE THE MODEL ---
model.save('my_object_model.h5')
print("Model saved as my_object_model.h5")

# --- 6. VISUALIZE RESULTS ---
acc = history.history['accuracy']
val_acc = history.history['validation_accuracy']
loss = history.history['loss']
val_loss = history.history['validation_loss']
epochs_range = range(EPOCHS)

plt.figure(figsize=(8, 8))
plt.subplot(1, 2, 1)
plt.plot(epochs_range, acc, label='Training Accuracy')
plt.plot(epochs_range, val_acc, label='Validation Accuracy')
plt.legend(loc='lower right')
plt.title('Training and Validation Accuracy')

plt.subplot(1, 2, 2)
plt.plot(epochs_range, loss, label='Training Loss')
plt.plot(epochs_range, val_loss, label='Validation Loss')
plt.legend(loc='upper right')
plt.title('Training and Validation Loss')
plt.show()