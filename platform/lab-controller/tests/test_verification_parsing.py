import json
import re
import pytest

def extract_json_from_output(output: str) -> dict:
    """The logic from admin.py router for ARCH-16 verification."""
    raw = output.strip()
    # Regex from admin.py
    json_match = re.search(r'```(?:json)?\s*([\s\S]*?)```', raw) or re.search(r'(\{[\s\S]*\})', raw)
    json_str = json_match.group(1) if json_match else raw
    
    return json.loads(json_str)

def test_extract_pure_json():
    output = '{"status": "correct", "detail": "All good"}'
    assert extract_json_from_output(output)["status"] == "correct"

def test_extract_json_in_code_block():
    output = '''
Some random noise here.
```json
{"status": "correct", "detail": "Found in block"}
```
More noise.
'''
    result = extract_json_from_output(output)
    assert result["status"] == "correct"
    assert result["detail"] == "Found in block"

def test_extract_json_in_untagged_code_block():
    output = '''
```
{"status": "workaround", "detail": "Untagged"}
```
'''
    result = extract_json_from_output(output)
    assert result["status"] == "workaround"

def test_extract_json_with_leading_noise():
    output = '''
PowerShell Warning: This is a warning.
{"status": "correct", "detail": "With noise"}
'''
    result = extract_json_from_output(output)
    assert result["status"] == "correct"

def test_invalid_json_raises():
    output = 'This is not JSON at all'
    with pytest.raises(json.JSONDecodeError):
        extract_json_from_output(output)
