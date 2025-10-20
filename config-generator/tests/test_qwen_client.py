import pytest
from unittest.mock import Mock, patch
import httpx

from generator.qwen_client import QwenClient


@pytest.fixture
def qwen_client():
    return QwenClient(base_url="http://localhost:11434", model="qwen:7b")


def test_qwen_client_initialization():
    """Test QwenClient initialization with default parameters"""
    client = QwenClient()
    assert client.base_url == "http://localhost:11434"
    assert client.model == "qwen:7b"
    assert client.timeout == 120.0


def test_qwen_client_custom_params():
    """Test QwenClient initialization with custom parameters"""
    client = QwenClient(
        base_url="http://custom:8080",
        model="custom-model",
        timeout=60.0
    )
    assert client.base_url == "http://custom:8080"
    assert client.model == "custom-model"
    assert client.timeout == 60.0


@patch.object(httpx.Client, 'post')
def test_generate_success(mock_post, qwen_client):
    """Test successful generation from Qwen model"""
    mock_response = Mock()
    mock_response.json.return_value = {"response": "Generated YAML content"}
    mock_response.raise_for_status.return_value = None
    mock_post.return_value = mock_response

    result = qwen_client.generate(
        prompt="Test prompt",
        system_prompt="Test system",
        temperature=0.5,
        max_tokens=2048
    )

    assert result == "Generated YAML content"
    mock_post.assert_called_once()

    # Check the call arguments
    call_args = mock_post.call_args
    assert call_args[0][0] == "http://localhost:11434/api/generate"

    payload = call_args[1]["json"]
    assert payload["model"] == "qwen:7b"
    assert payload["prompt"] == "Test prompt"
    assert payload["system"] == "Test system"
    assert payload["temperature"] == 0.5
    assert payload["stream"] is False
    assert payload["options"]["num_predict"] == 2048


@patch.object(httpx.Client, 'post')
def test_generate_http_error(mock_post, qwen_client):
    """Test HTTP error handling in generation"""
    mock_post.side_effect = httpx.HTTPError("Connection error")

    with pytest.raises(RuntimeError) as exc_info:
        qwen_client.generate("Test prompt")

    assert "Failed to call Qwen model" in str(exc_info.value)


@patch.object(httpx.Client, 'post')
def test_generate_empty_response(mock_post, qwen_client):
    """Test handling of empty response from API"""
    mock_response = Mock()
    mock_response.json.return_value = {}
    mock_response.raise_for_status.return_value = None
    mock_post.return_value = mock_response

    result = qwen_client.generate("Test prompt")
    assert result == ""


def test_close(qwen_client):
    """Test closing the HTTP client"""
    with patch.object(qwen_client.client, 'close') as mock_close:
        qwen_client.close()
        mock_close.assert_called_once()