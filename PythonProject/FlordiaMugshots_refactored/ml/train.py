import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import numpy as np
import tensorflow as tf
from tensorflow.keras.preprocessing.image import ImageDataGenerator
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Conv2D, MaxPooling2D, Dense, Flatten, Dropout
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau
import matplotlib.pyplot as plt

from config import TRAINING_DIR, MODEL_PATH, IMG_SIZE, CLASS_NAMES


def prepare_data(folder_path, img_size=IMG_SIZE, batch_size=32):
    datagen = ImageDataGenerator(
        rescale=1. / 255,
        validation_split=0.2,
        width_shift_range=0.2,
        height_shift_range=0.2,
        horizontal_flip=True,
        fill_mode='nearest',
    )
    train_gen = datagen.flow_from_directory(
        folder_path, target_size=img_size, batch_size=batch_size,
        class_mode='categorical', subset='training', shuffle=True
    )
    val_gen = datagen.flow_from_directory(
        folder_path, target_size=img_size, batch_size=batch_size,
        class_mode='categorical', subset='validation', shuffle=True
    )
    return train_gen, val_gen


def build_model(input_shape=(*IMG_SIZE, 3), num_classes=len(CLASS_NAMES)):
    model = Sequential([
        Conv2D(32, (3, 3), activation='relu', input_shape=input_shape),
        MaxPooling2D(2, 2),
        Conv2D(64, (3, 3), activation='relu'),
        MaxPooling2D(2, 2),
        Conv2D(128, (3, 3), activation='relu'),
        MaxPooling2D(2, 2),
        Flatten(),
        Dense(512, activation='relu'),
        Dropout(0.5),
        Dense(num_classes, activation='softmax')
    ])
    model.compile(
        optimizer=Adam(learning_rate=0.0001),
        loss='categorical_crossentropy',
        metrics=['accuracy']
    )
    return model


def plot_training_history(history, output_path):
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4))
    ax1.plot(history.history['accuracy'], label='Training Accuracy')
    ax1.plot(history.history['val_accuracy'], label='Validation Accuracy')
    ax1.set_title('Model Accuracy')
    ax1.set_xlabel('Epoch')
    ax1.set_ylabel('Accuracy')
    ax1.legend()
    ax2.plot(history.history['loss'], label='Training Loss')
    ax2.plot(history.history['val_loss'], label='Validation Loss')
    ax2.set_title('Model Loss')
    ax2.set_xlabel('Epoch')
    ax2.set_ylabel('Loss')
    ax2.legend()
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()


def main():
    epochs = 25
    batch_size = 32
    history_path = os.path.join(os.path.dirname(MODEL_PATH), 'training_history.png')

    print("Preparing data...")
    train_gen, val_gen = prepare_data(TRAINING_DIR, batch_size=batch_size)

    print("Building model...")
    model = build_model()
    model.summary()

    callbacks = [
        EarlyStopping(monitor='val_loss', patience=5, restore_best_weights=True, verbose=1),
        ReduceLROnPlateau(monitor='val_loss', factor=0.5, patience=3, min_lr=1e-6, verbose=1),
    ]

    print("Training model...")
    history = model.fit(train_gen, epochs=epochs, validation_data=val_gen, callbacks=callbacks)

    model.save(MODEL_PATH)
    print(f"Model saved to {MODEL_PATH}")

    plot_training_history(history, history_path)
    print(f"Training history saved to {history_path}")

    train_loss, train_acc = model.evaluate(train_gen)
    val_loss, val_acc = model.evaluate(val_gen)
    print(f"Training accuracy: {train_acc:.4f}")
    print(f"Validation accuracy: {val_acc:.4f}")


if __name__ == "__main__":
    main()
