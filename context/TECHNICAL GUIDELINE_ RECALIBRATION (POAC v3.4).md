# **TECHNICAL GUIDELINE: RECALIBRATION (POAC v3.4)**

Target: AI Agent Backend Team  
Context: Mengatasi Under-Detection (-83%) pada Gradient Elbow

## **1\. SITUASI SAAT INI**

* **Target (Ground Truth):** \~5.969 pohon.  
* **Hasil v3.3:** 1.022 pohon.  
* **Status:** **CRITICAL UNDER-DETECTION.**

## **2\. AKAR MASALAH**

Kombinasi antara **Range Capping** (yang didesain untuk metode lama) dan **Kneedle Algorithm** (metode baru) membuat ruang pencarian terlalu sempit. Kneedle sering menemukan "lokal optima" di angka rendah (misal 5%) dan berhenti di situ.

## **3\. INSTRUKSI PERBAIKAN (TUNING STEPS)**

Lakukan 2 langkah berikut secara berurutan untuk menaikkan sensitivitas sistem.

### **LANGKAH 1: LEPASKAN "HARD CAP" (Widen Ranges)**

Karena Kneedle bekerja berdasarkan kelengkungan kurva (bukan nilai maksimum), ia aman dilepas ke range yang lebih tinggi. Ia tidak akan "rakus" seperti metode Efficiency.

Update config.py:  
Buka keran pencarian agar Kneedle bisa menemukan tikungan di area 30-40% jika memang datanya mengarah ke sana.  
PRESET\_RANGES \= {  
    \# Konservatif: Naikkan sedikit agar tidak terlalu pelit  
    "konservatif": {"start": 0.05, "end": 0.20, "step": 0.01},   
      
    \# Standar: Buka sampai 40%  
    "standar":     {"start": 0.10, "end": 0.40, "step": 0.01},  
      
    \# Agresif: Buka sampai 60% (Biarkan Kneedle mencari batas alaminya)  
    "agresif":     {"start": 0.20, "end": 0.60, "step": 0.01}   
}

### **LANGKAH 2: EVALUASI VOTING LOGIC**

Coba jalankan simulasi ulang dengan *Ranges* baru di atas.

* **Skenario A (Ideal):** Jika hasil intersection (min\_votes=2) naik ke angka **4.500 \- 7.500**, maka **PERTAHANKAN** min\_votes=2. Ini adalah kondisi paling robust.  
* **Skenario B (Masih Rendah):** Jika hasil masih di bawah 3.000, ubah logika voting menjadi **UNION** (min\_votes=1).  
  * *Logika Union:* "Jika metode Konservatif ATAU Agresif bilang sakit, maka tandai sakit."

## **4\. TARGET METRIK (SUCCESS CRITERIA)**

Jangan berhenti tuning sampai angka output berada di **Range Toleransi**:

* **Batas Bawah:** 4.500 pohon (-25% dari GT).  
* **Target Ideal:** 6.000 pohon (Sesuai GT).  
* **Batas Atas:** 8.000 pohon (+35% dari GT, buffer untuk preventif).

## **5\. REKOMENDASI JANGKA PENDEK**

Untuk laporan ke Konsultan berikutnya, tolong sajikan tabel perbandingan:

| Skenario | Config Range | Voting Rule | Hasil Deteksi | % vs GT |
| :---- | :---- | :---- | :---- | :---- |
| v3.3 (Lama) | Capped (30%) | Intersection (2) | 1.022 | \-83% |
| **v3.4 A** | **Wide (60%)** | **Intersection (2)** | **\[ISI DISINI\]** | ... |
| v3.4 B | Wide (60%) | Union (1) | \[ISI DISINI\] | ... |

