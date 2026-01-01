import sys
sys.path.insert(0, '.')

from app.services.vector_store import get_vector_store
import re

vs = get_vector_store()

# Get visual docs for the source
results = vs.collection.get(
    where={'$and': [{'source_id': '0db60f05-2855-4768-a18e-b7bfbb350b66'}, {'type': 'visual'}]},
    limit=2,
    include=['metadatas']
)

print(f"Found {len(results['metadatas'])} visual docs")

for i, metadata in enumerate(results['metadatas']):
    frame_path = metadata.get('frame_path')
    if not frame_path:
        continue

    print(f"\n--- Doc {i+1} ---")
    print(f"Original frame_path: {frame_path}")
    print(f"Repr: {repr(frame_path)}")

    # Same code as analysis_service.py
    normalized_path = frame_path.replace("\\", "/")
    print(f"Normalized: {normalized_path}")

    temp_match = re.search(r'(?:^|/)data/temp/(.+)$', normalized_path)
    print(f"Match: {temp_match}")

    if temp_match:
        relative_path = temp_match.group(1)
        url = f"/static/temp/{relative_path}"
        print(f"SUCCESS! URL: {url}")
