"""
POAC v3.3 - Report Generator
Generate README.md dan HTML Report untuk hasil Algoritma Cincin Api

Fitur:
1. README.md - Panduan interpretasi dan deskripsi file
2. HTML Report - Laporan interaktif dengan gambar embedded
3. Legend/Footer di gambar visualisasi
"""

import pandas as pd
from pathlib import Path
from datetime import datetime
import base64
import logging
import json

logger = logging.getLogger(__name__)

# =============================================================================
# TEMPLATE CONSTANTS
# =============================================================================

STATUS_DESCRIPTIONS = {
    "MERAH": {
        "label": "MERAH (KLUSTER AKTIF)",
        "color": "#e74c3c",
        "emoji": "🔴",
        "meaning": "Pohon terdeteksi dalam kluster aktif Ganoderma",
        "criteria": "Persentil ≤ threshold DAN ≥3 tetangga sakit",
        "action": "**PRIORITAS UTAMA** - Segera lakukan sanitasi sesuai SOP",
        "urgency": "TINGGI"
    },
    "KUNING": {
        "label": "KUNING (RISIKO TINGGI)",
        "color": "#f1c40f",
        "emoji": "🟡",
        "meaning": "Pohon berisiko tinggi, berpotensi menjadi kluster",
        "criteria": "Persentil ≤ threshold DAN 1-2 tetangga sakit",
        "action": "Monitoring ketat, periksa perkembangan setiap 2 minggu",
        "urgency": "SEDANG"
    },
    "ORANYE": {
        "label": "ORANYE (NOISE/KENTOSAN)",
        "color": "#e67e22",
        "emoji": "🟠",
        "meaning": "Pohon suspect tapi terisolasi (tidak membentuk kluster)",
        "criteria": "Persentil ≤ threshold DAN 0 tetangga sakit",
        "action": "Investigasi lapangan untuk konfirmasi kondisi",
        "urgency": "RENDAH"
    },
    "HIJAU": {
        "label": "HIJAU (SEHAT)",
        "color": "#27ae60",
        "emoji": "🟢",
        "meaning": "Pohon dalam kondisi sehat/normal",
        "criteria": "Persentil > threshold",
        "action": "Tidak perlu tindakan, monitoring rutin",
        "urgency": "TIDAK ADA"
    }
}

FILE_DESCRIPTIONS = {
    "dashboard_main.png": {
        "title": "Dashboard Utama",
        "description": "Ringkasan visual hasil analisis dengan 4 panel: distribusi status, top blok terparah, distribusi kepadatan kluster, dan statistik ringkasan."
    },
    "dashboard_block_heatmap.png": {
        "title": "Heatmap per Blok",
        "description": "Perbandingan jumlah pohon MERAH, KUNING, dan ORANYE untuk setiap blok. Blok diurutkan dari yang terparah."
    },
    "dashboard_elbow.png": {
        "title": "Elbow Method Chart",
        "description": "Visualisasi proses auto-tuning untuk menentukan threshold optimal. Titik merah menunjukkan threshold terpilih."
    },
    "hasil_klasifikasi_lengkap.csv": {
        "title": "Data Klasifikasi Lengkap",
        "description": "File CSV berisi semua data pohon dengan status risiko, skor kepadatan, dan jumlah tetangga sakit."
    },
    "target_prioritas.csv": {
        "title": "Target Prioritas",
        "description": "Daftar 1000 pohon prioritas tertinggi untuk intervensi, diurutkan berdasarkan status dan kepadatan kluster."
    },
    "ringkasan_per_blok.csv": {
        "title": "Ringkasan per Blok",
        "description": "Agregasi jumlah pohon per status untuk setiap blok."
    },
    "laporan_mandor.txt": {
        "title": "Laporan untuk Mandor",
        "description": "Laporan teks sederhana berisi daftar target dan instruksi untuk mandor di lapangan."
    },
    "run_config.json": {
        "title": "Konfigurasi Run",
        "description": "File JSON berisi parameter yang digunakan dalam analisis ini. Berguna untuk reproduksi hasil."
    }
}


