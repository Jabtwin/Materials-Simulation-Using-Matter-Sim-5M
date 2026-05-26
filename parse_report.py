import re
import json

data = []
current_element = None
current_struct = None
current_entry = None

with open('comprehensive_report_elements.md', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for line in lines:
    el_match = re.search(r'^## Element: ([A-Za-z]+)', line)
    if el_match:
        current_element = el_match.group(1)
        continue
        
    st_match = re.search(r'^### Structure: ([a-z]+)', line)
    if st_match and current_element:
        current_struct = st_match.group(1)
        current_entry = {
            'Element': current_element,
            'Structure': current_struct,
            'a_pred': None,
            'B_pred': None,
            'pass_count': 0,
            'fail_count': 0,
            'modes': {}
        }
        data.append(current_entry)
        continue
        
    mode_match = re.search(r'^### (?!Structure:)(.*)', line)
    if mode_match and current_entry:
        current_mode = mode_match.group(1).strip()
        current_entry['modes'][current_mode] = {'status': 'UNKNOWN'}
        continue
        
    if current_entry and current_entry['modes']:
        last_mode = list(current_entry['modes'].keys())[-1]
        
        status_match = re.search(r'- \*\*Status\*\*: \[([A-Z]+)\]', line)
        if status_match:
            status = status_match.group(1)
            current_entry['modes'][last_mode]['status'] = status
            if status == 'PASS':
                current_entry['pass_count'] += 1
            elif status == 'FAIL':
                current_entry['fail_count'] += 1
                
        details_match = re.search(r'- \*\*Details\*\*: (.*)', line)
        if details_match:
            details = details_match.group(1)
            current_entry['modes'][last_mode]['details'] = details
            
            # Extract Lattice Constant
            if last_mode == 'Equilibrium Scan':
                a_match = re.search(r'a=([0-9.]+) ', details)
                if a_match:
                    current_entry['a_pred'] = float(a_match.group(1))
            
            # Extract Bulk Modulus
            if last_mode == 'Equation of State':
                b_match = re.search(r'Bulk Modulus = ([0-9.-]+) GPa', details)
                if b_match:
                    current_entry['B_pred'] = float(b_match.group(1))

# Write extracted data to json
with open('extracted_data.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2)

print(f"Extracted {len(data)} entries.")
