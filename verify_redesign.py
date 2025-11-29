import sys
import json
import torch
from unittest.mock import MagicMock, patch
from image_node import VertexGeminiImageGenerator

def test_redesign():
    print("Testing Redesign...")
    
    # Mock inputs
    vertex_config = {"api_key": "test_key"}
    prompt = "test prompt"
    model_name = "gemini-3-pro-image-preview"
    image_input = torch.zeros((1, 512, 512, 3)) # Dummy image 1
    image_2 = torch.zeros((1, 256, 256, 3)) # Dummy image 2
    
    # Mock Generation Config
    generation_config = {
        "temperature": 0.8,
        "imageConfig": {
            "aspectRatio": "16:9",
            "personGeneration": "ALLOW_ALL"
        },
        "safetySettings": [
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"}
        ],
        "responseModalities": ["TEXT", "IMAGE"],
        "systemInstruction": {
            "parts": [{"text": "You are a creative artist."}]
        }
    }
    
    # Instantiate Node
    node = VertexGeminiImageGenerator()
    
    # Mock requests.post
    with patch('requests.post') as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        # Mock response with dummy image data
        mock_response.json.return_value = {
            "candidates": [{
                "content": {
                    "parts": [{
                        "inlineData": {
                            "mimeType": "image/png",
                            "data": "" # Empty data for test
                        }
                    }]
                }
            }]
        }
        mock_post.return_value = mock_response
        
        # Run generate_image
        try:
            node.generate_image(
                vertex_config=vertex_config, 
                prompt=prompt, 
                model_name=model_name, 
                aspect_ratio="1:1",
                person_generation="ALLOW_ADULT",
                output_resolution="1K",
                output_format="image/png",
                image_input=image_input,
                image_2=image_2,
                generation_config=generation_config
            )
        except Exception as e:
            # We expect it might fail on image decoding since data is empty, 
            # but we care about the request payload
            print(f"Execution finished (expected failure on empty image): {e}")
            
        # Verify Call Args
        args, kwargs = mock_post.call_args
        url = args[0]
        json_body = kwargs['json']
        
        print(f"URL: {url}")
        print(f"Payload: {json.dumps(json_body, indent=2)}")
        
        # Assertions
        assert "key=test_key" in url
        assert json_body["generationConfig"]["temperature"] == 0.8
        # Check imageConfig comes from node args
        assert json_body["generationConfig"]["imageConfig"]["aspectRatio"] == "1:1"
        assert json_body["generationConfig"]["imageConfig"]["imageSize"] == "1K"
        assert json_body["generationConfig"]["imageConfig"]["imageOutputOptions"]["mimeType"] == "image/png"
        
        assert json_body["safetySettings"][0]["threshold"] == "BLOCK_NONE"
        assert json_body["generationConfig"]["responseModalities"] == ["TEXT", "IMAGE"]
        assert json_body["systemInstruction"]["parts"][0]["text"] == "You are a creative artist."
        
        # Verify multiple images
        parts = json_body["contents"][0]["parts"]
        print(f"Number of parts: {len(parts)}")
        assert len(parts) == 3 # Text + Image 1 + Image 2
        
        # Check mime types (dummy tensors are 3 channels -> JPEG by default in our logic? 
        # Wait, utils.py logic: channels == 4 -> PNG, else JPEG.
        # Our dummy tensors are (1, 512, 512, 3), so they should be JPEG.
        print(f"Part 1 mime: {parts[1]['inlineData']['mimeType']}")
        print(f"Part 2 mime: {parts[2]['inlineData']['mimeType']}")
        
        assert parts[1]['inlineData']['mimeType'] == "image/jpeg"
        assert parts[2]['inlineData']['mimeType'] == "image/jpeg"
        
        print("Redesign Verification Passed!")

if __name__ == "__main__":
    test_redesign()
