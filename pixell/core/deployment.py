"""Deployment module for deploying APKG files to Pixell Agent Cloud."""

import os
import time
import json
import zipfile
from pathlib import Path
from typing import Optional, Dict, Any
import requests  # type: ignore
import yaml
from urllib.parse import urljoin


class DeploymentError(Exception):
    """Base exception for deployment errors."""
    pass


class AuthenticationError(DeploymentError):
    """Authentication failed."""
    pass


class InsufficientCreditsError(DeploymentError):
    """Not enough credits for deployment."""
    pass


class ValidationError(DeploymentError):
    """Package validation failed."""
    pass


def extract_version_from_apkg(apkg_file: Path) -> Optional[str]:
    """Extract version from APKG file.
    
    Args:
        apkg_file: Path to the APKG file
        
    Returns:
        Version string if found, None otherwise
    """
    try:
        with zipfile.ZipFile(apkg_file, 'r') as zf:
            # Try to read from .pixell/package.json first (most reliable)
            try:
                with zf.open('.pixell/package.json') as f:
                    package_data = json.load(f)
                    version = package_data.get('manifest', {}).get('metadata', {}).get('version')
                    return str(version) if version is not None else None
            except KeyError:
                pass
            
            # Fallback to agent.yaml
            try:
                with zf.open('agent.yaml') as f:
                    manifest_data = yaml.safe_load(f)
                    version = manifest_data.get('metadata', {}).get('version')
                    return str(version) if version is not None else None
            except KeyError:
                pass
                
    except Exception:
        # If anything fails, return None
        pass
    
    return None


