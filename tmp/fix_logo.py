from PIL import Image
import os

def make_transparent(input_path, output_path):
    img = Image.open(input_path)
    img = img.convert("RGBA")
    
    datas = img.getdata()
    
    # Get the background color from the first pixel
    bg_color = datas[0]
    # In case it's not perfect, let's use a small tolerance
    # The screenshot shows a dark grey/teal background
    
    new_data = []
    for item in datas:
        # If the pixel is close to the background color, make it transparent
        # Using a tolerance of 30 for each channel (R, G, B)
        # Assuming background is dark (low values)
        if abs(item[0] - bg_color[0]) < 40 and \
           abs(item[1] - bg_color[1]) < 40 and \
           abs(item[2] - bg_color[2]) < 40:
            new_data.append((0, 0, 0, 0))
        else:
            new_data.append(item)
            
    img.putdata(new_data)
    img.save(output_path, "PNG")

logo_path = r"c:\Dirk\Codings\bedtime-stories\public\logo.png"
backup_path = r"c:\Dirk\Codings\bedtime-stories\public\logo_backup.png"

if os.path.exists(logo_path):
    if not os.path.exists(backup_path):
        os.rename(logo_path, backup_path)
        print(f"Backed up {logo_path} to {backup_path}")
    
    make_transparent(backup_path, logo_path)
    print(f"Processed {logo_path} to be transparent.")
else:
    print(f"Error: {logo_path} not found.")
