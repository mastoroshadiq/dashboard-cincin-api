"""
Fix Map Display Issue
Make map show for blocks that have generated maps, placeholder for others
"""

with open('data/output/dashboard_cincin_api_FINAL_CORRECTED.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Find map update section in JavaScript
search_str = "            // Update cluster maps"

if search_str in html:
    idx = html.find(search_str)
    # Find end of that function block (next comment or closing brace)
    end_idx = html.find("log('✅ Dashboard update complete", idx)
    
    if end_idx != -1:
        # Replace map update logic with better version
        new_map_logic = """            // Update cluster maps
            const mapImages = document.querySelectorAll('img[src*="cincin_api_map"]');
            if (mapImages.length > 0) {
                mapImages.forEach(img => {
                    // Try to load map for this block
                    const mapPath = data.map_filename;
                    
                    // For now, only F008A and D001A have maps
                    // Others show placeholder or no-image
                    if (blockCode === 'F008A' || blockCode === 'D001A') {
                        img.src = mapPath;
                        img.alt = `Peta Kluster ${blockCode}`;
                        img.style.display = 'block';
                    } else {
                        // Show placeholder for blocks without maps
                        img.style.display = 'none';
                        // Could insert placeholder div here
                        const parent = img.parentElement;
                        if (parent) {
                            const placeholder = document.createElement('div');
                            placeholder.className = 'bg-gray-100 rounded p-8 text-center text-gray-500';
                            placeholder.innerHTML = `
                                <svg class="mx-auto h-24 w-24 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
                                </svg>
                                <p class="mt-4 font-bold">Peta kluster belum tersedia untuk ${blockCode}</p>
                                <p class="text-sm mt-2">Hanya F008A dan D001A yang memiliki peta cluster saat ini</p>
                            `;
                            // Replace or append
                            if (!parent.querySelector('.bg-gray-100')) {
                                parent.appendChild(placeholder);
                            }
                        }
                    }
                });
                log('✅ Updated ' + mapImages.length + ' map images');
            }
            
            """
        
        # Extract everything before and after
        before = html[:idx]
        after = html[end_idx:]
        
        html = before + new_map_logic + after
        
        print("✅ Enhanced map display logic with placeholder support")
    else:
        print("⚠️  End of map section not found")
else:
    print("⚠️  Map update section not found")

with open('data/output/dashboard_cincin_api_FINAL_CORRECTED.html', 'w', encoding='utf-8') as f:
    f.write(html)

print("\n✅ Map display logic updated")
print("   - F008A & D001A: Show actual maps")
print("   - Other blocks: Show 'map not available' placeholder")
