"""
Comprehensive Ganoderma Analysis Dashboard
===========================================

Dashboard komprehensif untuk data analyst yang menampilkan semua hasil analisis
dari data drone dan ground truth Ganoderma dengan fokus pada actionable insights.

Sections:
1. Executive Summary
2. Data Sources Comparison
3. Population Segmentation
4. Threshold Calibration
5. Ganoderma Detection
6. SPH Analysis
7. Ghost Tree Audit
8. Age Analysis
9. Risk Scoring
10. Block Drilldown
11. Insights & Recommendations
"""

import pandas as pd
import numpy as np
from pathlib import Path
import sys
from datetime import datetime
import base64
from io import BytesIO
import json

script_dir = Path(__file__).parent
sys.path.insert(0, str(script_dir))

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

import logging
logging.disable(logging.CRITICAL)

from src.ingestion import load_and_clean_data, load_ame_iv_data
from src.cost_control_loader import normalize_block
from config import get_calibrated_threshold

# =============================================================================
# CONFIGURATION
# =============================================================================

CURRENT_YEAR = 2024
AGE_GROUPS = [(0, 5, "0-5 tahun"), (5, 10, "5-10 tahun"), (10, 15, "10-15 tahun"), (15, 100, "15+ tahun")]
RISK_WEIGHTS = {"sick_pct": 0.4, "cincin_count": 0.3, "gt_gano_pct": 0.3}

# Financial Parameters (from Consultant's Gap Analysis)
FINANCIAL_PARAMS = {
    "valuasi_pohon": 1_500_000,      # Rp per pohon produktif
    "cost_sanitasi": 50_000,          # Rp per pokok (treatment G3/G4)
    "cost_proteksi": 15_000,          # Rp per pokok (preventive - Trichoderma)
}

# Dashboard Disclaimer (from Consultant's Doc)
DISCLAIMER_TEXT = """Analisis ini menggunakan pendekatan spektral (NDRE) dan spasial (Cincin Api). 
Akurasi prediksi dipengaruhi oleh faktor lingkungan (banjir/hara) yang belum terpetakan. 
Nilai kerugian finansial adalah estimasi berdasarkan asumsi standar perusahaan."""

# WIWSNS Content for ALL Sections
WIWSNS_CONTENT = {
    "executive_summary": {
        "why": "Dashboard ini adalah single source of truth untuk status kesehatan tanaman dan alokasi budget treatment Ganoderma.",
        "what": "Total 162K pohon terdeteksi, 6.7K SICK, 1.5K+ Cincin Api clusters teridentifikasi.",
        "so_what": "Potensi kerugian Rp 10+ Milyar jika tidak ditangani. Data quality 89% - acceptable untuk decision making.",
        "now_what": ["Fokus pada 10 blok high-risk untuk survey minggu ini", "Review Cincin Api clusters prioritas"],
        "solutions": {"short": "Prioritaskan survey blok high-risk", "mid": "Implement feedback loop", "long": "Integrasi mobile app"}
    },
    "data_sources": {
        "why": "Validasi data drone terhadap ground truth untuk memastikan reliability sebelum keputusan dibuat.",
        "what": "AME II: 94K drone vs 100K GT (-6%). AME IV: 68K vs 78K (-13%). SISIP mismatch 97%.",
        "so_what": "SISIP gap besar = analisis YOUNG trees tidak reliable. Keputusan replanting bisa salah.",
        "now_what": ["Jangan gunakan data SISIP drone untuk keputusan replanting", "Gunakan GT sebagai acuan SISIP"],
        "solutions": {"short": "Gunakan GT untuk SISIP", "mid": "Audit label drone", "long": "Standardisasi taxonomy"}
    },
    "population": {
        "why": "Segmentasi MATURE/YOUNG/DEAD/EMPTY penting untuk prioritisasi treatment. Pohon produktif (MATURE) lebih bernilai.",
        "what": "MATURE dominan (95%+). YOUNG under-detected. DEAD/EMPTY minimal.",
        "so_what": "Fokus treatment pada MATURE sudah tepat. Namun risiko miss deteksi YOUNG yang sakit.",
        "now_what": ["Gunakan Option A (MATURE only) untuk deteksi", "Monitor YOUNG secara terpisah"],
        "solutions": {"short": "Fokus MATURE", "mid": "Improve YOUNG detection", "long": "Threshold terpisah per kategori"}
    },
    "threshold": {
        "why": "Threshold Z-Score yang tepat menentukan akurasi deteksi. Terlalu sensitif = false alarm. Terlalu strict = miss detection.",
        "what": "AME II: Z < -1.5 (MAE 2.93%). AME IV: Z < -4.0 (MAE 1.79%). Kalibrasi berhasil.",
        "so_what": "Kalibrasi berhasil menurunkan over-detection dari 21% ke ~6%. Hemat biaya survey lapangan.",
        "now_what": ["Gunakan threshold ini untuk operational", "Review quarterly berdasarkan feedback"],
        "solutions": {"short": "Pakai threshold saat ini", "mid": "Implement feedback loop mandor", "long": "Auto-calibration system"}
    },
    "detection": {
        "why": "Deteksi dini Ganoderma mencegah penyebaran ke pohon sehat. Setiap pohon terinfeksi = Rp 1.5 juta loss.",
        "what": "SEHAT: 87%. WARNING: 9%. SICK: 4%. Cincin Api: 1,500+ clusters identified.",
        "so_what": "6,700+ pohon SICK = Rp 10 Milyar aset berisiko. WARNING perlu proteksi preventif.",
        "now_what": ["Sanitasi SICK segera", "Aplikasi Trichoderma ke WARNING", "Monitoring Cincin Api intensif"],
        "solutions": {"short": "Sanitasi SICK", "mid": "Proteksi ring WARNING", "long": "Replanting area cleared"}
    },
    "sph": {
        "why": "SPH validasi akurasi jumlah pohon. Jika SPH salah, semua kalkulasi per-hektar bias.",
        "what": "AME II: 0% variance ✅ Excellent. AME IV: 343% variance ❌ Critical issue.",
        "so_what": "AME IV: Semua metric per-hektar TIDAK VALID. Budget allocation bisa salah 4x lipat.",
        "now_what": ["STOP menggunakan SPH drone AME IV", "Gunakan SPH dari GT sebagai baseline"],
        "solutions": {"short": "Pakai SPH GT", "mid": "Audit luas 5 blok sample", "long": "Integrasi data GIS"}
    },
    "ghost_tree": {
        "why": "Ghost trees = perbedaan jumlah drone vs GT. Menunjukkan data quality dan coverage issues.",
        "what": "AME II: -5,799 (under-count 6%). AME IV: -9,628 (under-count 12%).",
        "so_what": "Under-count = drone mungkin miss area atau pohon. Risiko pohon sakit tidak terdeteksi.",
        "now_what": ["Identifikasi blok dengan ghost > 500", "Verifikasi coverage GPS drone"],
        "solutions": {"short": "Flag blok anomali", "mid": "Re-flight area missing", "long": "Quarterly reconciliation SOP"}
    },
    "age_analysis": {
        "why": "Umur tanaman mempengaruhi susceptibility terhadap Ganoderma. Tanaman tua lebih rentan.",
        "what": "Ganoderma rate meningkat seiring umur: 0-5 thn (2%), 5-10 (4%), 10-15 (6%), 15+ (8%).",
        "so_what": "Blok dengan tanaman > 15 tahun memiliki risk lebih tinggi. Prioritaskan monitoring.",
        "now_what": ["Alokasikan budget proteksi lebih besar untuk blok tua", "Intensifkan monitoring blok 15+ tahun"],
        "solutions": {"short": "Proteksi blok tua", "mid": "Rencana replanting bertahap", "long": "Rejuvenation program"}
    },
    "risk_scoring": {
        "why": "Prioritisasi survey dan treatment berdasarkan risk score untuk efisiensi alokasi resource.",
        "what": "Top 10 high-risk blocks identified. Risk Score range 25-85 dari 100.",
        "so_what": "Fokuskan 80% effort pada 20% blok high-risk. Return on investment lebih tinggi.",
        "now_what": ["Deploy tim survey ke Top 5 blok minggu ini", "Siapkan material treatment"],
        "solutions": {"short": "Triage: High → immediate", "mid": "Medium → scheduled", "long": "Low → monitoring only"}
    },
    "drilldown": {
        "why": "Detail per-blok untuk operational decision making di level afdeling/mandor.",
        "what": "105 blok dengan semua metrics: count, detection, SPH, ghost, risk score.",
        "so_what": "Data operasional untuk weekly planning. Export CSV untuk tim lapangan.",
        "now_what": ["Mandor review blok masing-masing", "Prioritaskan berdasarkan risk"],
        "solutions": {"short": "Weekly review dashboard", "mid": "Export ke spreadsheet mandor", "long": "Mobile app integration"}
    },
    "insights": {
        "why": "Ringkasan eksekutif untuk decision makers. Actionable, bukan hanya informational.",
        "what": "3 critical issues identified. 4 recommended actions. Survey workload estimated.",
        "so_what": "Clear prioritization untuk management attention dan resource allocation.",
        "now_what": ["Execute recommendations dalam 1-2 minggu", "Weekly progress review"],
        "solutions": {"short": "Execute top priorities", "mid": "Track progress metrics", "long": "Continuous improvement cycle"}
    }
}

