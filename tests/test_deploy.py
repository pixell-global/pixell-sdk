"""Tests for the pixell deploy command and deployment module."""

import pytest
from unittest.mock import Mock, patch, mock_open
from click.testing import CliRunner
from pathlib import Path
import tempfile
import os

from pixell.cli.main import cli
from pixell.core.deployment import (
    DeploymentClient, 
    AuthenticationError, 
    InsufficientCreditsError, 
    ValidationError,
    get_api_key,
    extract_version_from_apkg
)


class TestDeploymentClient:
    """Test the DeploymentClient class."""
    
    def test_init_valid_environment(self):
        """Test initialization with valid environment."""
        client = DeploymentClient(environment='local')
        assert client.environment == 'local'
        assert client.base_url == 'http://localhost:4000'
        
        client = DeploymentClient(environment='prod')
        assert client.environment == 'prod'
        assert client.base_url == 'https://cloud.pixell.global'
    
    def test_init_invalid_environment(self):
        """Test initialization with invalid environment."""
        with pytest.raises(ValueError, match="Invalid environment"):
            DeploymentClient(environment='invalid')
    
    def test_init_with_api_key(self):
        """Test initialization with API key."""
        client = DeploymentClient(environment='prod', api_key='test-key')
        assert client.api_key == 'test-key'
        assert client.session.headers['Authorization'] == 'Bearer test-key'
    
    @patch('pixell.core.deployment.requests.Session.post')
    def test_deploy_success(self, mock_post):
        """Test successful deployment."""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 202
        mock_response.json.return_value = {
            'deployment': {
                'id': 'deploy-123',
                'status': 'queued',
                'queued_at': '2024-01-01T00:00:00Z'
            },
            'package': {
                'id': 'pkg-123',
                'version': '1.0.0',
                'size_bytes': 1024000
            },
            'tracking': {
                'status_url': 'https://api.example.com/deployments/deploy-123'
            }
        }
        mock_post.return_value = mock_response
        
        # Create a temporary file
        with tempfile.NamedTemporaryFile(suffix='.apkg', delete=False) as f:
            f.write(b'mock apkg content')
            apkg_path = Path(f.name)
        
        try:
            client = DeploymentClient(environment='prod', api_key='test-key')
            result = client.deploy('app-123', apkg_path, version='1.0.0')
            
            assert result['deployment']['id'] == 'deploy-123'
            assert result['package']['version'] == '1.0.0'
            
            # Verify the API call
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            assert 'api/agent-apps/app-123/packages/deploy' in call_args[0][0]
            
        finally:
            apkg_path.unlink()  # Clean up
    
    @patch('pixell.core.deployment.requests.Session.post')
    def test_deploy_authentication_error(self, mock_post):
        """Test deployment with authentication error."""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.json.return_value = {'error': 'Invalid API key'}
        mock_post.return_value = mock_response
        
        with tempfile.NamedTemporaryFile(suffix='.apkg', delete=False) as f:
            apkg_path = Path(f.name)
        
        try:
            client = DeploymentClient(environment='prod', api_key='invalid-key')
            
            with pytest.raises(AuthenticationError):
                client.deploy('app-123', apkg_path, version='1.0.0')
        finally:
            apkg_path.unlink()
    
    @patch('pixell.core.deployment.requests.Session.post')
    def test_deploy_insufficient_credits(self, mock_post):
        """Test deployment with insufficient credits."""
        mock_response = Mock()
        mock_response.status_code = 402
        mock_response.json.return_value = {
            'error': 'Insufficient credits',
            'required': 10,
            'available': 5
        }
        mock_post.return_value = mock_response
        
        with tempfile.NamedTemporaryFile(suffix='.apkg', delete=False) as f:
            apkg_path = Path(f.name)
        
        try:
            client = DeploymentClient(environment='prod', api_key='test-key')
            
            with pytest.raises(InsufficientCreditsError, match="Required: 10, Available: 5"):
                client.deploy('app-123', apkg_path, version='1.0.0')
        finally:
            apkg_path.unlink()
    
    @patch('pixell.core.deployment.requests.Session.post')
    def test_deploy_validation_error(self, mock_post):
        """Test deployment with validation error."""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            'error': 'Package validation failed',
            'details': ['Invalid APKG format', 'Missing manifest.json']
        }
        mock_post.return_value = mock_response
        
        with tempfile.NamedTemporaryFile(suffix='.apkg', delete=False) as f:
            apkg_path = Path(f.name)
        
        try:
            client = DeploymentClient(environment='prod', api_key='test-key')
            
            with pytest.raises(ValidationError, match="Package validation failed"):
                client.deploy('app-123', apkg_path, version='1.0.0')
        finally:
            apkg_path.unlink()
    
    def test_deploy_file_not_found(self):
        """Test deployment with non-existent file."""
        client = DeploymentClient(environment='prod', api_key='test-key')
        
        with pytest.raises(FileNotFoundError):
            client.deploy('app-123', Path('/nonexistent/file.apkg'))