def generate_readme(
    output_dir: Path,
    metadata: dict,
    config: dict = None,
    preset: str = None
) -> str:
    """
    Generate README.md untuk folder output.
    
    Args:
        output_dir: Path folder output
        metadata: Metadata hasil analisis
        config: Konfigurasi yang digunakan
        preset: Nama preset yang digunakan
        
    Returns:
        Path ke file README.md yang dibuat
    """
    output_dir = Path(output_dir)
    readme_path = output_dir / "README.md"
    
    # Get list of files in directory
    files_in_dir = [f.name for f in output_dir.iterdir() if f.is_file()]
    
    # Build README content
    content = f"""# 📊 Hasil Analisis Algoritma Cincin Api

**Tanggal Generate:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}  
**Preset:** {preset or 'standar'}  
**Folder:** `{output_dir.name}`

---

## 🎯 Ringkasan Hasil

| Metrik | Nilai |
|--------|-------|
| **Threshold Optimal** | {metadata.get('optimal_threshold_pct', 'N/A')} |
| **Total Pohon** | {metadata.get('total_trees', 0):,} |
| 🔴 MERAH (Kluster Aktif) | {metadata.get('merah_count', 0):,} |
| 🟡 KUNING (Risiko Tinggi) | {metadata.get('kuning_count', 0):,} |
| 🟠 ORANYE (Noise) | {metadata.get('oranye_count', 0):,} |
| 🟢 HIJAU (Sehat) | {metadata.get('hijau_count', 0):,} |
| **Total Target Intervensi** | {metadata.get('merah_count', 0) + metadata.get('kuning_count', 0):,} |

---

## 🎨 Panduan Interpretasi Warna

"""
    
    # Add status descriptions
    for status_key, status_info in STATUS_DESCRIPTIONS.items():
        content += f"""### {status_info['emoji']} {status_key} - {status_info['label']}

- **Arti:** {status_info['meaning']}
- **Kriteria:** {status_info['criteria']}
- **Tindakan:** {status_info['action']}
- **Urgensi:** {status_info['urgency']}

"""
    
    # Add file descriptions
    content += """---

## 📁 Deskripsi File Output

| File | Deskripsi |
|------|-----------|
"""
    
    for filename in sorted(files_in_dir):
        if filename in FILE_DESCRIPTIONS:
            desc = FILE_DESCRIPTIONS[filename]
            content += f"| `{filename}` | **{desc['title']}** - {desc['description']} |\n"
        elif filename.startswith("top10_"):
            blok_name = filename.replace("top10_", "").replace("_blok_", " - Blok ").replace(".png", "")
            content += f"| `{filename}` | **Detail Blok #{blok_name}** - Visualisasi detail pohon dalam blok terparah |\n"
        elif filename != "README.md" and filename != "report.html":
            content += f"| `{filename}` | File output tambahan |\n"
    
    # Add configuration section
    content += f"""
---

## ⚙️ Konfigurasi yang Digunakan

```json
{json.dumps(config or {}, indent=2, default=str)}
```

---

## 📋 Instruksi untuk Mandor

### Prioritas Kerja:
1. **UTAMA:** Fokus pada pohon 🔴 MERAH (Kluster Aktif)
2. Lakukan validasi lapangan untuk konfirmasi serangan Ganoderma
3. Jika terkonfirmasi, lakukan sanitasi sesuai SOP perusahaan
4. Pohon 🟡 KUNING perlu monitoring berkala (setiap 2 minggu)
5. Pohon 🟠 ORANYE bisa diabaikan kecuali ada indikasi lain di lapangan

### Tips Membaca Visualisasi:
- **Titik besar** = Pohon dengan banyak tetangga sakit (kluster padat)
- **Titik kecil** = Pohon dengan sedikit/tanpa tetangga sakit
- **Warna merah** = Prioritas tertinggi untuk sanitasi
- **Posisi X-Y** = Koordinat baris dan pokok di lapangan

---

## 🔄 Reproduksi Hasil

Untuk menghasilkan analisis yang sama, jalankan:

```bash
python run_cincin_api.py --preset {preset or 'standar'}
```

Atau gunakan konfigurasi manual dari `run_config.json`.

---

*Generated by POAC v3.3 - Algoritma Cincin Api*
"""
    
    # Write README
    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    logger.info(f"README.md generated: {readme_path}")
    return str(readme_path)


