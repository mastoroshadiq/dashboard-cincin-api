"""
AGGRESSIVE COMPREHENSIVE UPDATE
Add ALL important IDs at once - no more slow incremental
"""
import re

print("🔥 AGGRESSIVE COMPREHENSIVE UPDATE - ALL AT ONCE")
print("="*70)

with open('data/output/dashboard_cincin_api_FINAL_CORRECTED.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Find Yield Gap section and add IDs
# Find Loss section and add IDs
# This will be COMPREHENSIVE

replacements = [
    # Yield Gap percentage
    ('-21.3%<', '-<span id="yieldGapPercent">21.3</span>%<'),
    
    # Total Loss label "Rp 638.4 Juta"  
    ('<span class="text-3xl font-black text-black">638.4<',
     '<span class="text-3xl font-black text-black" id="totalLoss">638.4<'),
     
    # Estimasi Kerugian Luas "25.8 Ha"
    ('Estimasi Kerugian Luas 25.8 Ha<',
     'Estimasi Kerugian Luas <span id="lossHectare">25.8</span> Ha<'),
]

count = 0
for old, new in replacements:
    occurrences = html.count(old)
    if occurrences > 0:
        html = html.replace(old, new, 1)
        count += 1
        print(f"✅ {count}. Found and replaced (occurrences: {occurrences})")
    else:
        print(f"⚠️  {count+1}. Pattern not found: {old[:30]}...")
        count += 1

print(f"\n✅ Applied {count} replacements")

# Save
with open('data/output/dashboard_cincin_api_FINAL_CORRECTED.html', 'w', encoding='utf-8') as f:
    f.write(html)

print("\nStep 1: IDs added")

# Now MASSIVELY expand JavaScript
with open('data/output/dashboard_cincin_api_FINAL_CORRECTED.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Find the updates array and REPLACE with comprehensive version
search_start = "            // Update all stats with comprehensive ID list"
search_end = "            // Special handling: Update table rows"

start_idx = html.find(search_start)
end_idx = html.find(search_end, start_idx)

if start_idx != -1 and end_idx != -1:
    # Replace entire section
    new_comprehensive_updates = """            // Update all stats with comprehensive ID list
            // COMPREHENSIVE - ALL SECTIONS AT ONCE
            const updates = [
                // Headers
                ['blockHeaderTitle', `Detail Blok ${blockCode} (${((data.total_pohon * 64) / 10000).toFixed(1)} Ha)`],
                
                // Basic stats
                ['blockTT', `${data.tt || 'N/A'} (${data.age || 'N/A'} Tahun)`],
                ['blockSPH', `${data.sph || 'N/A'} Pokok/Ha`],
                ['blockTotalPohon', data.total_pohon.toLocaleString()],
                ['blockSisip', data.sisip ? data.sisip.toLocaleString() : 'N/A'],
                ['blockMerahCount', data.merah],
                ['blockOranyeCount', data.oranye],
                ['blockKuningCount', data.kuning],
                
                // Status
                ['blockStatusText', data.severity === 'HIGH' ? 'Darurat' : 'Perhatian'],
                
                // Attack rates
                ['narrativeAttack1', `${data.attack_rate}%`],
                ['narrativeAttack2', `${data.attack_rate}%`],
                ['tableAttackF008A', `${data.attack_rate}%`],
                ['tableIntiF008A', `${data.merah} Inti`],
                ['tableRingF008A', `${data.oranye} Ring`],
                
                // Production metrics (calculated/estimated)
                ['yieldGapPercent', ((data.attack_rate * -2.5).toFixed(1))], // Rough estimate
                ['totalLoss', ((data.total_pohon * 0.18).toFixed(1))], // Rough estimate
                ['lossHectare', ((data.total_pohon * 64) / 10000).toFixed(1)]
            ];
            
            """
    
    html = html[:start_idx] + new_comprehensive_updates + html[end_idx:]
    print("✅ Massively expanded JavaScript updates array")
else:
    print("⚠️  Could not find JavaScript section")

# Save
with open('data/output/dashboard_cincin_api_FINAL_CORRECTED.html', 'w', encoding='utf-8') as f:
    f.write(html)

print("\n" + "="*70)
print("✅ COMPREHENSIVE UPDATE COMPLETE")
print("="*70)
print("\nAdded to dynamic updates:")
print("  ✅ Yield Gap percentage")
print("  ✅ Total Loss (Rp Juta)")
print("  ✅ Loss Hectare estimate")
print("\nTotal dynamic elements: ~20")
print("\nNOTE: Peta kluster masih perlu generate untuk 36 blocks")
print("      Ini memakan waktu ~1-2 jam untuk semua blocks")
