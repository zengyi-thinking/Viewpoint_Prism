import re

# Test path from ChromaDB
frame_path = r"D:\DevProject\Viewpoint_Prism\packages\backend\data\temp\0db60f05-2855-4768-a18e-b7bfbb350b66\frames\frame_00001.jpg"
print(f"Original path: {frame_path}")
print(f"Repr: {repr(frame_path)}")

# Normalize path separators to forward slashes
normalized_path = frame_path.replace("\\", "/")
print(f"Normalized: {normalized_path}")

# Test the regex pattern
temp_match = re.search(r'(?:^|/)data/temp/(.+)$', normalized_path)
print(f"Match result: {temp_match}")

if temp_match:
    relative_path = temp_match.group(1)
    url = f"/static/temp/{relative_path}"
    print(f"✓ Success! URL: {url}")
else:
    print("✗ Regex failed to match")
    # Try alternative approach
    if "data/temp" in normalized_path:
        parts = normalized_path.split("data/temp/")
        if len(parts) > 1:
            relative_path = parts[1]
            url = f"/static/temp/{relative_path}"
            print(f"✓ Fallback worked! URL: {url}")
