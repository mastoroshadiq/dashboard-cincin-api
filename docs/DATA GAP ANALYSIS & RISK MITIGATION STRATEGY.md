# **DATA GAP ANALYSIS & RISK MITIGATION STRATEGY**

**Project:** POAC v3.3 \- Digital Nervous System

**Status:** LIVING DOCUMENT

**Last Updated:** \[Tanggal Hari Ini\]

## **1\. EXECUTIVE SUMMARY (THE "POLITICAL SHIELD")**

Tujuan Dokumen:  
Dokumen ini menginventarisasi variabel-variabel kritis yang saat ini BELUM TERSEDIA dalam sistem analitik POAC. Ketiadaan data ini diakui sebagai penyebab utama potensi False Positive (Alarm Palsu) atau False Negative (Lolos Deteksi).  
**Pernyataan Strategis:**

"Sistem saat ini bekerja optimal dalam batas kemampuan sensor spektral (Drone/Satelit). Akurasi 100% tidak dapat dicapai tanpa integrasi lapisan data abiotik (tanah/air) dan feedback loop manusia yang tercantum di bawah ini."

## **2\. ENVIRONMENTAL DATA GAPS (Faktor Alam)**

*Gap ini menjelaskan mengapa NDRE kadang tidak akurat di area tertentu.*

| Kategori Data | Status Saat Ini | Dampak pada Akurasi | Solusi Mitigasi (Sementara) |
| :---- | :---- | :---- | :---- |
| **Peta Genangan / Banjir** | ❌ **MISSING** | Area tergenang menyebabkan stres akar $\\rightarrow$ NDRE turun $\\rightarrow$ Terdeteksi G3 padahal hanya banjir. | Mandor melakukan *tagging* manual "Area Banjir" di aplikasi saat validasi. |
| **Defisiensi Hara (Nutrisi)** | ❌ **MISSING** | Daun kuning karena kurang Mg/N terbaca sama dengan gejala Ganoderma. | Gunakan Skenario *Threshold Konservatif* di area yang diketahui miskin hara. |
| **Topografi Mikro** | ❌ **MISSING** | Pohon di cekungan sering tergenang, pohon di bukit sering kering. NDRE bias. | Analisis visual mandor (Human-in-the-loop). |
| **Kedalaman Gambut** | ❌ **MISSING** | Gambut dalam \>3m memiliki perilaku kelembapan berbeda. | Asumsi *Flat Peat* untuk seluruh Divisi AME IV (Generalisasi). |

## **3\. OPERATIONAL DATA GAPS (Faktor Manusia)**

*Gap ini menjelaskan mengapa algoritma belum bisa "belajar" sendiri.*

| Kategori Data | Status Saat Ini | Dampak Bisnis | Action Plan |
| :---- | :---- | :---- | :---- |
| **Ground Truth Feedback** | ⚠️ **PARTIAL** | Algoritma tidak tahu apakah prediksinya benar atau salah. *Ensemble Model* tidak bisa dikalibrasi. | Wajibkan input "Realisasi Temuan" (Benar/Salah) untuk setiap Task Cincin Api. |
| **Riwayat Sensus Historis** | ❌ **MISSING** | Tidak bisa membedakan "Pohon Baru Sakit" vs "Pohon Sudah Lama Sakit". | Mulai *logging* snapshot status kesehatan per bulan mulai hari ini. |
| **Kapasitas Harian Tim** | ❌ **MISSING** | Sistem memberikan 100 tugas, padahal kapasitas tim hanya 20 tugas/hari. | Hardcode batasan tugas per mandor sementara waktu. |

## **4\. FINANCIAL DATA GAPS (Faktor Nilai \- Masukan Konsultan)**

*Gap ini menjelaskan mengapa dashboard belum bisa menampilkan "Potential Loss" (Rupiah).*

| Parameter Data | Nilai Default (Asumsi) | Risiko Asumsi | Kebutuhan Data Riil |
| :---- | :---- | :---- | :---- |
| **Valuasi Pohon Produktif** | Rp 1.500.000 / pohon | Bisa terlalu tinggi/rendah tergantung tahun tanam. | Tabel depresiasi aset biologis dari Finance. |
| **Cost of Treatment (Sanitasi)** | Rp 50.000 / pokok | Mengabaikan biaya logistik di area sulit. | Standar Biaya (HPS) terbaru dari Procurement. |
| **Cost of Treatment (Proteksi)** | Rp 15.000 / pokok | Fluktuasi harga bahan Trichoderma/Asap Cair. | Integrasi harga pokok produksi bahan hayati. |

## **5\. IMPACT MATRIX & PRIORITIZATION**

*Mana yang harus kita kejar datanya duluan?*

| Prioritas | Data Gap | Effort to Fix | Business Impact | Keputusan Manajemen |
| :---- | :---- | :---- | :---- | :---- |
| **PRIORITAS 1** | **Ground Truth Feedback** | **LOW** (Hanya SOP) | **HIGH** (Kunci Akurasi) | Wajib jalan minggu depan via App Mandor. |
| **PRIORITAS 2** | **Parameter Finansial** | **LOW** (Minta Finance) | **HIGH** (Buy-in Direksi) | Minta data ke Finance Controller besok. |
| **PRIORITAS 3** | **Peta Genangan Air** | **HIGH** (Survey Drone Lidar) | **MEDIUM** (Kurangi False Alarm) | Tunda ke Anggaran Tahun Depan. |

## **6\. DISCLAIMER UNTUK DASHBOARD**

*Teks ini wajib dicantumkan di footer Dashboard Executive:*

*"Analisis ini menggunakan pendekatan spektral (NDRE) dan spasial (Cincin Api). Akurasi prediksi dipengaruhi oleh faktor lingkungan (banjir/hara) yang belum terpetakan. Nilai kerugian finansial adalah estimasi berdasarkan asumsi standar perusahaan."*