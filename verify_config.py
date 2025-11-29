import sys
import os
import json
import time

try:
    from config_nodes import VertexGenerationConfig, VertexSaveConfig, VertexLoadConfig
    from utils import list_config_files, load_config_file, get_config_dir
    
    print("Testing Config Nodes...")
    
    # 1. Test Generation Config Creation
    gen_node = VertexGenerationConfig()
    gen_config = gen_node.create_config(temperature=0.8, top_p=0.9, top_k=20, max_output_tokens=1024)[0]
    print(f"Generation Config Created: {gen_config}")
    assert gen_config["temperature"] == 0.8
    
    # 2. Test Save Config
    save_node = VertexSaveConfig()
    filename_prefix = "test_config"
    filepath = save_node.save_config(filename_prefix, generation_config=gen_config)[0]
    print(f"Config Saved to: {filepath}")
    assert os.path.exists(filepath)
    
    # 3. Test List Configs
    files = list_config_files()
    print(f"Config Files: {files}")
    assert len(files) > 0
    latest_file = files[0]
    
    # 4. Test Load Config
    load_node = VertexLoadConfig()
    loaded_vertex, loaded_gen = load_node.load_config(latest_file)
    print(f"Loaded Gen Config: {loaded_gen}")
    assert loaded_gen["temperature"] == 0.8
    
    # Cleanup
    os.remove(filepath)
    print("Cleanup successful.")
    
    print("Config Verification Passed!")
    
except Exception as e:
    print(f"Verification failed: {e}")
    sys.exit(1)