def generate_html_report(
    output_dir: Path,
    df_classified: pd.DataFrame,
    metadata: dict,
    config: dict = None,
    preset: str = None
) -> str:
    """
    Generate HTML Report interaktif dengan gambar embedded.
    
    Args:
        output_dir: Path folder output
        df_classified: DataFrame hasil klasifikasi
        metadata: Metadata hasil analisis
        config: Konfigurasi yang digunakan
        preset: Nama preset yang digunakan
        
    Returns:
        Path ke file report.html yang dibuat
    """
    output_dir = Path(output_dir)
    html_path = output_dir / "report.html"
    
    # Collect all PNG files
    png_files = sorted([f for f in output_dir.iterdir() if f.suffix == '.png'])
    
    # Build HTML content
    html_content = f"""<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>POAC v3.3 - Laporan Algoritma Cincin Api</title>
    <style>
        :root {{
            --merah: #e74c3c;
            --kuning: #f1c40f;
            --oranye: #e67e22;
            --hijau: #27ae60;
            --biru: #3498db;
            --dark: #2c3e50;
            --light: #ecf0f1;
        }}
        
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }}
        
        header {{
            background: var(--dark);
            color: white;
            padding: 30px;
            text-align: center;
        }}
        
        header h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
        }}
        
        header .subtitle {{
            opacity: 0.8;
            font-size: 1.1em;
        }}
        
        .meta-info {{
            display: flex;
            justify-content: center;
            gap: 30px;
            margin-top: 20px;
            flex-wrap: wrap;
        }}
        
        .meta-item {{
            background: rgba(255,255,255,0.1);
            padding: 10px 20px;
            border-radius: 20px;
        }}
        
        main {{
            padding: 30px;
        }}
        
        .section {{
            margin-bottom: 40px;
        }}
        
        .section h2 {{
            color: var(--dark);
            border-bottom: 3px solid var(--biru);
            padding-bottom: 10px;
            margin-bottom: 20px;
            font-size: 1.8em;
        }}
        
        /* Summary Cards */
        .summary-cards {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        
        .card {{
            padding: 25px;
            border-radius: 15px;
            color: white;
            text-align: center;
            transition: transform 0.3s ease;
        }}
        
        .card:hover {{
            transform: translateY(-5px);
        }}
        
        .card.merah {{ background: linear-gradient(135deg, var(--merah), #c0392b); }}
        .card.kuning {{ background: linear-gradient(135deg, var(--kuning), #f39c12); color: var(--dark); }}
        .card.oranye {{ background: linear-gradient(135deg, var(--oranye), #d35400); }}
        .card.hijau {{ background: linear-gradient(135deg, var(--hijau), #27ae60); }}
        .card.biru {{ background: linear-gradient(135deg, var(--biru), #2980b9); }}
        
        .card .number {{
            font-size: 2.5em;
            font-weight: bold;
        }}
        
        .card .label {{
            font-size: 0.9em;
            opacity: 0.9;
            margin-top: 5px;
        }}
        
        /* Status Guide */
        .status-guide {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 20px;
        }}
        
        .status-item {{
            border: 2px solid #eee;
            border-radius: 15px;
            padding: 20px;
            transition: all 0.3s ease;
        }}
        
        .status-item:hover {{
            border-color: var(--biru);
            box-shadow: 0 5px 20px rgba(0,0,0,0.1);
        }}
        
        .status-item h3 {{
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 15px;
        }}
        
        .status-item .color-dot {{
            width: 20px;
            height: 20px;
            border-radius: 50%;
        }}
        
        .status-item .criteria {{
            background: var(--light);
            padding: 10px;
            border-radius: 8px;
            font-size: 0.9em;
            margin: 10px 0;
        }}
        
        .status-item .action {{
            color: var(--dark);
            font-weight: 500;
        }}
        
        /* Image Gallery */
        .image-gallery {{
            display: grid;
            gap: 30px;
        }}
        
        .image-container {{
            background: var(--light);
            border-radius: 15px;
            overflow: hidden;
        }}
        
        .image-container h3 {{
            background: var(--dark);
            color: white;
            padding: 15px 20px;
            font-size: 1.1em;
        }}
        
        .image-container p {{
            padding: 15px 20px;
            color: #666;
            font-size: 0.95em;
            border-bottom: 1px solid #ddd;
        }}
        
        .image-container img {{
            width: 100%;
            height: auto;
            display: block;
            cursor: zoom-in;
            transition: transform 0.3s ease;
        }}
        
        .image-container img:hover {{
            transform: scale(1.02);
        }}
        
        /* Top 10 Section */
        .top10-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 20px;
        }}
        
        .top10-item {{
            border: 2px solid #eee;
            border-radius: 15px;
            overflow: hidden;
        }}
        
        .top10-item h4 {{
            background: var(--merah);
            color: white;
            padding: 10px 15px;
        }}
        
        .top10-item img {{
            width: 100%;
            height: auto;
        }}
        
        /* Footer */
        footer {{
            background: var(--dark);
            color: white;
            text-align: center;
            padding: 20px;
            font-size: 0.9em;
        }}
        
        /* Modal for zoom */
        .modal {{
            display: none;
            position: fixed;
            z-index: 1000;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.9);
            cursor: zoom-out;
        }}
        
        .modal img {{
            max-width: 95%;
            max-height: 95%;
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
        }}
        
        .modal-close {{
            position: absolute;
            top: 20px;
            right: 30px;
            color: white;
            font-size: 40px;
            cursor: pointer;
        }}
        
        @media (max-width: 768px) {{
            header h1 {{ font-size: 1.8em; }}
            .meta-info {{ flex-direction: column; gap: 10px; }}
            .top10-grid {{ grid-template-columns: 1fr; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🔥 POAC v3.3 - Algoritma Cincin Api</h1>
            <p class="subtitle">Laporan Deteksi Kluster Ganoderma</p>
            <div class="meta-info">
                <span class="meta-item">📅 {datetime.now().strftime("%Y-%m-%d %H:%M")}</span>
                <span class="meta-item">📋 Preset: {preset or 'standar'}</span>
                <span class="meta-item">🎯 Threshold: {metadata.get('optimal_threshold_pct', 'N/A')}</span>
            </div>
        </header>
        
        <main>
            <!-- Summary Section -->
            <section class="section">
                <h2>📊 Ringkasan Hasil</h2>
                <div class="summary-cards">
                    <div class="card biru">
                        <div class="number">{metadata.get('total_trees', 0):,}</div>
                        <div class="label">Total Pohon</div>
                    </div>
                    <div class="card merah">
                        <div class="number">{metadata.get('merah_count', 0):,}</div>
                        <div class="label">🔴 MERAH (Kluster)</div>
                    </div>
                    <div class="card kuning">
                        <div class="number">{metadata.get('kuning_count', 0):,}</div>
                        <div class="label">🟡 KUNING (Risiko)</div>
                    </div>
                    <div class="card oranye">
                        <div class="number">{metadata.get('oranye_count', 0):,}</div>
                        <div class="label">🟠 ORANYE (Noise)</div>
                    </div>
                    <div class="card hijau">
                        <div class="number">{metadata.get('hijau_count', 0):,}</div>
                        <div class="label">🟢 HIJAU (Sehat)</div>
                    </div>
                </div>
            </section>
            
            <!-- Status Guide Section -->
            <section class="section">
                <h2>🎨 Panduan Interpretasi Warna</h2>
                <div class="status-guide">
"""
    
    # Add status guide items
    for status_key, status_info in STATUS_DESCRIPTIONS.items():
        html_content += f"""
                    <div class="status-item">
                        <h3>
                            <span class="color-dot" style="background: {status_info['color']}"></span>
                            {status_info['emoji']} {status_key}
                        </h3>
                        <p><strong>Arti:</strong> {status_info['meaning']}</p>
                        <div class="criteria"><strong>Kriteria:</strong> {status_info['criteria']}</div>
                        <p class="action"><strong>Tindakan:</strong> {status_info['action']}</p>
                    </div>
"""
    
    html_content += """
                </div>
            </section>
            
            <!-- Main Visualizations -->
            <section class="section">
                <h2>📈 Visualisasi Utama</h2>
                <div class="image-gallery">
"""
    
    # Add main visualizations
    main_images = ['dashboard_main.png', 'dashboard_block_heatmap.png', 'dashboard_elbow.png']
    for img_file in main_images:
        img_path = output_dir / img_file
        if img_path.exists():
            desc = FILE_DESCRIPTIONS.get(img_file, {"title": img_file, "description": ""})
            # Encode image to base64
            with open(img_path, 'rb') as f:
                img_base64 = base64.b64encode(f.read()).decode('utf-8')
            
            html_content += f"""
                    <div class="image-container">
                        <h3>{desc['title']}</h3>
                        <p>{desc['description']}</p>
                        <img src="data:image/png;base64,{img_base64}" alt="{desc['title']}" onclick="openModal(this)">
                    </div>
"""
    
    html_content += """
                </div>
            </section>
            
            <!-- Top 10 Blocks Section -->
            <section class="section">
                <h2>🏆 Top 10 Blok Terparah</h2>
                <p style="margin-bottom: 20px; color: #666;">Klik gambar untuk memperbesar. Blok diurutkan berdasarkan jumlah pohon MERAH (kluster aktif).</p>
                <div class="top10-grid">
"""
    
    # Add Top 10 block images
    top10_images = sorted([f for f in png_files if f.name.startswith('top10_')])
    for img_path in top10_images:
        # Extract rank and block name from filename
        filename = img_path.name
        parts = filename.replace('.png', '').split('_')
        if len(parts) >= 3:
            rank = parts[1]
            blok = parts[-1]
            
            with open(img_path, 'rb') as f:
                img_base64 = base64.b64encode(f.read()).decode('utf-8')
            
            html_content += f"""
                    <div class="top10-item">
                        <h4>#{rank} - Blok {blok}</h4>
                        <img src="data:image/png;base64,{img_base64}" alt="Blok {blok}" onclick="openModal(this)">
                    </div>
"""
    
    html_content += f"""
                </div>
            </section>
            
            <!-- Instructions Section -->
            <section class="section">
                <h2>📋 Instruksi untuk Mandor</h2>
                <div style="background: var(--light); padding: 25px; border-radius: 15px;">
                    <h3 style="color: var(--merah); margin-bottom: 15px;">🎯 Prioritas Kerja:</h3>
                    <ol style="line-height: 2; padding-left: 20px;">
                        <li><strong>UTAMA:</strong> Fokus pada pohon 🔴 MERAH (Kluster Aktif) - Total: <strong>{metadata.get('merah_count', 0):,}</strong> pohon</li>
                        <li>Lakukan validasi lapangan untuk konfirmasi serangan Ganoderma</li>
                        <li>Jika terkonfirmasi, lakukan sanitasi sesuai SOP perusahaan</li>
                        <li>Pohon 🟡 KUNING perlu monitoring berkala (setiap 2 minggu)</li>
                        <li>Pohon 🟠 ORANYE bisa diabaikan kecuali ada indikasi lain di lapangan</li>
                    </ol>
                    
                    <h3 style="color: var(--biru); margin: 25px 0 15px;">💡 Tips Membaca Visualisasi:</h3>
                    <ul style="line-height: 2; padding-left: 20px;">
                        <li><strong>Titik besar</strong> = Pohon dengan banyak tetangga sakit (kluster padat)</li>
                        <li><strong>Titik kecil</strong> = Pohon dengan sedikit/tanpa tetangga sakit</li>
                        <li><strong>Warna merah</strong> = Prioritas tertinggi untuk sanitasi</li>
                        <li><strong>Posisi X-Y</strong> = Koordinat baris dan pokok di lapangan</li>
                    </ul>
                </div>
            </section>
        </main>
        
        <footer>
            <p>Generated by <strong>POAC v3.3 - Algoritma Cincin Api</strong></p>
            <p style="margin-top: 5px; opacity: 0.7;">© 2025 - Precision Oil Palm Agriculture Control</p>
        </footer>
    </div>
    
    <!-- Modal for image zoom -->
    <div id="imageModal" class="modal" onclick="closeModal()">
        <span class="modal-close">&times;</span>
        <img id="modalImage" src="" alt="Zoomed Image">
    </div>
    
    <script>
        function openModal(img) {{
            document.getElementById('imageModal').style.display = 'block';
            document.getElementById('modalImage').src = img.src;
        }}
        
        function closeModal() {{
            document.getElementById('imageModal').style.display = 'none';
        }}
        
        // Close modal on Escape key
        document.addEventListener('keydown', function(e) {{
            if (e.key === 'Escape') closeModal();
        }});
    </script>
</body>
</html>
"""
    
    # Write HTML file
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    logger.info(f"HTML Report generated: {html_path}")
    return str(html_path)