class TestGetApiKey:
    """Test the get_api_key function."""
    
    @patch.dict(os.environ, {'PIXELL_API_KEY': 'env-key'})
    def test_get_api_key_from_env(self):
        """Test getting API key from environment variable."""
        assert get_api_key() == 'env-key'
    
    @patch.dict(os.environ, {}, clear=True)
    @patch('builtins.open', new_callable=mock_open, read_data='{"api_key": "config-key"}')
    @patch.object(Path, 'exists')
    @patch('pixell.core.deployment.Path.home')
    def test_get_api_key_from_config(self, mock_home, mock_exists, mock_file):
        """Test getting API key from config file."""
        mock_home.return_value = Path('/fake/home')
        mock_exists.return_value = True
        assert get_api_key() == 'config-key'
    
    @patch.dict(os.environ, {}, clear=True)
    @patch.object(Path, 'exists')
    @patch('pixell.core.deployment.Path.home')
    def test_get_api_key_no_config(self, mock_home, mock_exists):
        """Test getting API key when no config exists."""
        mock_home.return_value = Path('/fake/home')
        mock_exists.return_value = False
        assert get_api_key() is None


class TestVersionExtraction:
    """Test the extract_version_from_apkg function."""
    
    def test_extract_version_from_valid_apkg(self):
        """Test extracting version from a valid APKG file."""
        import zipfile
        import json
        import yaml
        
        # Create a temporary APKG file with version info
        with tempfile.NamedTemporaryFile(suffix='.apkg', delete=False) as f:
            apkg_path = Path(f.name)
        
        try:
            # Create a simple APKG structure
            with zipfile.ZipFile(apkg_path, 'w') as zf:
                # Add agent.yaml with version
                agent_manifest = {
                    'name': 'test-agent',
                    'version': '1.0',
                    'metadata': {
                        'version': '2.1.0'
                    }
                }
                zf.writestr('agent.yaml', yaml.dump(agent_manifest))
                
                # Add package.json with version (more reliable)
                package_meta = {
                    'format_version': '1.0',
                    'manifest': {
                        'metadata': {
                            'version': '2.1.0'
                        }
                    }
                }
                zf.writestr('.pixell/package.json', json.dumps(package_meta))
            
            # Test version extraction
            version = extract_version_from_apkg(apkg_path)
            assert version == '2.1.0'
            
        finally:
            apkg_path.unlink()
    
    def test_extract_version_from_invalid_apkg(self):
        """Test version extraction from invalid APKG file."""
        # Create a temporary file that's not a valid ZIP
        with tempfile.NamedTemporaryFile(suffix='.apkg', delete=False) as f:
            f.write(b'not a zip file')
            apkg_path = Path(f.name)
        
        try:
            version = extract_version_from_apkg(apkg_path)
            assert version is None
        finally:
            apkg_path.unlink()
    
    def test_extract_version_missing_metadata(self):
        """Test version extraction when metadata is missing."""
        import zipfile
        
        with tempfile.NamedTemporaryFile(suffix='.apkg', delete=False) as f:
            apkg_path = Path(f.name)
        
        try:
            # Create APKG without version info
            with zipfile.ZipFile(apkg_path, 'w') as zf:
                zf.writestr('some_file.txt', 'no version here')
            
            version = extract_version_from_apkg(apkg_path)
            assert version is None
            
        finally:
            apkg_path.unlink()