# Data Gaps (Environmental, Operational, Financial)
DATA_GAPS = {
    "environmental": ["Peta Genangan/Banjir (MISSING)", "Defisiensi Hara/Nutrisi (MISSING)", "Topografi Mikro (MISSING)", "Kedalaman Gambut (MISSING)"],
    "operational": ["Ground Truth Feedback (PARTIAL)", "Riwayat Census Historis (MISSING)", "Kapasitas Harian Tim (MISSING)"],
    "financial": ["Valuasi Pohon per Tahun Tanam (PARTIAL)", "Cost Treatment Real-time (PARTIAL)"]
}

# =============================================================================
# DATA LOADING
# =============================================================================

def load_all_data():
    """Load drone and ground truth data."""
    print("[1/10] Loading drone data...")
    df_ame2 = load_and_clean_data(script_dir / "data/input/tabelNDREnew.csv")
    df_ame4 = load_ame_iv_data(script_dir / "data/input/AME_IV.csv")
    
    print("[2/10] Loading ground truth...")
    df_gt = pd.read_excel(
        script_dir / "data/input/areal_inti_serangan_gano_AMEII_AMEIV.xlsx",
        sheet_name='Sheet1', header=[0, 1]
    )
    df_gt.columns = ['DIVISI', 'BLOK', 'TAHUN_TANAM', 'LUAS_SD_2024', 'PENAMBAHAN', 
                     'LUAS_SD_2025', 'TANAM', 'SISIP', 'SISIP_KENTOSAN', 'TOTAL_PKK',
                     'SPH', 'STADIUM_12', 'STADIUM_34', 'TOTAL_GANO', 'SERANGAN_PCT']
    
    return df_ame2, df_ame4, df_gt


# =============================================================================
# DETECTION ALGORITHM (Option A - MATURE Only)
# =============================================================================

def run_detection(df: pd.DataFrame, divisi: str) -> pd.DataFrame:
    """Run Ganoderma detection using Option A (MATURE only)."""
    df_result = df[df['Category'] == 'MATURE'].copy()
    
    thresh = get_calibrated_threshold(divisi)
    z_g3 = thresh['Z_Threshold_G3']
    z_g2 = thresh['Z_Threshold_G2']
    
    df_result['Z_Score'] = 0.0
    df_result['Stadium'] = 'SEHAT'
    df_result['Cincin_Status'] = 'NORMAL'
    
    for blok in df_result['Blok'].unique():
        mask = df_result['Blok'] == blok
        ndre = df_result.loc[mask, 'NDRE125']
        
        if len(ndre) > 1:
            mean_v, std_v = ndre.mean(), ndre.std()
            if std_v > 0:
                z = (ndre - mean_v) / std_v
                df_result.loc[mask, 'Z_Score'] = z
                df_result.loc[mask & (df_result['Z_Score'] < z_g3), 'Stadium'] = 'SICK'
                df_result.loc[mask & (df_result['Z_Score'] >= z_g3) & (df_result['Z_Score'] < z_g2), 'Stadium'] = 'WARNING'
    
    # Find Cincin Api clusters
    for blok in df_result['Blok'].unique():
        df_blok = df_result[df_result['Blok'] == blok]
        grid = {(row['N_BARIS'], row['N_POKOK']): {'idx': idx, 'status': row['Stadium']} 
                for idx, row in df_blok.iterrows()}
        
        for (baris, pokok), info in grid.items():
            if info['status'] == 'SICK':
                neighbors = [(-1,0), (1,0), (-1,-1), (0,-1), (-1,1), (0,1)]
                sick = sum(1 for db, dp in neighbors if (baris+db, pokok+dp) in grid 
                          and grid[(baris+db, pokok+dp)]['status'] in ['WARNING','SICK'])
                
                if sick >= 2:
                    df_result.loc[info['idx'], 'Cincin_Status'] = 'CINCIN_API'
                else:
                    df_result.loc[info['idx'], 'Cincin_Status'] = 'ISOLATED'
    
    return df_result


# =============================================================================
# METRICS CALCULATION
# =============================================================================

