"""
Test: Security Validation
Ensures no credentials are exposed and APIs work
"""
import pytest
import os
import glob
import re


class TestSecurity:
    
    def test_env_file_exists(self):
        """Verify .env file exists"""
        assert os.path.exists('.env'), ".env file missing!"
        print("✅ .env file exists")
    
    def test_env_example_has_placeholders(self):
        """Check .env.example doesn't have real credentials"""
        if not os.path.exists('.env.example'):
            pytest.skip(".env.example not found")
        
        with open('.env.example', 'r') as f:
            content = f.read()
        
        # Should NOT have real OpenAI keys (check for full keys, not just prefix)
        # Allow sk-proj-xxxxx as placeholder
        lines = content.split('\n')
        for line in lines:
            if 'OPENAI_API_KEY' in line and '=' in line:
                value = line.split('=', 1)[1].strip()
                # Check if it's a real key (longer than placeholder)
                if value.startswith('sk-') and len(value) > 20 and 'xxxxx' not in value.lower():
                    pytest.fail(f"Real OpenAI key found in .env.example: {value[:15]}...")
        
        # Should have placeholders
        assert 'your_' in content.lower() or 'xxx' in content.lower(), \
            ".env.example should have placeholders!"
        
        print("✅ .env.example has placeholders (no real credentials)")
    
    def test_api_keys_loaded(self):
        """Verify API keys are loaded from environment"""
        assert os.getenv('OPENAI_API_KEY'), "OPENAI_API_KEY not loaded!"
        assert os.getenv('MATHPIX_APP_ID'), "MATHPIX_APP_ID not loaded!"
        assert os.getenv('MATHPIX_APP_KEY'), "MATHPIX_APP_KEY not loaded!"
        
        print("✅ All API keys loaded")
    
    def test_no_hardcoded_credentials_in_code(self):
        """Check no hardcoded credentials in Python files"""
        violations = []
        
        for py_file in glob.glob('src/**/*.py', recursive=True):
            with open(py_file, 'r') as f:
                content = f.read()
                lines = content.split('\n')
                
                for i, line in enumerate(lines, 1):
                    # Skip comments
                    if line.strip().startswith('#'):
                        continue
                    
                    # Check for potential hardcoded credentials
                    if 'sk-proj-' in line or ('sk-' in line and 'openai' in line.lower()):
                        violations.append(f"{py_file}:{i} - Possible hardcoded API key")
                    
                    if re.search(r'password\s*=\s*["\'][^"\']+["\']', line, re.IGNORECASE):
                        violations.append(f"{py_file}:{i} - Hardcoded password")
        
        if violations:
            print("⚠️  Potential credential leaks found:")
            for v in violations:
                print(f"  - {v}")
            pytest.fail(f"Found {len(violations)} potential credential leaks")
        
        print("✅ No hardcoded credentials found")
    
    def test_gitignore_includes_env(self):
        """Verify .gitignore includes .env"""
        if not os.path.exists('.gitignore'):
            pytest.skip(".gitignore not found")
        
        with open('.gitignore', 'r') as f:
            content = f.read()
        
        assert '.env' in content, ".env not in .gitignore!"
        print("✅ .env is in .gitignore")
