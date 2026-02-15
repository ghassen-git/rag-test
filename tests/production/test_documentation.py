"""
Test: Documentation Accuracy
Verifies README instructions are accurate
"""
import pytest
import os
import yaml


class TestDocumentation:
    
    def test_required_files_exist(self):
        """Check all files mentioned in README exist"""
        required_files = [
            'docker-compose.yml',
            'requirements.txt',
            '.env.example',
            'README.md',
        ]
        
        missing = [f for f in required_files if not os.path.exists(f)]
        
        assert len(missing) == 0, f"Missing files: {missing}"
        print(f"✅ All required files exist")
    
    def test_architecture_diagram_exists(self):
        """Check architecture diagram exists"""
        diagram_files = [
            'architecture.png',
            'architecture.pdf',
            'architecture.jpg',
            'docs/architecture.png'
        ]
        
        exists = any(os.path.exists(f) for f in diagram_files)
        if not exists:
            print("⚠️  Warning: No architecture diagram found!")
        else:
            print("✅ Architecture diagram exists")
    
    def test_env_example_complete(self):
        """Verify .env.example has all required variables"""
        if not os.path.exists('.env.example'):
            pytest.skip(".env.example not found")
        
        with open('.env.example', 'r') as f:
            env_vars = [line.split('=')[0].strip()
                        for line in f
                        if '=' in line and not line.startswith('#')]
        
        required_vars = [
            'OPENAI_API_KEY',
            'MATHPIX_APP_ID',
            'MATHPIX_APP_KEY',
            'POSTGRES_HOST',
            'POSTGRES_PASSWORD',
            'MONGO_URI',
            'MILVUS_HOST'
        ]
        
        missing = [v for v in required_vars if v not in env_vars]
        
        if missing:
            print(f"⚠️  Missing env vars in .env.example: {missing}")
        else:
            print("✅ .env.example has all required variables")
    
    def test_docker_compose_services(self):
        """Verify docker-compose has required services"""
        if not os.path.exists('docker-compose.yml'):
            pytest.skip("docker-compose.yml not found")
        
        with open('docker-compose.yml', 'r') as f:
            compose = yaml.safe_load(f)
        
        required_services = ['postgres', 'mongo', 'kafka']
        
        if 'services' in compose:
            services = list(compose['services'].keys())
            
            for required in required_services:
                found = any(required in s.lower() for s in services)
                assert found, f"Service '{required}' not found in docker-compose!"
            
            print(f"✅ Docker Compose has required services: {services}")
        else:
            pytest.fail("No 'services' section in docker-compose.yml")
    
    def test_readme_has_setup_instructions(self):
        """Check README has setup instructions"""
        if not os.path.exists('README.md'):
            pytest.skip("README.md not found")
        
        with open('README.md', 'r') as f:
            content = f.read().lower()
        
        # Should mention docker-compose
        assert 'docker-compose up' in content or 'docker compose up' in content, \
            "README missing docker-compose instructions!"
        
        # Should mention .env setup
        assert '.env' in content, "README missing .env setup instructions!"
        
        print("✅ README has setup instructions")
