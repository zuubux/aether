import re
text = "remember that my preferred_ide is VS Code"
fact_pattern = r"(?:remember that|note that|my)\s+([a-zA-Z0-9_\-\s]+?)\s+(?:is|are|=|:)\s+['\"]?([^'\"\n\.]+)['\"]?"
for match in re.finditer(fact_pattern, text, re.IGNORECASE):
    raw_key = match.group(1).strip()
    clean_key = raw_key.lower().replace(' ', '_')
    print("key:", clean_key, "val:", match.group(2).strip())
