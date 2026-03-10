import json
import sys
from pathlib import Path

audio_dir = Path('/var/www/bedtime/backend/audio_output')
if not audio_dir.exists():
    print('No audio_output directory found on VPS.')
    sys.exit(0)

total_paragraphs = 0
total_length = 0
story_count = 0
all_paras = []

for d in audio_dir.iterdir():
    if not d.is_dir(): continue
    json_path = d / 'story.json'
    if json_path.exists():
        try:
            data = json.loads(json_path.read_text(encoding='utf-8', errors='ignore'))
            chaps = data.get('chapters', [])
            if not chaps: continue
            
            story_count += 1
            for c in chaps:
                text = c.get('text', '')
                paras = [p.strip() for p in text.split('\n\n') if p.strip()]
                for p in paras:
                    if len(p) < 10: continue # Skip very short artifacts like "---" 
                    total_paragraphs += 1
                    total_length += len(p.encode('utf-8'))
                    all_paras.append(p)
        except Exception:
            pass

if total_paragraphs > 0:
    avg = total_length / total_paragraphs
    print(f'Analyzed {story_count} stories.')
    print(f'Total paragraphs: {total_paragraphs}')
    print(f'Average paragraph length: {avg:.1f} bytes')
    
    print('\nBeispiele für Absatzlängen:')
    import random
    if all_paras:
        for p in random.sample(all_paras, min(10, len(all_paras))):
            print(f'- {len(p.encode("utf-8"))} Bytes: {p[:120]}...')
else:
    print('No paragraphs found.')
