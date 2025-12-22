# **Implementation Plan: Value-Driven Analytics Framework v2.1**

Date: 2024-12-17  
Status: In Progress  
Version: 2.1 (Updated with Consultant's Gap Analysis)

## **1\. Objective**

Mengimplementasikan framework analitik berbasis value bisnis yang menyertakan **WHY, WHAT, SO WHAT, NOW WHAT, dan SOLUTIONS** untuk setiap analisis Ganoderma yang dibuat.

## **2\. Framework: WIWSNS**

┌─────────────────────────────────────────────────────────────┐  
│  1\. WHY (Business Context)                                  │  
│     Mengapa analisis ini penting untuk bisnis?              │  
├─────────────────────────────────────────────────────────────┤  
│  2\. WHAT (Key Insights)                                     │  
│     Apa yang data ini ungkapkan?                            │  
├─────────────────────────────────────────────────────────────┤  
│  3\. SO WHAT (Business Impact)                               │  
│     Apa implikasi bisnisnya? (Termasuk Estimasi Rupiah)     │  
├─────────────────────────────────────────────────────────────┤  
│  4\. NOW WHAT (Actionable Recommendations)                   │  
│     Langkah konkret yang perlu diambil?                     │  
├─────────────────────────────────────────────────────────────┤  
│  5\. SOLUTIONS (Problem Resolution)                          │  
│     Solusi spesifik untuk setiap anomali/masalah            │  
└─────────────────────────────────────────────────────────────┘

## **3\. DATA GAP ANALYSIS: Drone vs Ground Truth**

**\[UPDATED\]** Gunakan referensi dokumen Docs/DATA\_GAP\_ANALYSIS.md sebagai sumber kebenaran tunggal (Single Source of Truth) untuk bagian ini.

### **3.1 Summary Comparison**

| Metric | Drone (NDRE) | Ground Truth (Fisik) | Gap (%) |
| :---- | :---- | :---- | :---- |
| Pokok G3 | 142 | 165 | \-14% |
| Pokok G2 | 560 | 410 | \+36% |

### **3.2 Root Cause Identification (Refer to Gap Analysis Doc)**

* **Environmental:** Banjir, Topografi, Defisiensi Hara.  
* **Operational:** Feedback loop mandor belum jalan.  
* **Financial:** Belum ada parameter biaya (HPS) di sistem.

## **4\. Implementation Phase Breakdown**

### **Phase 1: Preparation (✅ Done)**

* \[x\] Define Framework WIWSNS  
* \[x\] Analyze current dashboard limitations  
* \[x\] Identify missing business context

### **Phase 2: Documentation & Templates (⚡ In Progress)**

* \[x\] Create docs/ANALYSIS\_TEMPLATE.md  
* \[x\] Create docs/DATA\_GAP\_ANALYSIS.md (**DONE** \- See Consultant's Draft)  
  * *Includes: Environmental, Operational, and Financial Gaps.*  
* \[ \] Define standard sections for Report Generation

### **Phase 3: Executive Summary Construction**

* \[ \] Create docs/EXECUTIVE\_SUMMARY.md  
* \[ \] Compile all insights with WHY-WHAT-SO WHAT-SOLUTIONS  
* \[ \] **Action:** Inject "Financial Gap" data (Rupiah Loss) into the 'SO WHAT' section.

### **Phase 4: Dashboard Enhancement (UI/UX)**

* \[ \] **Header:** Add "Business Context" section.  
* \[ \] **Footer:** Add "Data Gap Disclaimer" (Copy from Gap Analysis Doc Section 6).  
* \[ \] **Feature:** Add "Potential Loss" counter (Formula: Tree Count \* Rp 1.5M).  
* \[ \] Regenerate HTML Dashboard.

## **7\. Current Status Summary**

| Component | Status | Notes |
| :---- | :---- | :---- |
| Threshold Calibration | ✅ Complete | AME II: \-1.5, AME IV: \-4.0 |
| Comprehensive Dashboard | ✅ Complete | 11 sections ready |
| SPH Analysis | ✅ Complete | \- |
| Data Gap Analysis | ✅ **Ready** | Dokumen DATA\_GAP\_ANALYSIS.md siap pakai |
| Value-Driven Framework | ⏳ In Progress | Integrasi parameter Rupiah |
| Solutions Implementation | ⏳ Pending | Menunggu persetujuan TBA |

## **8\. Appendix: Technical Details**

### **Calibrated Thresholds**

\# config.py  
CALIBRATED\_THRESHOLDS \= {  
    'AME002': {'Z\_Threshold\_G3': \-1.5, 'Z\_Threshold\_G2': \-0.5},  
    'AME004': {'Z\_Threshold\_G3': \-4.0, 'Z\_Threshold\_G2': \-2.0} \# Note: High tolerance due to Peat  
}  
