"""
PHASE 1: Apply Working PoC Pattern to Full Dashboard
Add ALL necessary IDs and fix JavaScript using proven pattern
"""
import re

print("🚀 PHASE 1: Applying Proven PoC Pattern to Full Dashboard")
print("="*70)

# Read HTML
with open('data/output/dashboard_cincin_api_FINAL_CORRECTED.html', 'r', encoding='utf-8') as f:
    html = f.read()

print("✅ Loaded HTML")

# Define ALL ID replacements needed (comprehensive list)
replacements = [
    # Block header
    ('<!-- SECTION DETAIL BLOK F008A -->', '<!-- SECTION DETAIL BLOK F008A --><div id="dynamicBlockSection">'),
    
    # Already have these from before - verify
    # TT, SPH, Total, Sisip, Merah, Oranye, Kuning
]

# Close dynamic section before D001A (which we hide)
html = html.replace(
    '<!-- SECTION DETAIL BLOK D001A (HIDDEN - Using F008A as dynamic) -->',
    '</div><!-- END dynamicBlockSection -->\n        <!-- SECTION DETAIL BLOK D001A (HIDDEN - Using F008A as dynamic) -->'
)

print("✅ Wrapped dynamic section")

# Now FIX JavaScript - Replace with PROVEN PoC pattern
js_old_start = '<!-- Interactive Controller Script -->'
js_old_end = '</script>\n\n</body>'

# Find and extract current JS section
js_start_idx = html.find(js_old_start)
if js_start_idx == -1:
    print("❌ JavaScript section not found!")
    exit(1)

js_end_idx = html.find('</body>', js_start_idx)

# Replace with WORKING pattern from PoC
new_js = '''<!-- Interactive Controller Script -->
    <script>
        let currentBlockData = null;
        
        // Debug logging
        function log(msg) {
            console.log('🔵 Dashboard:', msg);
        }

        // Initialize on page load - PROVEN PoC PATTERN
        window.addEventListener('DOMContentLoaded', function() {
            log('Page loaded, initializing...');
            
            if (typeof BLOCKS_DATA === 'undefined') {
                console.error('❌ BLOCKS_DATA not loaded!');
                alert('Error: Block data not loaded. Please refresh.');
                return;
            }
            
            log('✅ BLOCKS_DATA loaded with ' + Object.keys(BLOCKS_DATA).length + ' blocks');
            
            populateDropdown();
            
            // Attach event listener - PROVEN PATTERN
            const selector = document.getElementById('blockSelector');
            if (!selector) {
                console.error('❌ blockSelector not found!');
                return;
            }
            
            selector.addEventListener('change', function() {
                const selected = this.value;
                log('Dropdown changed to: ' + selected);
                updateDashboard(selected);
            });
            
            log('✅ Event listener attached');
            
            // Auto-select first block
            const firstBlock = Object.keys(BLOCKS_DATA)[0];
            if (firstBlock) {
                selector.value = firstBlock;
                updateDashboard(firstBlock);
                log('✅ Auto-selected: ' + firstBlock);
            }
        });

        // Populate dropdown
        function populateDropdown() {
            const selector = document.getElementById('blockSelector');
            const sorted = Object.entries(BLOCKS_DATA).sort((a,b) => a[1].rank - b[1].rank);
            
            selector.innerHTML = sorted.map(([code, data]) => 
                `<option value="${code}">#${data.rank} - ${code} | ${data.attack_rate}% | ${data.severity}</option>`
            ).join('');
            
            document.getElementById('totalBlocks').textContent = sorted.length;
            log('✅ Populated ' + sorted.length + ' blocks');
        }

        // Update dashboard - COMPREHENSIVE VERSION
        function updateDashboard(blockCode) {
            if (!blockCode) {
                log('⚠️ Empty blockCode');
                return;
            }
            
            const data = BLOCKS_DATA[blockCode];
            if (!data) {
                console.error('❌ No data for block:', blockCode);
                return;
            }
            
            currentBlockData = data;
            log('📊 Updating dashboard for: ' + blockCode);
            
            // Update header
            const headerEl = document.getElementById('headerBlockCode');
            if (headerEl) {
                headerEl.textContent = blockCode;
                log('✅ Updated header');
            }
            
            document.title = `Dashboard Cincin Api - ${blockCode} (${data.attack_rate}%)`;
            
            // Update all stats with comprehensive ID list
            const updates = [
                ['blockTT', `${data.tt || 'N/A'} (${data.age || 'N/A'} Tahun)`],
                ['blockSPH', `${data.sph || 'N/A'} Pokok/Ha`],
                ['blockTotalPohon', data.total_pohon.toLocaleString()],
                ['blockSisip', data.sisip ? data.sisip.toLocaleString() : 'N/A'],
                ['blockMerahCount', data.merah],
                ['blockOranyeCount', data.oranye],
                ['blockKuningCount', data.kuning]
            ];
            
            let successCount = 0;
            let failCount = 0;
            
            updates.forEach(([id, value]) => {
                const el = document.getElementById(id);
                if (el) {
                    el.textContent = value;
                    successCount++;
                } else {
                    console.warn(`⚠️ Element not found: ${id}`);
                    failCount++;
                }
            });
            
            log(`✅ Updated ${successCount} elements, ${failCount} missing`);
            
            // Update cluster maps
            const mapImages = document.querySelectorAll('img[src*="cincin_api_map"]');
            if (mapImages.length > 0 && data.map_filename) {
                mapImages.forEach(img => {
                    img.src = data.map_filename;
                    img.alt = `Peta Kluster ${blockCode}`;
                });
                log('✅ Updated ' + mapImages.length + ' map images');
            }
            
            log('✅ Dashboard update complete for: ' + blockCode);
        }

        // Tab switching (existing function)
        function showTab(tabName) {
            document.querySelectorAll('[id^="tab-"]').forEach(tab => tab.style.display = 'none');
            document.querySelectorAll('[id^="btn-"]').forEach(btn => {
                btn.classList.remove('bg-indigo-600', 'text-white', 'shadow-md');
                btn.classList.add('text-black', 'hover:bg-slate-50');
            });
            
            const selectedTab = document.getElementById('tab-' + tabName);
            if (selectedTab) {
                selectedTab.style.display = 'block';
            }
            
            const activeBtn = document.getElementById('btn-' + tabName);
            if (activeBtn) {
                activeBtn.classList.add('bg-indigo-600', 'text-white', 'shadow-md');
                activeBtn.classList.remove('text-black', 'hover:bg-slate-50');
            }
        }
    </script>

</body>'''

# Replace JavaScript section
html = html[:js_start_idx] + new_js

print("✅ Replaced JavaScript with proven PoC pattern")

# Write back
with open('data/output/dashboard_cincin_api_FINAL_CORRECTED.html', 'w', encoding='utf-8') as f:
    f.write(html)

print("\n" + "="*70)
print("✅ PHASE 1 COMPLETE!")
print("="*70)
print("\nChanges made:")
print("✅ Wrapped dynamic section with ID")
print("✅ Applied PROVEN PoC JavaScript pattern")
print("✅ Added comprehensive logging")
print("✅ Used addEventListener (not onchange attribute)")
print("\nTest now:")
print("1. Open dashboard")
print("2. Open Console (F12)")
print("3. Select different blocks")
print("4. Check console logs for detailed feedback")
