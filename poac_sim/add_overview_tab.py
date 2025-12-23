"""
Patch script to add Overview tab to dashboard_v7_fixed.py
"""

# Read current file
with open('dashboard_v7_fixed.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Add import at top (after other imports)
import_addition = "\nfrom all_divisions_module import generate_all_divisions_tab\n"

# Find where to insert (after pathlib import)
pathlib_pos = content.find('from pathlib import Path')
if pathlib_pos != -1:
    next_newline = content.find('\n', pathlib_pos)
    content = content[:next_newline] + import_addition + content[next_newline:]
    print('✅ Added import')
else:
    print('❌ Could not find pathlib import')

# Now add Overview tab generation before AME II/IV loop
# Find the line where tabs start being generated
marker = '    divisi_tabs = ""'
marker_pos = content.find(marker)

if marker_pos != -1:
    # Insert Overview tab logic before this
    overview_code = '''
    # Generate Overview tab for all divisions
    from all_divisions_module import generate_all_divisions_tab
    overview_data = generate_all_divisions_tab(prod_df, output_dir)
    
    divisi_tabs = '<button class="tab active" onclick="switchTab(\'overview\')" data-div="overview">📊 OVERVIEW</button>'
    divisi_content = f"""
        <div id="overview" class="tab-content" style="display:block;">
            {overview_data['html']}
        </div>
    """
    
'''
    content = content[:marker_pos] + overview_code + "    " + content[marker_pos:]
    print('✅ Added Overview tab generation')
else:
    print('❌ Could not find tabs marker')

# Update first AME tab to not be active by default
content = content.replace(
    'active = "active" if i == 0 else ""',
    'active = ""  # Overview is now default active'
)
print('✅ Updated AME tabs to not be default active')

# Write back
with open('dashboard_v7_fixed.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('\n✅✅✅ Dashboard patched successfully!')
print('Overview tab will now appear as first tab with production analysis')
