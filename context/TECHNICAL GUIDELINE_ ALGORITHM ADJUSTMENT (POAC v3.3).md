# **TECHNICAL GUIDELINE: ALGORITHM ADJUSTMENT (POAC v3.3)**

Module: Ring of Fire Engine  
Focus: Elbow Method Optimization & Consensus Voting  
Status: IMMEDIATE EXECUTION

## **1\. LATAR BELAKANG (THE "DENSITY TRAP")**

Masalah:  
Metode Elbow saat ini menggunakan metrik Efficiency Ratio (Klaster Valid / Total Suspect).

* **Paradoks:** Semakin tinggi threshold (semakin banyak pohon dianggap sakit), kebun semakin "padat". Kepadatan tinggi memudahkan pembentukan klaster secara artifisial.  
* **Akibat:** Algoritma cenderung memilih threshold tertinggi (Agresif Max), menyebabkan *Over-Detection* (21.000+ pohon).

Solusi:  
Kita beralih dari filosofi "Mencari Efisiensi Tertinggi" ke "Mencari Titik Jenuh (Diminishing Returns)" menggunakan Gradient/Knee Method, dan menerapkan Consensus Voting sebagai filter akhir.

## **2\. PART A: REVISI ELBOW METHOD (GRADIENT / KNEEDLE)**

Instruksi:  
Ganti fungsi optimasi maximize\_efficiency dengan find\_knee\_point.

### **2.1 Konsep Matematis**

Kita mencari titik di mana penambahan persentase threshold tidak lagi memberikan penambahan jumlah klaster yang signifikan.

* **X-Axis:** Threshold (% populasi terburuk).  
* **Y-Axis:** Jumlah Klaster Terbentuk.  
* **Target:** Titik siku (Elbow/Knee) terjauh dari garis diagonal.

### **2.2 Pseudocode Implementation**

def find\_optimal\_threshold\_gradient(candidates):  
    """  
    candidates: List of dicts \[{'threshold': 0.1, 'n\_clusters': 50}, ...\]  
    Menggunakan metode Kneedle (Knee detection) sederhana.  
    """  
    \# 1\. Extract X (Threshold) dan Y (n\_clusters)  
    x \= \[c\['threshold'\] for c in candidates\]  
    y \= \[c\['n\_clusters'\] for c in candidates\]  
      
    \# 2\. Normalize X dan Y ke scale 0-1 agar sebanding  
    x\_norm \= (x \- min(x)) / (max(x) \- min(x))  
    y\_norm \= (y \- min(y)) / (max(y) \- min(y))  
      
    \# 3\. Hitung Jarak Tegak Lurus ke Garis Diagonal (Start ke End)  
    \# Garis diagonal ditarik dari poin pertama ke poin terakhir kurva  
    distances \= \[\]  
    for i in range(len(x)):  
        \# Rumus jarak titik ke garis (Perpendicular Distance)  
        \# Sederhananya: Difference curve \- diagonal  
        dist \= y\_norm\[i\] \- x\_norm\[i\]   
        distances.append(dist)  
          
    \# 4\. Cari index dengan jarak maksimum (The Knee)  
    optimal\_idx \= argmax(distances)  
      
    return candidates\[optimal\_idx\]\['threshold'\]

## **3\. PART B: IMPLEMENTASI CONSENSUS VOTING**

Instruksi:  
Jangan hanya menjalankan satu preset. Jalankan ketiganya, lalu cari irisan (Intersection).

### **3.1 Logika Bisnis**

Sebuah pohon hanya divonis **G3 (Actionable)** jika disepakati oleh minimal 2 dari 3 metodologi (Konservatif, Standar, Agresif).

### **3.2 Workflow Backend**

1. **Run Preset 1 (Konservatif):** Output \-\> Set A {Tree\_ID\_1, Tree\_ID\_2...}  
2. **Run Preset 2 (Standar):** Output \-\> Set B {Tree\_ID\_2, Tree\_ID\_3...}  
3. **Run Preset 3 (Agresif):** Output \-\> Set C {Tree\_ID\_2, Tree\_ID\_3, Tree\_ID\_4...}  
4. **Voting Process:**

def apply\_consensus\_voting(results\_dict):  
    """  
    results\_dict: {  
        'konservatif': \[id1, id2\],  
        'standar': \[id2, id3\],  
        'agresif': \[id2, id3, id4\]  
    }  
    """  
    vote\_counter \= {}  
      
    \# Hitung Vote  
    for preset, tree\_ids in results\_dict.items():  
        for tid in tree\_ids:  
            if tid not in vote\_counter:  
                vote\_counter\[tid\] \= 0  
            vote\_counter\[tid\] \+= 1  
              
    \# Filter Pemenang (Majority Rule)  
    final\_g3\_list \= \[\]  
    for tid, votes in vote\_counter.items():  
        if votes \>= 2:  \# Threshold Voting (2 dari 3\)  
            final\_g3\_list.append(tid)  
              
    return final\_g3\_list

## **4\. PART C: UPDATE CONFIGURATION**

Update file config.py untuk mendukung perubahan ini. Batasi juga range pencarian Agresif agar tidak "liar" sampai 50%.

\# SYSTEM CONFIGURATION v3.3

ALGORITHM\_SETTINGS \= {  
    \# Metode Tuning: 'efficiency' (Old) vs 'gradient' (New)  
    "elbow\_method": "gradient",   
      
    \# Consensus Voting: True/False  
    "use\_consensus": True,  
    "min\_votes": 2,  \# Minimal 2 preset setuju  
}

\# PRESET RANGES (Dibatasi/Capped)  
\# Mencegah Agresif mencari sampai 0.50 (50% kebun sakit)  
PRESET\_RANGES \= {  
    "konservatif": {"start": 0.01, "end": 0.10, "step": 0.01},  
    "standar":     {"start": 0.10, "end": 0.20, "step": 0.01},  
    "agresif":     {"start": 0.15, "end": 0.30, "step": 0.01} \# CAP di 30%  
}

## **5\. DAMPAK YANG DIHARAPKAN**

Dengan menerapkan **Gradient Elbow** \+ **Consensus Voting**:

1. **Reduksi False Positive:** Target penurunan jumlah deteksi dari \~21.000 menjadi **\~11.000 pohon** (Angka yang lebih realistis secara operasional).  
2. **Robustness:** Sistem tidak akan mudah "tertipu" oleh kepadatan (density trap).  
3. **Kredibilitas:** Angka 11.000 lebih mudah diterima oleh Manajemen Operasional dibanding 21.000.