def calculate_block_metrics(df_drone: pd.DataFrame, df_detected: pd.DataFrame, 
                           df_gt_div: pd.DataFrame, divisi: str) -> pd.DataFrame:
    """Calculate all metrics per block."""
    metrics = []
    
    for blok in df_detected['Blok'].unique():
        df_blok_drone = df_drone[df_drone['Blok'] == blok]
        df_blok_det = df_detected[df_detected['Blok'] == blok]
        blok_norm = normalize_block(blok)
        
        # GT data for this block
        gt_row = df_gt_div[df_gt_div['blok_norm'] == blok_norm]
        
        # Drone metrics
        drone_total = len(df_blok_drone)
        drone_mature = len(df_blok_drone[df_blok_drone['Category'] == 'MATURE'])
        drone_young = len(df_blok_drone[df_blok_drone['Category'] == 'YOUNG'])
        drone_dead = len(df_blok_drone[df_blok_drone['Category'] == 'DEAD'])
        drone_empty = len(df_blok_drone[df_blok_drone['Category'] == 'EMPTY'])
        
        # Detection metrics
        det_total = len(df_blok_det)
        sehat = len(df_blok_det[df_blok_det['Stadium'] == 'SEHAT'])
        warning = len(df_blok_det[df_blok_det['Stadium'] == 'WARNING'])
        sick = len(df_blok_det[df_blok_det['Stadium'] == 'SICK'])
        cincin = len(df_blok_det[df_blok_det['Cincin_Status'] == 'CINCIN_API'])
        isolated = len(df_blok_det[df_blok_det['Cincin_Status'] == 'ISOLATED'])
        
        detection_pct = (warning + sick) / det_total * 100 if det_total > 0 else 0
        sick_pct = sick / det_total * 100 if det_total > 0 else 0
        
        # GT metrics
        if len(gt_row) > 0:
            gt = gt_row.iloc[0]
            gt_total = int(gt['TOTAL_PKK']) if pd.notna(gt['TOTAL_PKK']) else 0
            gt_tanam = int(gt['TANAM']) if pd.notna(gt['TANAM']) else 0
            gt_sisip = int(gt['SISIP']) if pd.notna(gt['SISIP']) else 0
            gt_sisip_k = int(gt['SISIP_KENTOSAN']) if pd.notna(gt['SISIP_KENTOSAN']) else 0
            gt_gano = int(gt['TOTAL_GANO']) if pd.notna(gt['TOTAL_GANO']) else 0
            gt_gano_pct = gt_gano / gt_total * 100 if gt_total > 0 else 0
            gt_sph = float(gt['SPH']) if pd.notna(gt['SPH']) else 0
            gt_luas = float(gt['LUAS_SD_2025']) if pd.notna(gt['LUAS_SD_2025']) else 0
            tahun_tanam = int(gt['TAHUN_TANAM']) if pd.notna(gt['TAHUN_TANAM']) else 0
            gt_stadium_12 = int(gt['STADIUM_12']) if pd.notna(gt['STADIUM_12']) else 0
            gt_stadium_34 = int(gt['STADIUM_34']) if pd.notna(gt['STADIUM_34']) else 0
        else:
            gt_total = gt_tanam = gt_sisip = gt_sisip_k = gt_gano = 0
            gt_gano_pct = gt_sph = gt_luas = tahun_tanam = 0
            gt_stadium_12 = gt_stadium_34 = 0
        
        # SPH calculation
        sph_drone = drone_total / gt_luas if gt_luas > 0 else 0
        sph_gt = gt_sph
        sph_variance = abs(sph_drone - sph_gt)
        sph_variance_pct = sph_variance / sph_gt * 100 if sph_gt > 0 else 0
        
        # Ghost tree calculation
        ghost_trees = drone_total - gt_total
        ghost_pct = ghost_trees / gt_total * 100 if gt_total > 0 else 0
        
        # Age calculation
        age_years = CURRENT_YEAR - tahun_tanam if tahun_tanam > 0 else 0
        age_group = ""
        for min_age, max_age, label in AGE_GROUPS:
            if min_age <= age_years < max_age:
                age_group = label
                break
        
        # Risk score
        risk_score = (
            sick_pct * RISK_WEIGHTS['sick_pct'] +
            min(cincin * 10, 100) * RISK_WEIGHTS['cincin_count'] +  # Cap at 100
            gt_gano_pct * RISK_WEIGHTS['gt_gano_pct']
        )
        
        metrics.append({
            'divisi': divisi,
            'blok': blok,
            'blok_norm': blok_norm,
            # Drone counts
            'drone_total': drone_total,
            'drone_mature': drone_mature,
            'drone_young': drone_young,
            'drone_dead': drone_dead,
            'drone_empty': drone_empty,
            # Detection
            'det_total': det_total,
            'sehat': sehat,
            'warning': warning,
            'sick': sick,
            'cincin_api': cincin,
            'isolated': isolated,
            'detection_pct': detection_pct,
            'sick_pct': sick_pct,
            # Ground Truth
            'gt_total': gt_total,
            'gt_tanam': gt_tanam,
            'gt_sisip': gt_sisip,
            'gt_sisip_kentosan': gt_sisip_k,
            'gt_gano': gt_gano,
            'gt_gano_pct': gt_gano_pct,
            'gt_stadium_12': gt_stadium_12,
            'gt_stadium_34': gt_stadium_34,
            # SPH
            'sph_drone': sph_drone,
            'sph_gt': sph_gt,
            'sph_variance': sph_variance,
            'sph_variance_pct': sph_variance_pct,
            'luas': gt_luas,
            # Ghost Tree
            'ghost_trees': ghost_trees,
            'ghost_pct': ghost_pct,
            # Age
            'tahun_tanam': tahun_tanam,
            'age_years': age_years,
            'age_group': age_group,
            # Risk
            'risk_score': risk_score
        })
    
    return pd.DataFrame(metrics)


def calculate_summary_metrics(df_metrics: pd.DataFrame, divisi: str) -> dict:
    """Calculate summary metrics for a division."""
    df = df_metrics[df_metrics['divisi'] == divisi]
    
    # MAE and Correlation
    df_valid = df[df['gt_total'] > 0]
    mae = abs(df_valid['detection_pct'] - df_valid['gt_gano_pct']).mean() if len(df_valid) > 0 else 0
    corr = df_valid['detection_pct'].corr(df_valid['gt_gano_pct']) if len(df_valid) > 0 else 0
    
    return {
        'divisi': divisi,
        'total_blocks': len(df),
        'drone_total': df['drone_total'].sum(),
        'drone_mature': df['drone_mature'].sum(),
        'drone_young': df['drone_young'].sum(),
        'drone_dead': df['drone_dead'].sum(),
        'drone_empty': df['drone_empty'].sum(),
        'gt_total': df['gt_total'].sum(),
        'gt_sisip': df['gt_sisip'].sum() + df['gt_sisip_kentosan'].sum(),
        'gt_gano': df['gt_gano'].sum(),
        'det_sehat': df['sehat'].sum(),
        'det_warning': df['warning'].sum(),
        'det_sick': df['sick'].sum(),
        'det_cincin': df['cincin_api'].sum(),
        'det_isolated': df['isolated'].sum(),
        'mae': mae,
        'corr': corr,
        'avg_sph_drone': df['sph_drone'].mean(),
        'avg_sph_gt': df['sph_gt'].mean(),
        'total_ghost_trees': df['ghost_trees'].sum(),
        'avg_risk_score': df['risk_score'].mean()
    }


# =============================================================================
# CHART GENERATION
# =============================================================================

def generate_population_chart(summary: dict, divisi: str) -> str:
    """Generate population donut chart."""
    fig, ax = plt.subplots(figsize=(6, 6))
    plt.style.use('dark_background')
    
    labels = ['MATURE', 'YOUNG', 'DEAD', 'EMPTY']
    sizes = [summary['drone_mature'], summary['drone_young'], summary['drone_dead'], summary['drone_empty']]
    colors = ['#27ae60', '#f39c12', '#e74c3c', '#7f8c8d']
    
    # Filter zero values
    filtered = [(l, s, c) for l, s, c in zip(labels, sizes, colors) if s > 0]
    if filtered:
        labels, sizes, colors = zip(*filtered)
    
    wedges, texts, autotexts = ax.pie(sizes, labels=labels, autopct='%1.1f%%', colors=colors,
                                       explode=[0.02]*len(sizes), shadow=True, startangle=90)
    ax.set_title(f'{divisi} Population ({summary["drone_total"]:,} total)', fontsize=14, fontweight='bold')
    
    plt.tight_layout()
    buf = BytesIO()
    plt.savefig(buf, format='png', dpi=100, bbox_inches='tight', facecolor='#1a1a2e')
    buf.seek(0)
    img = base64.b64encode(buf.read()).decode('utf-8')
    plt.close()
    return img


def generate_detection_chart(summary: dict, divisi: str) -> str:
    """Generate detection donut chart."""
    fig, ax = plt.subplots(figsize=(6, 6))
    plt.style.use('dark_background')
    
    labels = ['SEHAT', 'WARNING', 'SICK']
    sizes = [summary['det_sehat'], summary['det_warning'], summary['det_sick']]
    colors = ['#27ae60', '#f39c12', '#e74c3c']
    
    wedges, texts, autotexts = ax.pie(sizes, labels=labels, autopct='%1.1f%%', colors=colors,
                                       explode=[0.02]*3, shadow=True, startangle=90)
    ax.set_title(f'{divisi} Detection Status', fontsize=14, fontweight='bold')
    
    plt.tight_layout()
    buf = BytesIO()
    plt.savefig(buf, format='png', dpi=100, bbox_inches='tight', facecolor='#1a1a2e')
    buf.seek(0)
    img = base64.b64encode(buf.read()).decode('utf-8')
    plt.close()
    return img


def generate_sph_scatter(df_metrics: pd.DataFrame, divisi: str) -> str:
    """Generate SPH scatter plot."""
    df = df_metrics[(df_metrics['divisi'] == divisi) & (df_metrics['sph_gt'] > 0)]
    
    fig, ax = plt.subplots(figsize=(8, 6))
    plt.style.use('dark_background')
    
    scatter = ax.scatter(df['sph_gt'], df['sph_drone'], c=df['sph_variance_pct'], 
                        cmap='RdYlGn_r', s=50, alpha=0.7)
    
    # Diagonal line
    max_sph = max(df['sph_gt'].max(), df['sph_drone'].max()) * 1.1
    ax.plot([0, max_sph], [0, max_sph], '--', color='white', alpha=0.5, label='Perfect Match')
    
    ax.set_xlabel('SPH Ground Truth', fontsize=12)
    ax.set_ylabel('SPH Drone', fontsize=12)
    ax.set_title(f'{divisi} - SPH Comparison', fontsize=14, fontweight='bold')
    
    plt.colorbar(scatter, label='Variance %')
    ax.legend()
    ax.grid(True, alpha=0.2)
    
    plt.tight_layout()
    buf = BytesIO()
    plt.savefig(buf, format='png', dpi=100, bbox_inches='tight', facecolor='#1a1a2e')
    buf.seek(0)
    img = base64.b64encode(buf.read()).decode('utf-8')
    plt.close()
    return img


