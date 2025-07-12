"""Tests for the pixell list command."""

import pytest
from click.testing import CliRunner
from pixell.cli.main import cli
from pixell.core.registry import Registry, AgentInfo, SubAgent
import json
import tempfile
import shutil
from pathlib import Path
from datetime import datetime


class TestListCommand:
    """Test the list command functionality."""
    
    @pytest.fixture
    def temp_registry(self):
        """Create a temporary registry for testing."""
        temp_dir = tempfile.mkdtemp()
        registry = Registry(registry_path=Path(temp_dir))
        
        # Add test agents
        test_agents = [
            AgentInfo(
                name="test-agent-1",
                display_name="Test Agent One",
                version="1.0.0",
                description="A test agent for unit testing",
                author="Test Author",
                license="MIT",
                capabilities=["testing", "demo"],
                tags=["test", "sample"],
                sub_agents=[
                    SubAgent(
                        name="sub-test",
                        description="Test sub-agent",
                        endpoint="/test",
                        capabilities=["testing"],
                        public=True
                    )
                ]
            ),
            AgentInfo(
                name="test-agent-2",
                display_name="Test Agent Two",
                version="2.0.0",
                description="Another test agent",
                author="Test Corp",
                license="Apache-2.0",
                extensive_description="This is a longer description for testing.",
                tags=["test", "example", "nlp"]
            )
        ]
        
        for agent in test_agents:
            registry.register_agent(agent)
        
        yield registry
        
        # Cleanup
        shutil.rmtree(temp_dir)
    
    def test_list_command_exists(self):
        """Test that the list command exists and has help."""
        runner = CliRunner()
        result = runner.invoke(cli, ['list', '--help'])
        
        assert result.exit_code == 0
        assert 'List installed agents' in result.output
        assert '--format' in result.output
        assert '--search' in result.output
        assert '--show-sub-agents' in result.output
        assert '--help' in result.output
    
    def test_list_table_format(self):
        """Test list command with table format."""
        runner = CliRunner()
        result = runner.invoke(cli, ['list'])
        
        assert result.exit_code == 0
        # Should either show agents or indicate loading sample agents
        assert ('Loading sample agents' in result.output or 
                'Name' in result.output and 'Version' in result.output)
    
    def test_list_json_format(self):
        """Test list command with JSON format."""
        runner = CliRunner()
        result = runner.invoke(cli, ['list', '--format', 'json'])
        
        assert result.exit_code == 0
        
        # Extract JSON from output
        lines = result.output.strip().split('\n')
        # Find where JSON starts (after any messages)
        json_start = -1
        for i, line in enumerate(lines):
            if line.strip().startswith('[') or line.strip().startswith('{'):
                json_start = i
                break
        
        if json_start >= 0:
            json_output = '\n'.join(lines[json_start:])
            
            # Verify it's valid JSON
            try:
                data = json.loads(json_output)
                assert isinstance(data, list)  # Should be a list of agents
                
                # If agents are loaded, verify structure
                if data:
                    agent = data[0]
                    assert 'name' in agent
                    assert 'version' in agent
                    assert 'description' in agent
                    assert 'author' in agent
            except json.JSONDecodeError as e:
                pytest.fail(f"Output is not valid JSON: {e}")
    
    def test_list_detailed_format(self):
        """Test list command with detailed format."""
        runner = CliRunner()
        result = runner.invoke(cli, ['list', '--format', 'detailed'])
        
        assert result.exit_code == 0
        
        # Detailed format should show extensive information
        if 'Loading sample agents' not in result.output:
            # Check for detailed sections
            assert any(keyword in result.output for keyword in [
                'Package name:', 'Author:', 'License:', 
                'Capabilities:', 'Technical Details:'
            ])
    
    def test_list_with_search(self):
        """Test list command with search functionality."""
        runner = CliRunner()
        
        # Search for something that likely exists in sample data
        result = runner.invoke(cli, ['list', '--search', 'text'])
        assert result.exit_code == 0
        
        # Search for something that likely doesn't exist
        result = runner.invoke(cli, ['list', '--search', 'nonexistentxyz123'])
        assert result.exit_code == 0
        assert ('No agents found matching' in result.output or
                'Loading sample agents' in result.output)
    
    def test_list_show_sub_agents(self):
        """Test list command with sub-agents flag."""
        runner = CliRunner()
        result = runner.invoke(cli, ['list', '--show-sub-agents'])
        
        assert result.exit_code == 0
        
        # If agents with sub-agents are shown, check for indication
        if 'Loading sample agents' not in result.output and 'Total:' in result.output:
            # Sub-agents would be shown with indentation
            assert ('└─' in result.output or 'No agents' in result.output)
    
    def test_list_invalid_format(self):
        """Test list command with invalid format."""
        runner = CliRunner()
        result = runner.invoke(cli, ['list', '--format', 'invalid'])
        
        assert result.exit_code != 0
        assert 'Invalid value for' in result.output
    
    def test_list_combined_options(self):
        """Test list command with multiple options."""
        runner = CliRunner()
        
        # Test search with JSON format
        result = runner.invoke(cli, ['list', '--search', 'test', '--format', 'json'])
        assert result.exit_code == 0
        
        # Test search with detailed format
        result = runner.invoke(cli, ['list', '--search', 'test', '--format', 'detailed'])
        assert result.exit_code == 0
    
    def test_registry_integration(self, temp_registry):
        """Test that the registry module works correctly."""
        # Test listing agents
        agents = temp_registry.list_agents()
        assert len(agents) == 2
        assert agents[0].name == "test-agent-1"
        assert agents[1].name == "test-agent-2"
        
        # Test searching
        results = temp_registry.search_agents("nlp")
        assert len(results) == 1
        assert results[0].name == "test-agent-2"
        
        # Test getting specific agent
        agent = temp_registry.get_agent("test-agent-1")
        assert agent is not None
        assert agent.display_name == "Test Agent One"
        assert len(agent.sub_agents) == 1
        
        # Test JSON serialization
        agent_dict = agent.to_dict()
        assert agent_dict['name'] == "test-agent-1"
        assert 'install_date' in agent_dict
        
        # Test removing agent
        assert temp_registry.unregister_agent("test-agent-1") is True
        assert temp_registry.get_agent("test-agent-1") is None


# Backwards compatibility - keep individual test functions
def test_list_command_exists():
    """Test that the list command exists."""
    test = TestListCommand()
    test.test_list_command_exists()


def test_list_command_table_format():
    """Test list command with default table format."""
    test = TestListCommand()
    test.test_list_table_format()


def test_list_command_json_format():
    """Test list command with JSON format."""
    test = TestListCommand()
    test.test_list_json_format()


def test_list_command_invalid_format():
    """Test list command with invalid format option."""
    test = TestListCommand()
    test.test_list_invalid_format()