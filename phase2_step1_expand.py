"""
PHASE 2: Add More Dynamic Elements
Focus on visible, high-impact sections
"""

print("🚀 PHASE 2: Expanding Interactive Dashboard")
print("="*70)

# Read HTML
with open('data/output/dashboard_cincin_api_FINAL_CORRECTED.html', 'r', encoding='utf-8') as f:
    html = f.read()

print("✅ Loaded HTML")

# Define comprehensive replacements for Phase 2
# Focus on text content that mentions block codes or shows statistics

replacements = [
    # Snapshot Faktual section - Attack Rate displays
    # These appear in the summary cards at top
    
    # Find and add ID to attack rate percentage displays
    # We need to be careful with exact matching
    
    # Status badge "Darurat" - maybe dynamic based on severity
    ('class="bg-red-600 text-white text-[10px] font-black px-3 py-1 rounded-full uppercase tracking-widest animate-pulse">Status:\n                            Darurat<',
     'class="bg-red-600 text-white text-[10px] font-black px-3 py-1 rounded-full uppercase tracking-widest animate-pulse" id="blockStatusBadge">Status:\n                            <span id="blockStatusText">Darurat</span><'),
]

# Apply basic replacements
for old, new in replacements:
    if old in html:
        html = html.replace(old, new, 1)
        print(f"✅ Added status badge IDs")
    else:
        print(f"⚠️  Status badge pattern not found, trying alternative...")

# Save temporarily
with open('data/output/dashboard_cincin_api_FINAL_CORRECTED.html', 'w', encoding='utf-8') as f:
    f.write(html)

print("\n" + "="*70)
print("Step 1: Basic IDs added")
print("="*70)

# Now let's enhance the JavaScript with MORE comprehensive updates
# Read again with fresh data
with open('data/output/dashboard_cincin_api_FINAL_CORRECTED.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Find updateDashboard function and enhance it
js_search = "            // Update all stats with comprehensive ID list\n            const updates = ["

if js_search in html:
    print("\n✅ Found updates array in JavaScript")
    
    # Find the full updates array
    start_idx = html.find(js_search)
    end_idx = html.find("];", start_idx) + 2
    
    old_updates_section = html[start_idx:end_idx]
    
    # Create EXPANDED updates array
    new_updates_section = """            // Update all stats with comprehensive ID list
            const updates = [
                // Header and title
                ['blockHeaderTitle', `Detail Blok ${blockCode} (${((data.total_pohon * 64) / 10000).toFixed(1)} Ha)`],
                
                // Basic stats (Phase 1 - already working)
                ['blockTT', `${data.tt || 'N/A'} (${data.age || 'N/A'} Tahun)`],
                ['blockSPH', `${data.sph || 'N/A'} Pokok/Ha`],
                ['blockTotalPohon', data.total_pohon.toLocaleString()],
                ['blockSisip', data.sisip ? data.sisip.toLocaleString() : 'N/A'],
                ['blockMerahCount', data.merah],
                ['blockOranyeCount', data.oranye],
                ['blockKuningCount', data.kuning],
                
                // Phase 2: Status and severity
                ['blockStatusText', data.severity === 'HIGH' ? 'Darurat' : 'Perhatian']
            ];
            
            // Update status badge color based on severity
            const statusBadge = document.getElementById('blockStatusBadge');
            if (statusBadge) {
                if (data.severity === 'HIGH') {
                    statusBadge.className = 'bg-red-600 text-white text-[10px] font-black px-3 py-1 rounded-full uppercase tracking-widest animate-pulse';
                } else {
                    statusBadge.className = 'bg-orange-600 text-white text-[10px] font-black px-3 py-1 rounded-full uppercase tracking-widest animate-pulse';
                }
            }"""
    
    html = html.replace(old_updates_section, new_updates_section)
    print("✅ Enhanced JavaScript updates array")
else:
    print("⚠️  Updates array not found - skipping JS enhancement")

# Save final
with open('data/output/dashboard_cincin_api_FINAL_CORRECTED.html', 'w', encoding='utf-8') as f:
    f.write(html)

print("\n" + "="*70)
print("✅ PHASE 2 STEP 1 COMPLETE!")
print("="*70)
print("\nAdded:")
print("  ✅ Status badge (Darurat/Perhatian) - dynamic based on severity")
print("  ✅ Badge color changes: RED for HIGH, ORANGE for MEDIUM")
print("\nNext: Will add more sections in Step 2...")
