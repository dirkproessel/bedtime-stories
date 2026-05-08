import os
from pathlib import Path

env_path = Path("../backend/.env")

# Try to read the file, handling potential encoding issues
try:
    with open(env_path, "rb") as f:
        content = f.read()
    
    # If it has null bytes, it's likely UTF-16
    if b"\x00" in content:
        print("Detected UTF-16 or null bytes, fixing...")
        # Try to decode as UTF-16 and re-encode as UTF-8
        try:
            text = content.decode("utf-16")
        except UnicodeDecodeError:
            # Fallback: strip null bytes
            text = content.replace(b"\x00", b"").decode("utf-8", errors="ignore")
    else:
        text = content.decode("utf-8")
except Exception as e:
    print(f"Error reading .env: {e}")
    text = ""

# Clean up text
lines = [line.strip() for line in text.splitlines() if line.strip()]
# Remove any existing FAL_KEY lines to avoid duplicates
lines = [line for line in lines if not line.startswith("FAL_KEY=")]
# Add the new FAL_KEY
lines.append("FAL_KEY=6fb8d09f-336a-41af-b310-7d9f2384298e:86c0d8b6db845959fa5adc0d3023649c")

# Write back as UTF-8
with open(env_path, "w", encoding="utf-8") as f:
    f.write("\n".join(lines) + "\n")

print(".env fixed and FAL_KEY added.")
