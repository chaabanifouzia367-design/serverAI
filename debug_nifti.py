import os
import sys

file_path = r"C:\Users\jihad\Desktop\264_cbct.nii"

print(f"Checking: {file_path}")

if os.path.exists(file_path):
    print("✅ os.path.exists: True")
    try:
        stat_info = os.stat(file_path)
        print(f"✅ os.stat size: {stat_info.st_size}")
        
        # Check read access
        if os.access(file_path, os.R_OK):
            print("✅ Read access: OK")
        else:
            print("❌ Read access: DENIED")
            
        with open(file_path, 'rb') as f:
            data = f.read(10)
            print(f"✅ First 10 bytes: {data}")
            
    except Exception as e:
        print(f"❌ Error during access checks: {e}")
else:
    print("❌ os.path.exists: False")


