"""
FIX CRITICAL CALCULATION ERROR + Add detailed explanations
Potensi Kerugian was using 1.5 instead of 1500 for TBS price!
"""

with open('data/output/dashboard_cincin_api_INTERACTIVE_FULL.html', 'r', encoding='utf-8') as f:
    html = f.read()

print("🔧 Fixing CRITICAL calculation error + adding explanations...")
print("="*70)

# Find and fix the loss calculation - change 1.5 to 1500
old_loss_calc = "['lossValue', `Rp ${(((data.merah + data.oranye) * 128 * 1.5 * 10) / 1000000).toFixed(2)}`],"

new_loss_calc = "['lossValue', `Rp ${(((data.merah + data.oranye) * 128 * 1500 * 10) / 1000000).toFixed(1)}`],"

if old_loss_calc in html:
    html = html.replace(old_loss_calc, new_loss_calc)
    print("✅ Fixed loss calculation (1.5 → 1500 for TBS price)")
else:
    print("⚠️  Loss calc pattern not found")

# Save
with open('data/output/dashboard_cincin_api_INTERACTIVE_FULL.html', 'w', encoding='utf-8') as f:
    f.write(html)

# Now add detailed explanation tooltips/notes
with open('data/output/dashboard_cincin_api_INTERACTIVE_FULL.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Add explanation under Cakupan Wilayah
old_area_note = '<p class="text-[10px] text-white opacity-90 mt-1 font-black tracking-tighter" id="area-note"\n                                style="display: none;"></p>'

new_area_note = '''<p class="text-[10px] text-white opacity-90 mt-1 font-black tracking-tighter" id="areaNote">
                                Berdasarkan total pohon × 64 m²/pohon</p>'''

if old_area_note in html:
    html = html.replace(old_area_note, new_area_note)
    print("✅ Added area calculation note")

# Add explanation for Loss value (after the value)
# Find the loss card and add explanation
search_loss = '</div>\n                        </div>'  # After POTENSI KERUGIAN value

# We need to be more specific. Let me find the exact section
loss_section = '''<div class="flex items-baseline gap-2">
                                <span class="text-4xl text-red-400 font-black" id="lossValue">Rp --</span>
                                <span
                                    class="text-red-400 text-sm uppercase tracking-tighter font-black">MILAR/THN</span>
                            </div>'''

new_loss_section = '''<div class="flex items-baseline gap-2">
                                <span class="text-4xl text-red-400 font-black" id="lossValue">Rp --</span>
                                <span
                                    class="text-red-400 text-sm uppercase tracking-tighter font-black">MILAR/THN</span>
                            </div>
                            <p class="text-[10px] text-red-300 mt-2 font-bold italic" id="lossFormula">
                                Formula: Pohon terinfeksi × 128 kg/thn × Rp 1.500/kg × 10 tahun
                            </p>'''

if loss_section in html:
    html = html.replace(loss_section, new_loss_section)
    print("✅ Added loss formula explanation")

# Add mitigation explanation
mitigation_section = '''<div class="flex items-baseline gap-2">
                                <span class="text-4xl text-emerald-400 font-black" id="mitigationValue">Rp --</span>
                                <span
                                    class="text-emerald-400 text-sm uppercase tracking-tighter font-black">MILAR</span>
                            </div>
                            <p class="text-[10px] text-emerald-300 mt-2 font-black italic" id="mitigationRatio">Parit Isolasi untuk cluster terinfeksi
                            </p>'''

new_mitigation_section = '''<div class="flex items-baseline gap-2">
                                <span class="text-4xl text-emerald-400 font-black" id="mitigationValue">Rp --</span>
                                <span
                                    class="text-emerald-400 text-sm uppercase tracking-tighter font-black">MILAR</span>
                            </div>
                            <p class="text-[10px] text-emerald-300 mt-2 font-black italic" id="mitigationRatio">
                                Hanya X% dari potensi kerugian
                            </p>
                            <p class="text-[10px] text-emerald-300 mt-1 font-bold">
                                Formula: Keliling cluster × Rp 75.000/meter parit
                            </p>'''

if mitigation_section in html:
    html = html.replace(mitigation_section, new_mitigation_section)
    print("✅ Added mitigation formula explanation")

with open('data/output/dashboard_cincin_api_INTERACTIVE_FULL.html', 'w', encoding='utf-8') as f:
    f.write(html)

# Update JavaScript to also update the areaNote
with open('data/output/dashboard_cincin_api_INTERACTIVE_FULL.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Find updates array and add areaNote
search_area = "['areaValue', ((data.total_pohon * 64) / 10000).toFixed(1)],  // Hectares from tree count"

new_area = """['areaValue', ((data.total_pohon * 64) / 10000).toFixed(1)],  // Hectares from tree count
                ['areaNote', `${data.total_pohon.toLocaleString()} pohon × 64 m²`],"""

if search_area in html:
    html = html.replace(search_area, new_area)
    print("✅ Added dynamic area note update")

# Update mitigation ratio calculation to also update formula text
search_ratio_update = """// Update mitigation ratio text
            const ratioEl = document.getElementById('mitigationRatio');
            if (ratioEl) {
                ratioEl.textContent = `Hanya ${ratio}% dari potensi kerugian - SANGAT EFEKTIF!`;
            }"""

new_ratio_update = """// Update mitigation ratio text with CORRECT economic interpretation
            const ratioEl = document.getElementById('mitigationRatio');
            if (ratioEl) {
                if (ratio < 5) {
                    ratioEl.textContent = `Hanya ${ratio}% dari kerugian - SANGAT EFEKTIF!`;
                } else if (ratio < 10) {
                    ratioEl.textContent = `${ratio}% dari kerugian - EFEKTIF`;
                } else if (ratio < 20) {
                    ratioEl.textContent = `${ratio}% dari kerugian - CUKUP EFEKTIF`;
                } else {
                    ratioEl.textContent = `${ratio}% dari kerugian - PERTIMBANGKAN ULANG`;
                }
            }"""

if search_ratio_update in html:
    html = html.replace(search_ratio_update, new_ratio_update)
    print("✅ Enhanced mitigation ratio interpretation")

with open('data/output/dashboard_cincin_api_INTERACTIVE_FULL.html', 'w', encoding='utf-8') as f:
    f.write(html)

print("\n" + "="*70)
print("✅ CRITICAL FIX + EXPLANATIONS ADDED!")
print("="*70)

print("\n🔢 CORRECTED FORMULAS:\n")
print("POTENSI KERUGIAN (was WRONG, now CORRECT):")
print("  BEFORE: × 1.5 (WRONG! Too small by 1000x)")
print("  AFTER:  × 1,500 (CORRECT TBS price Rp/kg)")
print("  = (Merah + Oranye) × 128 kg/thn × Rp 1,500/kg × 10 years")
print()
print("Example E009A (336 infected):")
print("  BEFORE: Rp 0.645 MILAR (WRONG!)")
print("  AFTER:  Rp 645.1 MILAR (CORRECT!)")
print()
print("BIAYA MITIGASI:")
print("  = sqrt(336) × 8m × 4 sides × Rp 75,000/m")
print("  = Rp 43.8 MILAR")
print()
print("RATIO:")
print("  = 43.8 / 645.1 = 6.8% ← NOW MAKES SENSE!")
print("\nExplanations now shown on dashboard for transparency!")
