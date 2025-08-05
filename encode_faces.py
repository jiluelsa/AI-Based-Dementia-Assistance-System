import cv2
import face_recognition
import pickle
import os
import pandas as pd
from datetime import datetime

# Paths
KNOWN_FACES_DIR = "known_faces"
UNKNOWN_FACES_DIR = "unknown_faces"
ENCODINGS_FILE = "face_encodings.pkl"
CSV_FILE = "people_data.csv"

# Ensure directories exist
os.makedirs(UNKNOWN_FACES_DIR, exist_ok=True)

# Load known faces
if os.path.exists(ENCODINGS_FILE):
    with open(ENCODINGS_FILE, "rb") as f:
        data = pickle.load(f)
        known_encodings, known_names = data.get("encodings", []), data.get("names", [])
else:
    known_encodings, known_names = [], []

# Process known faces
for person_name in os.listdir(KNOWN_FACES_DIR):
    person_folder = os.path.join(KNOWN_FACES_DIR, person_name)
    if os.path.isdir(person_folder):
        for filename in os.listdir(person_folder):
            if filename.endswith(".jpg") or filename.endswith(".png"):
                image_path = os.path.join(person_folder, filename)
                image = face_recognition.load_image_file(image_path)
                encodings = face_recognition.face_encodings(image)

                if encodings:
                    encoding = encodings[0]
                    known_encodings.append(encoding)
                    known_names.append(person_name)

# Save encodings to file
with open(ENCODINGS_FILE, "wb") as f:
    pickle.dump({"encodings": known_encodings, "names": known_names}, f)

print("Encodings updated successfully!")
print(f"Total Encodings: {len(known_encodings)}")  # Debugging line
print(f"Names in Encodings: {set(known_names)}")  # Debugging line