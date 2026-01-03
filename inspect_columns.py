import json

# Load raw data
with open('data/output/all_36_blocks_raw_rows.json') as f:
    data = json.load(f)

print(f"✅ Loaded {len(data)} blocks\n")

# Check F008A values to find Potensi and Realisasi columns
f008_vals = data['F008A']['values']

print("F008A row values (first 50):")
for i in range(min(50, len(f008_vals))):
    val = f008_vals[i]
    print(f"Col {i:2d}: {val}")
    
    # Highlight if close to known values
    try:
        num_val = float(val)
        if abs(num_val - 19.52) < 0.1 or abs(num_val - 21.22) < 0.1:
            print(f"      ^^^ POTENTIAL MATCH! (Potensi=19.52 or Realisasi=21.22)")
    except:
        pass

print("\n" + "="*70)
print("D001A row values (first 50):")
d001_vals = data['D001A']['values']
for i in range(min(50, len(d001_vals))):
    val = d001_vals[i]
    print(f"Col {i:2d}: {val}")
    
    # Highlight if close to known values (Potensi=22.13, Realisasi=17.42)
    try:
        num_val = float(val)
        if abs(num_val - 22.13) < 0.1 or abs(num_val - 17.42) < 0.1:
            print(f"      ^^^ POTENTIAL MATCH! (Potensi=22.13 or Realisasi=17.42)")
    except:
        pass
