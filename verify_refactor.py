import sys
import os

try:
    from auth_node import VertexAIAuth
    from image_node import VertexGeminiImageGenerator
    from text_node import VertexGeminiTextGenerator
    import __init__
    
    print("All modules imported successfully.")
    print("Mappings in __init__:", list(__init__.NODE_CLASS_MAPPINGS.keys()))
    
    expected_nodes = ["VertexAIAuth", "VertexGeminiImageGenerator", "VertexGeminiTextGenerator"]
    for node in expected_nodes:
        if node not in __init__.NODE_CLASS_MAPPINGS:
            raise Exception(f"Missing node in mappings: {node}")
            
    print("Verification passed!")
except Exception as e:
    print(f"Verification failed: {e}")
    sys.exit(1)