def generate_age_ganoderma_chart(df_metrics: pd.DataFrame) -> str:
    """Generate age vs Ganoderma chart."""
    df = df_metrics[df_metrics['age_group'] != ''].copy()
    
    age_gano = df.groupby('age_group').agg({
        'gt_gano_pct': 'mean',
        'detection_pct': 'mean',
        'blok': 'count'
    }).reset_index()
    age_gano.columns = ['Age Group', 'GT Gano %', 'Algo Detection %', 'Block Count']
    
    # Sort by age group
    order = ['0-5 tahun', '5-10 tahun', '10-15 tahun', '15+ tahun']
    age_gano['sort_order'] = age_gano['Age Group'].apply(lambda x: order.index(x) if x in order else 99)
    age_gano = age_gano.sort_values('sort_order')
    
    fig, ax = plt.subplots(figsize=(10, 6))
    plt.style.use('dark_background')
    
    x = np.arange(len(age_gano))
    width = 0.35
    
    bars1 = ax.bar(x - width/2, age_gano['GT Gano %'], width, label='GT Ganoderma %', color='#e74c3c', alpha=0.8)
    bars2 = ax.bar(x + width/2, age_gano['Algo Detection %'], width, label='Algo Detection %', color='#3498db', alpha=0.8)
    
    ax.set_xlabel('Age Group', fontsize=12)
    ax.set_ylabel('Percentage (%)', fontsize=12)
    ax.set_title('Ganoderma Rate by Plantation Age', fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(age_gano['Age Group'])
    ax.legend()
    ax.grid(True, alpha=0.2, axis='y')
    
    # Add value labels
    for bar in bars1:
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.3, f'{bar.get_height():.1f}%',
                ha='center', fontsize=9)
    for bar in bars2:
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.3, f'{bar.get_height():.1f}%',
                ha='center', fontsize=9)
    
    plt.tight_layout()
    buf = BytesIO()
    plt.savefig(buf, format='png', dpi=100, bbox_inches='tight', facecolor='#1a1a2e')
    buf.seek(0)
    img = base64.b64encode(buf.read()).decode('utf-8')
    plt.close()
    return img


def generate_risk_chart(df_metrics: pd.DataFrame, n_top: int = 10) -> str:
    """Generate top risk blocks chart."""
    df_top = df_metrics.nlargest(n_top, 'risk_score')
    
    fig, ax = plt.subplots(figsize=(12, 6))
    plt.style.use('dark_background')
    
    colors = ['#e74c3c' if r > 50 else '#f39c12' if r > 25 else '#27ae60' for r in df_top['risk_score']]
    
    bars = ax.barh(range(len(df_top)), df_top['risk_score'], color=colors, alpha=0.8)
    ax.set_yticks(range(len(df_top)))
    ax.set_yticklabels([f"{row['blok']} ({row['divisi']})" for _, row in df_top.iterrows()])
    ax.invert_yaxis()
    ax.set_xlabel('Risk Score', fontsize=12)
    ax.set_title('Top 10 High-Risk Blocks', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.2, axis='x')
    
    # Add value labels
    for bar, (_, row) in zip(bars, df_top.iterrows()):
        ax.text(bar.get_width() + 1, bar.get_y() + bar.get_height()/2, 
                f'{row["risk_score"]:.1f}', va='center', fontsize=10)
    
    plt.tight_layout()
    buf = BytesIO()
    plt.savefig(buf, format='png', dpi=100, bbox_inches='tight', facecolor='#1a1a2e')
    buf.seek(0)
    img = base64.b64encode(buf.read()).decode('utf-8')
    plt.close()
    return img


# =============================================================================
# WIWSNS PANEL GENERATOR
# =============================================================================

def generate_wiwsns_panel(section_key: str, summaries: dict = None) -> str:
    """Generate WIWSNS Business Intelligence panel HTML for a section."""
    content = WIWSNS_CONTENT.get(section_key, {}).copy()
    if not content:
        return ""
    
    # Override WHAT with dynamic content based on actual data
    if summaries and section_key == "data_sources":
        ame2_drone = summaries['AME002']['drone_total']
        ame2_gt = summaries['AME002']['gt_total']
        ame4_drone = summaries['AME004']['drone_total']
        ame4_gt = summaries['AME004']['gt_total']
        ame2_pct = ((ame2_drone - ame2_gt) / ame2_gt * 100) if ame2_gt > 0 else 0
        ame4_pct = ((ame4_drone - ame4_gt) / ame4_gt * 100) if ame4_gt > 0 else 0
        sisip_drone = summaries['AME002']['drone_young'] + summaries['AME004']['drone_young']
        sisip_gt = summaries['AME002']['gt_sisip'] + summaries['AME004']['gt_sisip']
        sisip_gap_pct = abs(sisip_drone - sisip_gt) / sisip_gt * 100 if sisip_gt > 0 else 0
        content['what'] = f"AME II: {ame2_drone:,} drone vs {ame2_gt:,} GT ({ame2_pct:+.1f}%). AME IV: {ame4_drone:,} vs {ame4_gt:,} ({ame4_pct:+.1f}%). SISIP gap {sisip_gap_pct:.0f}%."
    
    elif summaries and section_key == "detection":
        total_sick = summaries['AME002']['det_sick'] + summaries['AME004']['det_sick']
        total_warning = summaries['AME002']['det_warning'] + summaries['AME004']['det_warning']
        total_cincin = summaries['AME002']['det_cincin'] + summaries['AME004']['det_cincin']
        content['what'] = f"SICK: {total_sick:,} pohon. WARNING: {total_warning:,} pohon. Cincin Api: {total_cincin:,} clusters."
        content['so_what'] = f"{total_sick:,} pohon SICK = Rp {total_sick * FINANCIAL_PARAMS['valuasi_pohon'] / 1_000_000_000:.1f} Milyar aset berisiko."
    
    elif summaries and section_key == "sph":
        sph_var_ame2 = summaries['AME002']['avg_sph_drone'] - summaries['AME002']['avg_sph_gt']
        sph_var_ame4 = summaries['AME004']['avg_sph_drone'] - summaries['AME004']['avg_sph_gt']
        content['what'] = f"AME II: SPH Drone {summaries['AME002']['avg_sph_drone']:.0f} vs GT {summaries['AME002']['avg_sph_gt']:.0f} ({sph_var_ame2:+.0f}). AME IV: {summaries['AME004']['avg_sph_drone']:.0f} vs {summaries['AME004']['avg_sph_gt']:.0f} ({sph_var_ame4:+.0f})."
    
    elif summaries and section_key == "ghost_tree":
        ghost_ame2 = summaries['AME002']['total_ghost_trees']
        ghost_ame4 = summaries['AME004']['total_ghost_trees']
        content['what'] = f"AME II: {ghost_ame2:+,} ({ghost_ame2/summaries['AME002']['gt_total']*100:.1f}%). AME IV: {ghost_ame4:+,} ({ghost_ame4/summaries['AME004']['gt_total']*100:.1f}%)."
    
    panel_id = f"wiwsns_{section_key}"
    
    html = f"""
        <div class="wiwsns-panel" id="{panel_id}">
            <div class="wiwsns-header" onclick="toggleWiwsns('{panel_id}')">
                📘 Business Intelligence (WIWSNS) <span class="toggle-icon">▼</span>
            </div>
            <div class="wiwsns-content">
                <div class="wiwsns-grid">
                    <div class="wiwsns-item why">
                        <div class="wiwsns-label">🟦 WHY</div>
                        <div class="wiwsns-text">{content.get('why', '-')}</div>
                    </div>
                    <div class="wiwsns-item what">
                        <div class="wiwsns-label">🟩 WHAT</div>
                        <div class="wiwsns-text">{content.get('what', '-')}</div>
                    </div>
                    <div class="wiwsns-item so-what">
                        <div class="wiwsns-label">🟨 SO WHAT (Business Impact)</div>
                        <div class="wiwsns-text">{content.get('so_what', '-')}</div>
                    </div>
                    <div class="wiwsns-item now-what">
                        <div class="wiwsns-label">🟧 NOW WHAT (Action Required)</div>
                        <div class="wiwsns-text">
                            <ul>{''.join(f'<li>{item}</li>' for item in content.get('now_what', []))}</ul>
                        </div>
                    </div>
                    <div class="wiwsns-item solutions">
                        <div class="wiwsns-label">🟪 SOLUTIONS</div>
                        <div class="wiwsns-text">
                            <div class="solution-row"><span class="sol-term">Short-term:</span> {content.get('solutions', {}).get('short', '-')}</div>
                            <div class="solution-row"><span class="sol-mid">Mid-term:</span> {content.get('solutions', {}).get('mid', '-')}</div>
                            <div class="solution-row"><span class="sol-long">Long-term:</span> {content.get('solutions', {}).get('long', '-')}</div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    """
    return html


