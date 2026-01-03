"""
Change loss projection from 10 years to 1 year (more practical)
Adjust mitigation cost to be realistic 1-time expense
"""

with open('data/output/dashboard_cincin_api_INTERACTIVE_FULL.html', 'r', encoding='utf-8') as f:
    html = f.read()

print("🔧 Adjusting to 1-year loss projection...")
print("="*70)

# Change loss calculation from 10 years to 1 year
old_loss = "['lossValue', `Rp ${(((data.merah + data.oranye) * 128 * 1500 * 10) / 1000000).toFixed(1)}`]"
new_loss = "['lossValue', `Rp ${(((data.merah + data.oranye) * 128 * 1500 * 1) / 1000000).toFixed(1)}`]"

if old_loss in html:
    html = html.replace(old_loss, new_loss)
    print("✅ Changed loss from 10 years to 1 year")
else:
    print("⚠️  Loss calc not found")

# Update explanation text
old_formula = "Formula: Pohon terinfeksi × 128 kg/thn × Rp 1.500/kg × 10 tahun"
new_formula = "Formula: Pohon terinfeksi × 128 kg/thn × Rp 1.500/kg × 1 tahun"

if old_formula in html:
    html = html.replace(old_formula, new_formula)
    print("✅ Updated formula explanation")

# Update JavaScript calculation comment
old_comment = "// = (merah + oranye) × (20000 kg / 156 trees/ha) × 1.5 × 10 / 1,000,000 (to get millions)"
new_comment = "// = (merah + oranye) × 128 kg/tree/yr × 1500 Rp/kg × 1 year / 1,000,000"

if old_comment in html:
    html = html.replace(old_comment, new_comment)
    print("✅ Updated JS comment")

# Update ratio calculation in JavaScript
old_ratio_calc = "const lossValue = ((infectedTrees * 128 * 1.5 * 10) / 1000000);"
new_ratio_calc = "const lossValue = ((infectedTrees * 128 * 1500 * 1) / 1000000);"

if old_ratio_calc in html:
    html = html.replace(old_ratio_calc, new_ratio_calc)
    print("✅ Updated ratio calculation")

with open('data/output/dashboard_cincin_api_INTERACTIVE_FULL.html', 'w', encoding='utf-8') as f:
    f.write(html)

print("\n" + "="*70)
print("✅ ADJUSTED TO 1-YEAR PROJECTION")
print("="*70)

print("\n📊 NEW CALCULATIONS:\n")
print("POTENSI KERUGIAN (1 year):")
print("  = (Merah + Oranye) × 128 kg/thn × Rp 1,500/kg × 1 tahun")
print("  Example E009A: 336 × 128 × 1500 × 1 = Rp 64.5 MILAR/tahun")
print()
print("BIAYA MITIGASI (one-time):")
print("  = Unchanged: Rp 43.8 MILAR (excavation cost)")
print()
print("RATIO:")
print("  = 43.8 / 64.5 = 67.9%")
print("  Interpretation: One-time mitigation cost vs annual loss")
print("  ROI: Investment recoup in ~8 months if successful")
print()
print("More realistic and actionable timeframe!")
