"""Check and patch xAI VOICE_INSTRUCTIONS entries."""
import os
tts_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app', 'services', 'tts_service.py')

with open(tts_path, 'r', encoding='utf-8') as f:
    content = f.read()

has_xai = '"xai_felix": ""' in content
print(f'xai_felix already in VOICE_INSTRUCTIONS: {has_xai}')

if not has_xai:
    # Find the jenny entry and the closing brace right after it
    jenny_start = content.find('"jenny":')
    if jenny_start == -1:
        print("ERROR: jenny not found")
    else:
        # Find end of jenny's line
        jenny_line_end = content.find('\n', jenny_start)
        # The next non-empty char should be }
        after_jenny = content[jenny_line_end:]
        close_pos = after_jenny.find('}')
        insert_pos = jenny_line_end + close_pos  # position of } in content

        xai_entries = (
            '\n    # xAI voices - kein system-prompt-Konzept fur TTS'
            '\n    "xai_felix": "",'
            '\n    "xai_sonja": "",'
            '\n    "xai_ara":   "",'
            '\n    "xai_eve":   "",'
            '\n    "xai_leo":   "",'
            '\n    "xai_rex":   "",'
            '\n    "xai_sal":   "",'
            '\n'
        )
        content = content[:insert_pos] + xai_entries + content[insert_pos:]
        with open(tts_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print('OK: xAI entries inserted before } of VOICE_INSTRUCTIONS')
else:
    print('Already patched, nothing to do')

# Verify lines around jenny
with open(tts_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()
for i, line in enumerate(lines[107:120], start=108):
    print(f'{i}: {line}', end='')