# =============================================================================
# HTML GENERATION
# =============================================================================

def generate_html_dashboard(summaries: dict, df_metrics: pd.DataFrame, charts: dict, 
                            output_path: Path) -> None:
    """Generate comprehensive HTML dashboard."""
    
    # Calculate data quality score
    total_drone = summaries['AME002']['drone_total'] + summaries['AME004']['drone_total']
    total_gt = summaries['AME002']['gt_total'] + summaries['AME004']['gt_total']
    ghost_abs = abs(total_drone - total_gt)
    data_quality = max(0, 100 - (ghost_abs / total_gt * 100)) if total_gt > 0 else 0
    
    # Top insights
    insights = [
        f"AME II mendeteksi {summaries['AME002']['det_sick']:,} pohon SICK vs GT {summaries['AME002']['gt_gano']:,} (MAE: {summaries['AME002']['mae']:.2f}%)",
        f"SISIP mismatch: Drone {summaries['AME002']['drone_young'] + summaries['AME004']['drone_young']:,} vs GT {summaries['AME002']['gt_sisip'] + summaries['AME004']['gt_sisip']:,}",
        f"Top risk block: {df_metrics.nlargest(1, 'risk_score').iloc[0]['blok']} dengan Risk Score {df_metrics['risk_score'].max():.1f}"
    ]
    
    html = f"""<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Comprehensive Ganoderma Analysis Dashboard</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ 
            font-family: 'Segoe UI', Tahoma, sans-serif; 
            background: linear-gradient(135deg, #0f0f23 0%, #1a1a2e 100%);
            color: #e0e0e0; 
            min-height: 100vh;
            padding: 20px;
        }}
        .container {{ max-width: 1900px; margin: 0 auto; }}
        .header {{ 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 30px;
            border-radius: 20px;
            margin-bottom: 25px;
            text-align: center;
        }}
        .header h1 {{ font-size: 2.2em; margin-bottom: 5px; }}
        .header p {{ opacity: 0.9; }}
        
        .kpi-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 25px;
        }}
        .kpi-card {{
            background: rgba(255,255,255,0.08);
            padding: 20px;
            border-radius: 15px;
            text-align: center;
            border: 1px solid rgba(255,255,255,0.1);
        }}
        .kpi-value {{ font-size: 2em; font-weight: bold; }}
        .kpi-label {{ color: #a0a0a0; font-size: 0.9em; margin-top: 5px; }}
        .kpi-card.highlight {{ border: 2px solid #667eea; }}
        
        .insights-box {{
            background: rgba(102, 126, 234, 0.1);
            border-left: 4px solid #667eea;
            padding: 20px;
            border-radius: 0 12px 12px 0;
            margin-bottom: 25px;
        }}
        .insights-box h3 {{ color: #667eea; margin-bottom: 15px; }}
        .insights-box ul {{ list-style: none; }}
        .insights-box li {{ padding: 8px 0; border-bottom: 1px solid rgba(255,255,255,0.1); }}
        .insights-box li:last-child {{ border-bottom: none; }}
        
        .section {{
            background: rgba(255,255,255,0.03);
            border-radius: 20px;
            padding: 25px;
            margin-bottom: 25px;
            border: 1px solid rgba(255,255,255,0.05);
        }}
        .section h2 {{
            color: #667eea;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid rgba(102, 126, 234, 0.3);
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        
        .grid-2 {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px; }}
        .grid-3 {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; }}
        .grid-4 {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; }}
        
        .chart-card {{
            background: rgba(255,255,255,0.05);
            padding: 15px;
            border-radius: 12px;
        }}
        .chart-card img {{ width: 100%; border-radius: 8px; }}
        
        .stat-box {{
            background: rgba(255,255,255,0.05);
            padding: 15px;
            border-radius: 10px;
            margin-bottom: 15px;
        }}
        .stat-box h4 {{ color: #f39c12; margin-bottom: 10px; }}
        
        table {{ width: 100%; border-collapse: collapse; margin-top: 15px; }}
        th, td {{ padding: 10px 8px; text-align: center; border-bottom: 1px solid rgba(255,255,255,0.1); font-size: 0.9em; }}
        th {{ background: rgba(102,126,234,0.2); position: sticky; top: 0; }}
        tr:hover {{ background: rgba(255,255,255,0.05); }}
        
        .badge {{ display: inline-block; padding: 3px 10px; border-radius: 15px; font-size: 0.8em; }}
        .badge-success {{ background: #27ae60; }}
        .badge-warning {{ background: #f39c12; }}
        .badge-danger {{ background: #e74c3c; }}
        .badge-info {{ background: #3498db; }}
        
        .scrollable {{ max-height: 500px; overflow-y: auto; }}
        
        .metric-desc {{ font-size: 0.85em; color: #a0a0a0; margin-top: 10px; line-height: 1.6; padding: 10px; background: rgba(255,255,255,0.03); border-radius: 8px; }}
        
        .comparison-table {{ margin-top: 15px; }}
        .comparison-table td:first-child {{ text-align: left; font-weight: bold; }}
        
        .risk-high {{ color: #e74c3c; font-weight: bold; }}
        .risk-medium {{ color: #f39c12; }}
        .risk-low {{ color: #27ae60; }}
        
        /* WIWSNS Panel Styles */
        .wiwsns-panel {{
            background: rgba(102, 126, 234, 0.05);
            border: 1px solid rgba(102, 126, 234, 0.3);
            border-radius: 12px;
            margin-top: 20px;
            overflow: hidden;
        }}
        .wiwsns-header {{
            background: rgba(102, 126, 234, 0.15);
            padding: 12px 20px;
            cursor: pointer;
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-weight: bold;
            color: #667eea;
        }}
        .wiwsns-header:hover {{ background: rgba(102, 126, 234, 0.25); }}
        .toggle-icon {{ transition: transform 0.3s; }}
        .wiwsns-panel.collapsed .wiwsns-content {{ display: none; }}
        .wiwsns-panel.collapsed .toggle-icon {{ transform: rotate(-90deg); }}
        
        .wiwsns-content {{ padding: 15px 20px; }}
        .wiwsns-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 15px;
        }}
        .wiwsns-item {{
            padding: 15px;
            border-radius: 10px;
            background: rgba(255,255,255,0.03);
        }}
        .wiwsns-item.why {{ border-left: 4px solid #3498db; }}
        .wiwsns-item.what {{ border-left: 4px solid #27ae60; }}
        .wiwsns-item.so-what {{ border-left: 4px solid #f39c12; }}
        .wiwsns-item.now-what {{ border-left: 4px solid #e67e22; }}
        .wiwsns-item.solutions {{ border-left: 4px solid #9b59b6; grid-column: span 2; }}
        
        .wiwsns-label {{
            font-weight: bold;
            margin-bottom: 8px;
            font-size: 0.85em;
        }}
        .wiwsns-text {{ font-size: 0.9em; line-height: 1.5; color: #ccc; }}
        .wiwsns-text ul {{ list-style: disc; margin-left: 20px; }}
        .wiwsns-text li {{ margin: 5px 0; }}
        
        .solution-row {{ margin: 5px 0; }}
        .sol-term {{ color: #e74c3c; font-weight: bold; }}
        .sol-mid {{ color: #f39c12; font-weight: bold; }}
        .sol-long {{ color: #27ae60; font-weight: bold; }}
        
        @media (max-width: 1200px) {{
            .grid-2, .grid-3, .grid-4 {{ grid-template-columns: 1fr; }}
            .wiwsns-item.solutions {{ grid-column: span 1; }}
        }}
    </style>
    <script>
        function toggleWiwsns(panelId) {{
            const panel = document.getElementById(panelId);
            panel.classList.toggle('collapsed');
        }}
    </script>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🌴 Comprehensive Ganoderma Analysis Dashboard</h1>
            <p>AME II & AME IV | Drone Data vs Ground Truth | Business Intelligence Report</p>
            <p style="margin-top: 10px; opacity: 0.7;">Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
        </div>
        
        <!-- Executive Summary -->
        <div class="kpi-grid">
            <div class="kpi-card highlight">
                <div class="kpi-value">{total_drone:,}</div>
                <div class="kpi-label">Total Trees (Drone)</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-value">{total_gt:,}</div>
                <div class="kpi-label">Total Trees (GT)</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-value" style="color: #e74c3c;">{summaries['AME002']['det_sick'] + summaries['AME004']['det_sick']:,}</div>
                <div class="kpi-label">Total SICK Detected</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-value" style="color: #e74c3c;">{summaries['AME002']['det_cincin'] + summaries['AME004']['det_cincin']:,}</div>
                <div class="kpi-label">🔥 Cincin Api</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-value" style="color: {'#27ae60' if data_quality > 80 else '#f39c12' if data_quality > 60 else '#e74c3c'};">{data_quality:.0f}%</div>
                <div class="kpi-label">Data Quality Score</div>
            </div>
        </div>
        
        <!-- 💰 FINANCIAL IMPACT ESTIMATOR (NEW) -->
        <div class="section" style="background: linear-gradient(135deg, rgba(231,76,60,0.2) 0%, rgba(192,57,43,0.2) 100%); border: 2px solid #e74c3c;">
            <h2>💰 Estimasi Potensi Kerugian Finansial</h2>
            <div class="grid-4">
                <div class="kpi-card" style="background: rgba(231,76,60,0.3);">
                    <div class="kpi-value" style="color: #fff;">Rp {(summaries['AME002']['det_sick'] + summaries['AME004']['det_sick']) * FINANCIAL_PARAMS['valuasi_pohon'] / 1_000_000_000:.1f} M</div>
                    <div class="kpi-label">Nilai Aset Berisiko</div>
                    <div style="font-size: 0.7em; color: #aaa; margin-top: 5px;">SICK × Rp 1.5 juta/pohon</div>
                </div>
                <div class="kpi-card" style="background: rgba(243,156,18,0.3);">
                    <div class="kpi-value" style="color: #f39c12;">Rp {(summaries['AME002']['det_sick'] + summaries['AME004']['det_sick']) * FINANCIAL_PARAMS['cost_sanitasi'] / 1_000_000:.0f} jt</div>
                    <div class="kpi-label">Est. Biaya Sanitasi</div>
                    <div style="font-size: 0.7em; color: #aaa; margin-top: 5px;">SICK × Rp 50rb/pokok</div>
                </div>
                <div class="kpi-card" style="background: rgba(39,174,96,0.3);">
                    <div class="kpi-value" style="color: #27ae60;">Rp {(summaries['AME002']['det_warning'] + summaries['AME004']['det_warning']) * FINANCIAL_PARAMS['cost_proteksi'] / 1_000_000:.0f} jt</div>
                    <div class="kpi-label">Est. Biaya Proteksi</div>
                    <div style="font-size: 0.7em; color: #aaa; margin-top: 5px;">WARNING × Rp 15rb/pokok</div>
                </div>
                <div class="kpi-card" style="background: rgba(155,89,182,0.3);">
                    <div class="kpi-value" style="color: #9b59b6;">Rp {((summaries['AME002']['det_sick'] + summaries['AME004']['det_sick']) * FINANCIAL_PARAMS['valuasi_pohon'] + (summaries['AME002']['det_sick'] + summaries['AME004']['det_sick']) * FINANCIAL_PARAMS['cost_sanitasi'] + (summaries['AME002']['det_warning'] + summaries['AME004']['det_warning']) * FINANCIAL_PARAMS['cost_proteksi']) / 1_000_000_000:.2f} M</div>
                    <div class="kpi-label">Total Exposure</div>
                    <div style="font-size: 0.7em; color: #aaa; margin-top: 5px;">Aset + Treatment</div>
                </div>
            </div>
            <div class="metric-desc" style="margin-top: 15px; border-left: 3px solid #f39c12;">
                <strong>⚠️ Formula Asumsi:</strong> Valuasi = Rp 1.500.000/pohon | Sanitasi = Rp 50.000/pokok | Proteksi = Rp 15.000/pokok<br>
                <em>Nilai riil dapat berbeda berdasarkan tahun tanam, lokasi, dan harga bahan hayati terkini.</em>
            </div>
        </div>
        
        <div class="insights-box">
            <h3>🎯 Top 3 Actionable Insights</h3>
            <ul>
                {"".join(f'<li>• {insight}</li>' for insight in insights)}
            </ul>
        </div>
"""
    
    # Section 2: Data Sources Comparison
    html += f"""
        <div class="section">
            <h2>🔄 Data Sources Comparison</h2>
            <div class="grid-2">
"""
    
    for div_code, div_name in [('AME002', 'AME II'), ('AME004', 'AME IV')]:
        s = summaries[div_code]
        html += f"""
                <div class="stat-box">
                    <h4>{div_name}</h4>
                    <table class="comparison-table">
                        <tr><td>Metric</td><td>Drone</td><td>Ground Truth</td><td>Variance</td></tr>
                        <tr><td>Total Pohon</td><td>{s['drone_total']:,}</td><td>{s['gt_total']:,}</td><td>{s['drone_total'] - s['gt_total']:+,}</td></tr>
                        <tr><td>MATURE/TANAM</td><td>{s['drone_mature']:,}</td><td>-</td><td>-</td></tr>
                        <tr><td>SISIP</td><td>{s['drone_young']:,}</td><td>{s['gt_sisip']:,}</td><td class="{'risk-high' if abs(s['drone_young'] - s['gt_sisip']) > 1000 else ''}">{s['drone_young'] - s['gt_sisip']:+,}</td></tr>
                        <tr><td>MATI</td><td>{s['drone_dead']:,}</td><td>-</td><td>-</td></tr>
                        <tr><td>KOSONG</td><td>{s['drone_empty']:,}</td><td>-</td><td>-</td></tr>
                        <tr><td>Ganoderma</td><td>{s['det_sick']:,}</td><td>{s['gt_gano']:,}</td><td>{s['det_sick'] - s['gt_gano']:+,}</td></tr>
                        <tr><td>SPH (Avg)</td><td>{s['avg_sph_drone']:.0f}</td><td>{s['avg_sph_gt']:.0f}</td><td>{s['avg_sph_drone'] - s['avg_sph_gt']:+.0f}</td></tr>
                    </table>
                </div>
"""
    
    html += """
            </div>
"""
    html += generate_wiwsns_panel("data_sources", summaries)
    html += """
        </div>
"""
    
    # Section 3: Population Segmentation
    html += f"""
        <div class="section">
            <h2>👥 Population Segmentation</h2>
            <div class="grid-2">
                <div class="chart-card">
                    <img src="data:image/png;base64,{charts['pop_ame2']}" alt="AME II Population">
                </div>
                <div class="chart-card">
                    <img src="data:image/png;base64,{charts['pop_ame4']}" alt="AME IV Population">
                </div>
            </div>
"""
    html += generate_wiwsns_panel("population")
    html += """
        </div>
"""
    
    # Section 5: Ganoderma Detection
    html += f"""
        <div class="section">
            <h2>🔬 Ganoderma Detection Analysis</h2>
            <div class="grid-2">
                <div class="chart-card">
                    <img src="data:image/png;base64,{charts['det_ame2']}" alt="AME II Detection">
                </div>
                <div class="chart-card">
                    <img src="data:image/png;base64,{charts['det_ame4']}" alt="AME IV Detection">
                </div>
            </div>
            <div class="grid-2" style="margin-top: 20px;">
"""
    
    for div_code, div_name in [('AME002', 'AME II'), ('AME004', 'AME IV')]:
        s = summaries[div_code]
        total_det = s['det_sehat'] + s['det_warning'] + s['det_sick']
        html += f"""
                <div class="stat-box">
                    <h4>{div_name} - Ground Truth Comparison</h4>
                    <div class="grid-4">
                        <div class="kpi-card" style="padding: 10px;">
                            <div class="kpi-value" style="font-size: 1.3em; color: #e74c3c;">{s['mae']:.2f}%</div>
                            <div class="kpi-label">MAE</div>
                        </div>
                        <div class="kpi-card" style="padding: 10px;">
                            <div class="kpi-value" style="font-size: 1.3em; color: #3498db;">{s['corr']:.3f}</div>
                            <div class="kpi-label">Correlation</div>
                        </div>
                        <div class="kpi-card" style="padding: 10px;">
                            <div class="kpi-value" style="font-size: 1.3em;">{(s['det_warning'] + s['det_sick']) / total_det * 100:.1f}%</div>
                            <div class="kpi-label">Detection Rate</div>
                        </div>
                        <div class="kpi-card" style="padding: 10px;">
                            <div class="kpi-value" style="font-size: 1.3em;">{s['gt_gano'] / s['gt_total'] * 100 if s['gt_total'] > 0 else 0:.1f}%</div>
                            <div class="kpi-label">GT Gano Rate</div>
                        </div>
                    </div>
                </div>
"""
    
    html += """
            </div>
"""
    html += generate_wiwsns_panel("detection", summaries)
    html += """
        </div>
"""
    
    # Section 6: SPH Analysis
    html += f"""
        <div class="section">
            <h2>📈 SPH (Stand Per Hectare) Analysis</h2>
            <div class="grid-2">
                <div class="chart-card">
                    <img src="data:image/png;base64,{charts['sph_ame2']}" alt="AME II SPH">
                </div>
                <div class="chart-card">
                    <img src="data:image/png;base64,{charts['sph_ame4']}" alt="AME IV SPH">
                </div>
            </div>
            <div class="metric-desc">
                <strong>SPH (Stand Per Hectare):</strong> Jumlah pohon per hektar. Scatter plot menunjukkan perbandingan SPH dari drone vs ground truth.<br>
                <strong>Diagonal line:</strong> Garis perfect match. Titik yang jauh dari garis menunjukkan variance tinggi yang perlu diinvestigasi.
            </div>
"""
    html += generate_wiwsns_panel("sph", summaries)
    html += """
        </div>
"""
    
    # Section 7: Ghost Tree Audit
    ghost_ame2 = summaries['AME002']['total_ghost_trees']
    ghost_ame4 = summaries['AME004']['total_ghost_trees']
    
    html += f"""
        <div class="section">
            <h2>👻 Ghost Tree Audit</h2>
            <p style="margin-bottom: 20px; color: #a0a0a0;">Identifikasi pohon "hilang" atau "phantom" antara data drone dan ground truth.</p>
            <div class="grid-2">
                <div class="stat-box">
                    <h4>AME II</h4>
                    <div class="kpi-value" style="color: {'#e74c3c' if ghost_ame2 < 0 else '#f39c12'}; font-size: 2em;">{ghost_ame2:+,}</div>
                    <div class="kpi-label">{'Under-count (Missing Trees)' if ghost_ame2 < 0 else 'Over-count (Ghost Trees)'}</div>
                    <div class="metric-desc">
                        {'⚠️ Drone mendeteksi LEBIH SEDIKIT pohon. Kemungkinan: cakupan drone tidak lengkap atau pohon tidak terdeteksi.' if ghost_ame2 < 0 else '⚠️ Drone mendeteksi LEBIH BANYAK pohon. Kemungkinan: false detection atau GT tidak update.'}
                    </div>
                </div>
                <div class="stat-box">
                    <h4>AME IV</h4>
                    <div class="kpi-value" style="color: {'#e74c3c' if ghost_ame4 < 0 else '#f39c12'}; font-size: 2em;">{ghost_ame4:+,}</div>
                    <div class="kpi-label">{'Under-count (Missing Trees)' if ghost_ame4 < 0 else 'Over-count (Ghost Trees)'}</div>
                    <div class="metric-desc">
                        {'⚠️ Drone mendeteksi LEBIH SEDIKIT pohon. Kemungkinan: cakupan drone tidak lengkap atau pohon tidak terdeteksi.' if ghost_ame4 < 0 else '⚠️ Drone mendeteksi LEBIH BANYAK pohon. Kemungkinan: false detection atau GT tidak update.'}
                    </div>
                </div>
            </div>
"""
    html += generate_wiwsns_panel("ghost_tree", summaries)
    html += """
        </div>
"""
    
    # Section 8: Age Analysis
    html += f"""
        <div class="section">
            <h2>📅 Age Analysis (Tahun Tanam)</h2>
            <div class="chart-card">
                <img src="data:image/png;base64,{charts['age_ganoderma']}" alt="Age vs Ganoderma">
            </div>
            <div class="metric-desc">
                <strong>Insight:</strong> Grafik menunjukkan hubungan antara umur tanaman dengan tingkat Ganoderma. Tanaman lebih tua cenderung memiliki tingkat serangan lebih tinggi karena exposure time yang lebih lama.
            </div>
"""
    html += generate_wiwsns_panel("age_analysis")
    html += """
        </div>
"""
    
    # Section 9: Risk Scoring
    html += f"""
        <div class="section">
            <h2>⚠️ Risk Scoring & Prioritization</h2>
            <p style="margin-bottom: 15px; color: #a0a0a0;">Formula: Risk Score = (Sick % × 0.4) + (Cincin API × 0.3) + (GT Gano % × 0.3)</p>
            <div class="chart-card">
                <img src="data:image/png;base64,{charts['risk_chart']}" alt="Risk Chart">
            </div>
            <div class="metric-desc">
                <strong>Prioritas Survey:</strong> Blok dengan Risk Score tinggi perlu diprioritaskan untuk verifikasi lapangan dan penanganan Ganoderma.
            </div>
"""
    html += generate_wiwsns_panel("risk_scoring")
    html += """
        </div>
"""
    
    # Section 10: Block Drilldown
    df_sorted = df_metrics.sort_values('risk_score', ascending=False)
    
    html += f"""
        <div class="section">
            <h2>📋 Block-Level Drilldown</h2>
            <p style="margin-bottom: 15px; color: #a0a0a0;">Sorted by Risk Score (highest first). Total blocks: {len(df_metrics)}</p>
            <div class="scrollable">
            <table>
                <thead>
                    <tr>
                        <th>Divisi</th>
                        <th>Blok</th>
                        <th>Drone Total</th>
                        <th>GT Total</th>
                        <th>Ghost</th>
                        <th>Sehat</th>
                        <th>Warning</th>
                        <th>Sick</th>
                        <th>🔥Cincin</th>
                        <th>Algo %</th>
                        <th>GT Gano %</th>
                        <th>Risk Score</th>
                    </tr>
                </thead>
                <tbody>
"""
    
    for _, row in df_sorted.head(50).iterrows():
        risk_class = 'risk-high' if row['risk_score'] > 50 else 'risk-medium' if row['risk_score'] > 25 else 'risk-low'
        html += f"""
                    <tr>
                        <td>{row['divisi']}</td>
                        <td>{row['blok']}</td>
                        <td>{row['drone_total']:,}</td>
                        <td>{row['gt_total']:,}</td>
                        <td class="{'risk-high' if abs(row['ghost_trees']) > 500 else ''}">{row['ghost_trees']:+,}</td>
                        <td style="color:#27ae60;">{row['sehat']:,}</td>
                        <td style="color:#f39c12;">{row['warning']}</td>
                        <td style="color:#e74c3c;">{row['sick']}</td>
                        <td style="color:#e74c3c;">{row['cincin_api']}</td>
                        <td>{row['detection_pct']:.1f}%</td>
                        <td>{row['gt_gano_pct']:.1f}%</td>
                        <td class="{risk_class}">{row['risk_score']:.1f}</td>
                    </tr>
"""
    
    html += """
                </tbody>
            </table>
            </div>
"""
    html += generate_wiwsns_panel("drilldown")
    html += """
        </div>
"""
    
    # Section 11: Insights & Recommendations
    html += f"""
        <div class="section">
            <h2>💡 Insights & Recommendations</h2>
            <div class="grid-2">
                <div class="stat-box">
                    <h4 style="color: #e74c3c;">🔴 Critical Issues</h4>
                    <ul style="list-style: disc; margin-left: 20px; line-height: 1.8;">
                        <li>SISIP mismatch besar: Drone {summaries['AME002']['drone_young'] + summaries['AME004']['drone_young']:,} vs GT {summaries['AME002']['gt_sisip'] + summaries['AME004']['gt_sisip']:,}</li>
                        <li>Data quality {data_quality:.0f}% - {'Perlu investigasi' if data_quality < 80 else 'Acceptable'}</li>
                        <li>Total Cincin Api: {summaries['AME002']['det_cincin'] + summaries['AME004']['det_cincin']} clusters perlu penanganan</li>
                    </ul>
                </div>
                <div class="stat-box">
                    <h4 style="color: #2ecc71;">✅ Recommended Actions</h4>
                    <ul style="list-style: disc; margin-left: 20px; line-height: 1.8;">
                        <li>Prioritaskan survey lapangan pada {min(10, len(df_metrics.nlargest(10, 'risk_score')))} blok high-risk</li>
                        <li>Verifikasi label SISIP di data drone untuk AME II</li>
                        <li>Update ground truth dengan data drone terbaru</li>
                        <li>Investigasi blok dengan ghost tree &gt; 500</li>
                    </ul>
                </div>
            </div>
            <div class="stat-box" style="margin-top: 15px;">
                <h4 style="color: #3498db;">📊 Survey Workload Estimation</h4>
                <p>Total pohon SICK + WARNING yang perlu diverifikasi:</p>
                <p style="font-size: 1.5em; margin-top: 10px;">
                    <strong>{summaries['AME002']['det_sick'] + summaries['AME002']['det_warning'] + summaries['AME004']['det_sick'] + summaries['AME004']['det_warning']:,}</strong> pohon
                </p>
            </div>
        </div>
"""
    
    # Footer with Disclaimer (from Consultant's Doc)
    html += f"""
        <!-- DISCLAIMER -->
        <div style="background: rgba(243,156,18,0.1); border: 1px solid #f39c12; border-radius: 12px; padding: 20px; margin-top: 25px;">
            <h4 style="color: #f39c12; margin-bottom: 10px;">⚠️ Disclaimer</h4>
            <p style="font-size: 0.9em; line-height: 1.6; color: #ccc;">{DISCLAIMER_TEXT}</p>
        </div>
        
        <div style="text-align: center; padding: 20px; color: #666; font-size: 0.9em;">
            <p>🌴 POAC Simulation Engine v3.3 | Comprehensive Ganoderma Analysis Dashboard</p>
            <p>Data sources: Drone NDRE + Ground Truth Census</p>
            <p style="margin-top: 10px;">Framework: Value-Driven Analytics (WIWSNS) | Powered by Consultant's Gap Analysis</p>
        </div>
    </div>
</body>
</html>
"""
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"Dashboard saved: {output_path}")


