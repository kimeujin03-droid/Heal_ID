

# 🏥 Heal ID: Emergency Patient Identification System based on FHIR & Face Recognition

> **🏆 ACK 2025 ETRI President's Award Winner (ETRI 원장상 수상작)** > **Capstone Design Project**

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![Flask](https://img.shields.io/badge/Flask-2.0-green.svg)
![OpenCV](https://img.shields.io/badge/OpenCV-Face_Recognition-red.svg)
![FHIR](https://img.shields.io/badge/Standard-HL7_FHIR-orange.svg)

## 📖 Overview
[cite_start]**Heal ID** is a non-contact patient identification system designed to secure the **Golden Time** in emergency situations[cite: 12, 24].
[cite_start]When an unconscious patient arrives, medical staff can identify the patient using facial recognition and immediately retrieve medical history (allergies, underlying conditions) from a **FHIR Standard Server**, ensuring safe and rapid treatment[cite: 50, 60].

## 🔑 Key Features

### 1. ⚡ Instant Identity Verification
- Utilizes **OpenCV LBPH (Local Binary Patterns Histograms)** algorithm for real-time face recognition.
- Capable of detecting and cropping faces from raw image data sent via API.

### 2. 🌐 FHIR Standard Interoperability
- Strictly follows **HL7 FHIR (Fast Healthcare Interoperability Resources)** standards for data exchange.
- **Bi-directional Sync:** - Checks local DB first; if not found, queries the FHIR server.
    - Registers new patients to the FHIR server with extended medical data (blood type, pregnancy, allergies).

### 3. 🛡️ Robust Error Handling
- **Data Normalization:** Automatically converts full-width numbers (e.g., １２３) to half-width for consistent ID processing.
- **Safe I/O:** Handles Korean file paths and image encoding/decoding safely.

## 🛠️ System Architecture

graph LR
    A["Emergency Scene\n(Camera/Tablet)"] -->|Face Image| B("Heal ID Server\nFlask + OpenCV")
    B -->|Identify ID| C{"Local DB"}
    C -->|If Exists| D["Return Patient Info"]
    C -->|If New| E["Request to FHIR Server"]
    E -->|JSON Data| B
💻 Tech Stack
Backend: Python, Flask

Computer Vision: OpenCV (CascadeClassifier, LBPHFaceRecognizer)

Database: MySQL

Protocol: REST API, HL7 FHIR

Hardware: Worked with Webcam/Tablet inputs

🚀 How to Run
Install Dependencies

Bash

pip install -r requirements.txt
Database Configuration Update your MySQL credentials in config.py:

Python

DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'YOUR_PASSWORD',
    'database': 'heal_id'
}
Run Server

Bash

python app.py
The server will start at http://0.0.0.0:5000.

👨‍💻 Project Members
So-yeon Kim

Su-bin Bae

Yu-jin Kim (Back-end & AI Development)

Yu-rim Lee

This project was developed for the Capstone Design course and demonstrated high reliability in non-contact identification scenarios.