def add_legend_to_figure(fig, metadata: dict, position: str = 'bottom'):
    """
    Menambahkan legend/footer informatif ke figure matplotlib.
    
    Args:
        fig: matplotlib Figure object
        metadata: Metadata hasil analisis
        position: 'bottom' atau 'right'
    """
    legend_text = (
        f"PANDUAN WARNA: 🔴 MERAH = Kluster Aktif (Sanitasi) | "
        f"🟡 KUNING = Risiko Tinggi (Monitoring) | "
        f"🟠 ORANYE = Noise (Investigasi) | "
        f"🟢 HIJAU = Sehat\n"
        f"Threshold: {metadata.get('optimal_threshold_pct', 'N/A')} | "
        f"Total: {metadata.get('total_trees', 0):,} pohon | "
        f"Target Intervensi: {metadata.get('merah_count', 0) + metadata.get('kuning_count', 0):,} pohon"
    )
    
    if position == 'bottom':
        fig.text(0.5, 0.01, legend_text, ha='center', va='bottom', 
                fontsize=9, style='italic',
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
    
    return fig


def get_interpretation_text(status: str) -> str:
    """
    Mendapatkan teks interpretasi untuk status tertentu.
    """
    if status in STATUS_DESCRIPTIONS:
        info = STATUS_DESCRIPTIONS[status]
        return f"{info['emoji']} {info['meaning']} - {info['action']}"
    return ""
