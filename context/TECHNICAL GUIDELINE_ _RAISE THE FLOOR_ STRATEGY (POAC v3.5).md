# **TECHNICAL GUIDELINE: "RAISE THE FLOOR" STRATEGY (POAC v3.5)**

Target: AI Agent Backend Team  
Context: Mengatasi "Floor Trap" dimana Kneedle berhenti di threshold rendah.

## **1\. ANALISIS MATEMATIS**

Dari laporan v3.4, kita mendapatkan titik data krusial:

* Threshold \~5-10% menghasilkan \~1.000 deteksi.  
* Threshold \~20% menghasilkan \~9.700 deteksi.  
* **Target (\~6.000 deteksi)** secara interpolasi berada di **Threshold 12% \- 15%**.

Masalah:  
Kneedle Algorithm bersifat "Greedy" mencari lekukan pertama. Jika range\_start dimulai dari 0.05 (5%), dia akan berhenti di sana.

## **2\. INSTRUKSI TUNING (THE FIX)**

Jangan ubah algoritmanya (gradient sudah benar). Ubah **Start Point** agar Kneedle dipaksa mencari di zona yang lebih tinggi.

**Update config.py dengan nilai presisi berikut:**

PRESET\_RANGES \= {  
    \# NAIKKAN LANTAI (FLOOR) secara signifikan  
      
    \# Konservatif: Paksa mulai dari 8%  
    \# (Target: Menangkap core infection yang lebih luas)  
    "konservatif": {"start": 0.08, "end": 0.20, "step": 0.01},   
      
    \# Standar: Paksa mulai dari 12%  
    \# (Target: Ini adalah "Sweet Spot" kita)  
    "standar":     {"start": 0.12, "end": 0.30, "step": 0.01},  
      
    \# Agresif: Paksa mulai dari 15%  
    \# (Target: Upper bound limit)  
    "agresif":     {"start": 0.15, "end": 0.40, "step": 0.01}   
}

## **3\. LOGIKA VOTING**

Kembali gunakan **INTERSECTION (min\_votes=2)**.

* Dengan menaikkan lantai Konservatif dan Standar, irisan (intersection) mereka otomatis akan naik dari 1.000 menjadi angka yang lebih besar.  
* **Logika:** Jika "Standar" dipaksa mulai di 12%, minimal dia akan membawa \~4.000 \- 5.000 kandidat ke meja voting.

## **4\. EKSPEKTASI HASIL**

* **Konservatif** akan memilih threshold \~8-10%.  
* **Standar** akan memilih threshold \~12-15%.  
* **Agresif** akan memilih threshold \~18-20%.  
* **Intersection (Min 2 Votes)** diharapkan jatuh di area **12-15%**, yang memproduksi angka deteksi **\~5.500 \- 7.000 pohon**.

## **5\. ACTION PLAN**

1. Update config.py.  
2. Re-run simulasi v3.5.  
3. Jika hasil masuk range 4.500 \- 8.000 \-\> **LOCK & DEPLOY**.