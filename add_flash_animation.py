"""
Add visual flash animation to show which elements change
"""

with open('data/output/dashboard_cincin_api_FINAL_CORRECTED.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Add CSS for flash animation
css_insert = '''    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;900&display=swap');

        body {
            font-family: 'Inter', sans-serif;
        }

        @keyframes flashGreen {
            0%, 100% { background-color: transparent; }
            50% { background-color: #10b981; color: white; }
        }

        .flash-update {
            animation: flashGreen 0.6s ease-in-out;
        }

        .animate-pulse {'''

html = html.replace(
    '''    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;900&display=swap');

        body {
            font-family: 'Inter', sans-serif;
        }

        .animate-pulse {''',
    css_insert
)

# Update JavaScript to add flash class
js_update = '''            updates.forEach(([id, value]) => {
                const el = document.getElementById(id);
                if (el) {
                    el.textContent = value;
                    // Add flash animation
                    el.classList.add('flash-update');
                    setTimeout(() => el.classList.remove('flash-update'), 600);
                    successCount++;
                } else {
                    console.warn(`⚠️ Element not found: ${id}`);
                    failCount++;
                }
            });'''

html = html.replace(
    '''            updates.forEach(([id, value]) => {
                const el = document.getElementById(id);
                if (el) {
                    el.textContent = value;
                    successCount++;
                } else {
                    console.warn(`⚠️ Element not found: ${id}`);
                    failCount++;
                }
            });''',
    js_update
)

with open('data/output/dashboard_cincin_api_FINAL_CORRECTED.html', 'w', encoding='utf-8') as f:
    f.write(html)

print("✅ Added flash animation!")
print("✅ Changed elements will now FLASH GREEN for 0.6 seconds")
print("\nRefresh browser and select different block - you'll SEE what changes!")