class DeploymentClient:
    """Client for deploying APKG files to Pixell Agent Cloud."""
    
    # Environment configurations
    ENVIRONMENTS = {
        'local': {
            'base_url': 'http://localhost:4000',
            'name': 'Local Development'
        },
        'prod': {
            'base_url': 'https://cloud.pixell.global',
            'name': 'Production'
        }
    }
    
    def __init__(self, environment: str = 'prod', api_key: Optional[str] = None):
        """Initialize deployment client.
        
        Args:
            environment: Deployment environment ('local' or 'prod')
            api_key: Optional API key for authentication
        """
        if environment not in self.ENVIRONMENTS:
            raise ValueError(f"Invalid environment: {environment}. Must be one of: {list(self.ENVIRONMENTS.keys())}")
        
        self.environment = environment
        self.base_url = self.ENVIRONMENTS[environment]['base_url']
        self.api_key = api_key or os.environ.get('PIXELL_API_KEY')
        
        # Session for connection pooling
        self.session = requests.Session()
        if self.api_key:
            self.session.headers['Authorization'] = f'Bearer {self.api_key}'
    
    def deploy(self, 
               app_id: str, 
               apkg_file: Path, 
               version: Optional[str] = None,
               release_notes: Optional[str] = None,
               signature_file: Optional[Path] = None,
               force_overwrite: bool = False) -> Dict[str, Any]:
        """Deploy an APKG file to an agent app.
        
        Args:
            app_id: The agent app ID
            apkg_file: Path to the APKG file
            version: Version string (optional, will extract from package if not provided)
            release_notes: Release notes for this deployment
            signature_file: Path to signature file for signed packages
            force_overwrite: Force overwrite existing version if it exists
            
        Returns:
            Deployment response with status and tracking information
            
        Raises:
            DeploymentError: If deployment fails
            AuthenticationError: If authentication fails
            InsufficientCreditsError: If not enough credits
            ValidationError: If package validation fails
        """
        if not apkg_file.exists():
            raise FileNotFoundError(f"APKG file not found: {apkg_file}")
        
        # Extract version from APKG if not provided
        if not version:
            version = extract_version_from_apkg(apkg_file)
            if not version:
                raise ValidationError("Version not provided and could not be extracted from APKG file")
        
        # Prepare the deployment request
        url = urljoin(self.base_url, f'/api/agent-apps/{app_id}/packages/deploy')
        
        # Prepare files for multipart upload
        files = [
            ('file', ('agent.apkg', open(apkg_file, 'rb'), 'application/octet-stream'))
        ]
        
        # Prepare form data - using list of tuples to ensure proper ordering
        data = [
            ('version', version)  # Version is now always required
        ]
        
        if release_notes:
            data.append(('release_notes', release_notes))
        
        if force_overwrite:
            # Send as form field with string value 'true'
            data.append(('force_overwrite', 'true'))
            
        if signature_file and signature_file.exists():
            files.append(('signature', ('agent.apkg.sig', open(signature_file, 'rb'), 'application/octet-stream')))
        
        try:
            # Send deployment request
            response = self.session.post(url, files=files, data=data, timeout=60)
            
            # Handle different response codes
            if response.status_code == 202:  # Accepted
                return response.json()  # type: ignore  # type: ignore
            elif response.status_code == 400:  # Bad Request
                error_data = response.json()
                raise ValidationError(f"Package validation failed: {error_data.get('details', error_data.get('error'))}")
            elif response.status_code == 401:  # Unauthorized
                raise AuthenticationError("Invalid API key or session. Please check your credentials.")
            elif response.status_code == 402:  # Payment Required
                error_data = response.json()
                raise InsufficientCreditsError(
                    f"Insufficient credits. Required: {error_data.get('required')}, "
                    f"Available: {error_data.get('available')}"
                )
            elif response.status_code == 409:  # Conflict
                error_data = response.json()
                if force_overwrite:
                    # If force was specified but we still got 409, there's an issue
                    raise ValidationError(
                        f"Version {version} conflict occurred even with force overwrite enabled. "
                        f"API response: {error_data.get('error', 'Unknown error')}"
                    )
                else:
                    raise ValidationError(
                        f"Version {version} already exists. Use --force to overwrite existing version."
                    )
            else:
                response.raise_for_status()
                return response.json()  # type: ignore  # type: ignore
                
        except requests.exceptions.RequestException as e:
            raise DeploymentError(f"Deployment request failed: {str(e)}")
        finally:
            # Clean up file handles
            for field_name, file_info in files:
                if isinstance(file_info, tuple) and len(file_info) > 1:
                    file_obj = file_info[1]
                    if hasattr(file_obj, 'close'):
                        file_obj.close()
    
    def get_deployment_status(self, deployment_id: str) -> Dict[str, Any]:
        """Get the status of a deployment.
        
        Args:
            deployment_id: The deployment ID to check
            
        Returns:
            Deployment status information
        """
        url = urljoin(self.base_url, f'/api/deployments/{deployment_id}')
        
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return response.json()  # type: ignore
        except requests.exceptions.RequestException as e:
            raise DeploymentError(f"Failed to get deployment status: {str(e)}")
    
    def wait_for_deployment(self, deployment_id: str, timeout: int = 300) -> Dict[str, Any]:
        """Wait for a deployment to complete.
        
        Args:
            deployment_id: The deployment ID to wait for
            timeout: Maximum time to wait in seconds
            
        Returns:
            Final deployment status
            
        Raises:
            DeploymentError: If deployment fails or times out
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            status = self.get_deployment_status(deployment_id)
            deployment_status = status['deployment']['status']
            
            if deployment_status == 'completed':
                return status
            elif deployment_status == 'failed':
                raise DeploymentError(f"Deployment failed: {status.get('deployment', {}).get('error', 'Unknown error')}")
            
            # Wait before checking again
            time.sleep(5)
        
        raise DeploymentError(f"Deployment timed out after {timeout} seconds")
    
    def get_queue_stats(self) -> Dict[str, Any]:
        """Get deployment queue statistics.
        
        Returns:
            Queue statistics and health information
        """
        url = urljoin(self.base_url, '/api/deployments/queue/stats')
        
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return response.json()  # type: ignore
        except requests.exceptions.RequestException as e:
            raise DeploymentError(f"Failed to get queue stats: {str(e)}")


def get_api_key() -> Optional[str]:
    """Get API key from environment or config file.
    
    Returns:
        API key if found, None otherwise
    """
    # First check environment variable
    api_key = os.environ.get('PIXELL_API_KEY')
    if api_key:
        return api_key
    
    # Check config file
    config_file = Path.home() / '.pixell' / 'config.json'
    if config_file.exists():
        import json
        try:
            with open(config_file) as f:
                config = json.load(f)
                return config.get('api_key')  # type: ignore
        except Exception:
            pass
    
    return None