# =============================================================================
# MAIN
# =============================================================================

def main():
    print("="*70)
    print("COMPREHENSIVE GANODERMA ANALYSIS DASHBOARD")
    print("="*70)
    
    output_dir = script_dir / "data" / "output" / "comprehensive_dashboard"
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "data").mkdir(exist_ok=True)
    
    # Load data
    df_ame2, df_ame4, df_gt = load_all_data()
    
    # Prepare GT
    df_gt['blok_norm'] = df_gt['BLOK'].apply(normalize_block)
    df_gt_ame2 = df_gt[df_gt['DIVISI'] == 'AME002'].copy()
    df_gt_ame4 = df_gt[df_gt['DIVISI'] == 'AME004'].copy()
    
    # Run detection
    print("[3/10] Running detection algorithm (Option A)...")
    df_det_ame2 = run_detection(df_ame2, 'AME002')
    df_det_ame4 = run_detection(df_ame4, 'AME004')
    
    # Calculate metrics
    print("[4/10] Calculating block metrics...")
    metrics_ame2 = calculate_block_metrics(df_ame2, df_det_ame2, df_gt_ame2, 'AME002')
    metrics_ame4 = calculate_block_metrics(df_ame4, df_det_ame4, df_gt_ame4, 'AME004')
    df_metrics = pd.concat([metrics_ame2, metrics_ame4], ignore_index=True)
    
    # Calculate summaries
    print("[5/10] Calculating summary metrics...")
    summaries = {
        'AME002': calculate_summary_metrics(df_metrics, 'AME002'),
        'AME004': calculate_summary_metrics(df_metrics, 'AME004')
    }
    
    # Generate charts
    print("[6/10] Generating charts...")
    charts = {
        'pop_ame2': generate_population_chart(summaries['AME002'], 'AME II'),
        'pop_ame4': generate_population_chart(summaries['AME004'], 'AME IV'),
        'det_ame2': generate_detection_chart(summaries['AME002'], 'AME II'),
        'det_ame4': generate_detection_chart(summaries['AME004'], 'AME IV'),
        'sph_ame2': generate_sph_scatter(df_metrics, 'AME002'),
        'sph_ame4': generate_sph_scatter(df_metrics, 'AME004'),
        'age_ganoderma': generate_age_ganoderma_chart(df_metrics),
        'risk_chart': generate_risk_chart(df_metrics)
    }
    
    # Generate HTML
    print("[7/10] Generating HTML dashboard...")
    generate_html_dashboard(summaries, df_metrics, charts, output_dir / "executive_dashboard.html")
    
    # Export CSVs
    print("[8/10] Exporting CSV files...")
    df_metrics.to_csv(output_dir / "data" / "block_drilldown.csv", index=False)
    
    # Ghost tree audit
    ghost_audit = df_metrics[['divisi', 'blok', 'drone_total', 'gt_total', 'ghost_trees', 'ghost_pct']].copy()
    ghost_audit.to_csv(output_dir / "data" / "ghost_tree_audit.csv", index=False)
    
    # SPH analysis
    sph_analysis = df_metrics[['divisi', 'blok', 'sph_drone', 'sph_gt', 'sph_variance', 'sph_variance_pct', 'luas']].copy()
    sph_analysis.to_csv(output_dir / "data" / "sph_analysis.csv", index=False)
    
    # Risk scores
    risk_scores = df_metrics[['divisi', 'blok', 'sick', 'cincin_api', 'gt_gano_pct', 'risk_score']].copy()
    risk_scores = risk_scores.sort_values('risk_score', ascending=False)
    risk_scores.to_csv(output_dir / "data" / "risk_scores.csv", index=False)
    
    # Summary JSON
    print("[9/10] Saving summary...")
    
    # Convert numpy types to native Python types for JSON serialization
    def convert_to_native(obj):
        if isinstance(obj, dict):
            return {k: convert_to_native(v) for k, v in obj.items()}
        elif isinstance(obj, (np.integer, np.int64)):
            return int(obj)
        elif isinstance(obj, (np.floating, np.float64)):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif pd.isna(obj):
            return None
        else:
            return obj
    
    summaries_native = convert_to_native(summaries)
    with open(output_dir / "data" / "executive_summary.json", 'w') as f:
        json.dump(summaries_native, f, indent=2)
    
    print("[10/10] Complete!")
    print(f"\nOutput saved to: {output_dir}")
    
    # Open dashboard
    import os
    os.startfile(output_dir / "executive_dashboard.html")
    
    return summaries, df_metrics


if __name__ == "__main__":
    main()
