import os
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from skills_mcp_server.sources.git import GitSource
from skills_mcp_server.sources.base import SourceError

@pytest.fixture
def data_dir(tmp_path):
    d = tmp_path / "data"
    d.mkdir()
    return d

def test_git_source_init(data_dir):
    source = GitSource("test-git", "https://github.com/foo/bar.git", "main", data_dir)
    assert source.name == "test-git"
    assert source.cache_dir == data_dir / "skills" / "test-git"
    assert source.lock_file == data_dir / "locks" / "test-git.lock"

@patch("skills_mcp_server.sources.git.subprocess.run")
@patch("skills_mcp_server.sources.git.LocalSource")
def test_git_source_clone(mock_local_source, mock_run, data_dir):
    # Setup mock local source
    mock_ls_instance = mock_local_source.return_value
    mock_ls_instance.load.return_value = []
    
    mock_run.return_value = MagicMock(stdout="commit123")
    
    source = GitSource("test-git", "https://foo.git", "main", data_dir)
    
    # Run load, which triggers sync -> clone
    with patch.object(source, "_get_commit_sha", return_value="12345"):
        list(source.load())
    
    # Should have called subprocess.run for clone
    calls = mock_run.call_args_list
    assert any("clone" in call[0][0] for call in calls)

@patch("skills_mcp_server.sources.git.subprocess.run")
def test_git_source_fetch_existing(mock_run, data_dir):
    source = GitSource("test-git", "https://foo.git", "main", data_dir)
    
    # Make .git dir to simulate existing cache
    (source.cache_dir / ".git").mkdir(parents=True)
    
    with patch.object(source, "_get_commit_sha", return_value="12345"):
        with patch("skills_mcp_server.sources.git.LocalSource") as mock_local_source:
            mock_local_source.return_value.load.return_value = []
            list(source.load())
    
    calls = mock_run.call_args_list
    # Should have called fetch, not clone
    assert any("fetch" in call[0][0] for call in calls)
    assert not any("clone" in call[0][0] for call in calls)
