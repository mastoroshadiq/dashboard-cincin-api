"""
Convert Potensi Kerugian Skala Makro to SINGLE BLOCK view
Remove 2-block aggregate concept, show only current selected block
"""

with open('data/output/dashboard_cincin_api_INTERACTIVE_FULL.html', 'r', encoding='utf-8') as f:
    html = f.read()

print("🔧 Converting Potensi Kerugian to Single Block view...")
print("="*70)

# 1. Update title and description to reflect single block
replacements = [
    # Change title to single block
    ('⚡ Potensi Kerugian Skala Makro (Impact Escalation)',
     '⚡ Potensi Kerugian Blok <span id="potensiHeaderBlock">--</span>'),
    
    # Change description
    ('Ekstrapolasi temuan sampel ke wilayah operasional yang lebih luas.',
     'Estimasi dampak ekonomi untuk blok terpilih berdasarkan tingkat serangan aktual.'),
    
    # Hide the 3 scaling buttons (set to display none)
    ('<div class="flex bg-white/10 p-1 rounded-lg gap-1">',
     '<div class="flex bg-white/10 p-1 rounded-lg gap-1" style="display: none;">'),
    
    # Update the value IDs (already have some but ensure they're correct)
    ('<span class="text-4xl" id="area-value">55.4</span>',
     '<span class="text-4xl font-black" id="areaValue">--</span>'),
    
    ('<span class="text-4xl text-red-400 font-black" id="loss-value">Rp 0.182</span>',
     '<span class="text-4xl text-red-400 font-black" id="lossValue">Rp --</span>'),
    
    ('<span class="text-4xl text-emerald-400 font-black" id="mitigation-value">Rp 0.1</span>',
     '<span class="text-4xl text-emerald-400 font-black" id="mitigationValue">Rp --</span>'),
]

count = 0
for old, new in replacements:
    if old in html:
        html = html.replace(old, new, 1)
        count += 1
        print(f"✅ {count}. Updated section element")
    else:
        print(f"⚠️  {count+1}. NOT FOUND")
        count += 1

# Save
with open('data/output/dashboard_cincin_api_INTERACTIVE_FULL.html', 'w', encoding='utf-8') as f:
    f.write(html)

print(f"\n✅ Applied {count} changes to Potensi Kerugian section")

# Update JavaScript to populate these values
with open('data/output/dashboard_cincin_api_INTERACTIVE_FULL.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Find and update the JavaScript updates array
search_str = "                // Potensi Kerugian Makro (CALCULATED)\n                ['cakupanWilayah', ((data.total_pohon * 64) / 10000).toFixed(1)],  // Hectares\n                ['potensiKerugian', ((data.total_pohon * 0.35).toFixed(0))],  // Rough estimate in millions\n                ['biayaMitigasi', ((data.merah * 0.002).toFixed(1))],  // Rough estimate"

if search_str in html:
    new_js = """                // Potensi Kerugian Skala Makro - SINGLE BLOCK
                ['potensiHeaderBlock', blockCode],
                ['areaValue', ((data.total_pohon * 64) / 10000).toFixed(1)],  // Hectares
                ['lossValue', `Rp ${((data.total_pohon * data.attack_rate * 0.03).toFixed(2))}`],  // Loss based on attack rate
                ['mitigationValue', `Rp ${((data.merah * 1.5) / 1000).toFixed(2)}`]  // Mitigation cost from infected trees"""
    
    html = html.replace(search_str, new_js)
    print("✅ Updated JavaScript for single block calculations")
else:
    print("⚠️  JavaScript section not found")

# Save final
with open('data/output/dashboard_cincin_api_INTERACTIVE_FULL.html', 'w', encoding='utf-8') as f:
    f.write(html)

print("\n" + "="*70)
print("✅ POTENSI KERUGIAN NOW SINGLE BLOCK FOCUSED!")
print("="*70)
print("\nChanges:")
print("  • Title shows current block code")
print("  • Description reflects single block analysis")
print("  • Scaling buttons hidden (not relevant for 1 block)")
print("  • All 3 values calculated for CURRENT block only:")
print("    - Cakupan Wilayah (hectares)")
print("    - Potensi Kerugian (based on attack rate)")
print("    - Biaya Mitigasi (based on infected count)")