class TestDeployCommand:
    """Test the deploy CLI command."""
    
    def test_deploy_command_help(self):
        """Test that the deploy command exists and has help."""
        runner = CliRunner()
        result = runner.invoke(cli, ['deploy', '--help'])
        
        assert result.exit_code == 0
        assert 'Deploy an APKG file to Pixell Agent Cloud' in result.output
        assert '--apkg-file' in result.output
        assert '--env' in result.output
        assert '--app-id' in result.output
    
    def test_deploy_command_missing_api_key(self):
        """Test deploy command without API key."""
        runner = CliRunner()
        
        with tempfile.NamedTemporaryFile(suffix='.apkg', delete=False) as f:
            apkg_path = f.name
        
        try:
            with patch.dict(os.environ, {}, clear=True):
                with patch('pixell.core.deployment.get_api_key', return_value=None):
                    result = runner.invoke(cli, [
                        'deploy', 
                        '--apkg-file', apkg_path,
                        '--app-id', 'test-app'
                    ])
                    
                    assert result.exit_code == 1
                    assert 'No API key provided' in result.output
        finally:
            Path(apkg_path).unlink()
    
    def test_deploy_command_missing_required_args(self):
        """Test deploy command without required arguments."""
        runner = CliRunner()
        result = runner.invoke(cli, ['deploy'])
        
        assert result.exit_code != 0
        assert 'Missing option' in result.output
    
    @patch('pixell.core.deployment.DeploymentClient')
    def test_deploy_command_success(self, mock_client_class):
        """Test successful deploy command."""
        # Mock the deployment client
        mock_client = Mock()
        mock_client.ENVIRONMENTS = {
            'prod': {'name': 'Production'},
            'local': {'name': 'Local Development'}
        }
        mock_client.base_url = 'https://api.example.com'
        mock_client.deploy.return_value = {
            'deployment': {
                'id': 'deploy-123',
                'status': 'queued',
                'queued_at': '2024-01-01T00:00:00Z'
            },
            'package': {
                'id': 'pkg-123',
                'version': '1.0.0',
                'size_bytes': 1024000
            },
            'tracking': {
                'status_url': 'https://api.example.com/deployments/deploy-123'
            }
        }
        mock_client_class.return_value = mock_client
        
        runner = CliRunner()
        
        with tempfile.NamedTemporaryFile(suffix='.apkg', delete=False) as f:
            apkg_path = f.name
        
        try:
            with patch('pixell.core.deployment.get_api_key', return_value='test-key'):
                result = runner.invoke(cli, [
                    'deploy',
                    '--apkg-file', apkg_path,
                    '--app-id', 'test-app',
                    '--version', '1.0.0'
                ])
                
                assert result.exit_code == 0
                assert 'Deployment initiated successfully!' in result.output
                assert 'deploy-123' in result.output
                
                # Verify deployment was called
                mock_client.deploy.assert_called_once()
        finally:
            Path(apkg_path).unlink()
    
    @patch('pixell.core.deployment.DeploymentClient')
    def test_deploy_command_with_environment(self, mock_client_class):
        """Test deploy command with different environment."""
        mock_client = Mock()
        mock_client.ENVIRONMENTS = {
            'local': {'name': 'Local Development'}
        }
        mock_client.base_url = 'http://localhost:4000'
        mock_client.deploy.return_value = {
            'deployment': {'id': 'deploy-123', 'status': 'queued', 'queued_at': '2024-01-01T00:00:00Z'},
            'package': {'id': 'pkg-123', 'version': '1.0.0', 'size_bytes': 1024},
            'tracking': {'status_url': 'http://localhost:4000/deployments/deploy-123'}
        }
        mock_client_class.return_value = mock_client
        
        runner = CliRunner()
        
        with tempfile.NamedTemporaryFile(suffix='.apkg', delete=False) as f:
            apkg_path = f.name
        
        try:
            with patch('pixell.core.deployment.get_api_key', return_value='test-key'):
                result = runner.invoke(cli, [
                    'deploy',
                    '--apkg-file', apkg_path,
                    '--app-id', 'test-app',
                    '--env', 'local'
                ])
                
                assert result.exit_code == 0
                assert 'Local Development' in result.output
                assert 'localhost:4000' in result.output
                
                # Verify client was created with correct environment
                mock_client_class.assert_called_with(environment='local', api_key='test-key')
        finally:
            Path(apkg_path).unlink()