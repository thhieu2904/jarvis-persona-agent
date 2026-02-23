"""
Unit tests for image upload helpers in agent router.
Tests the pure functions _build_multimodal_content and _build_db_content.
"""

import pytest
from app.features.agent.router import _build_multimodal_content, _build_db_content


# -- _build_multimodal_content --

class TestBuildMultimodalContent:
    def test_no_images_returns_string(self):
        result = _build_multimodal_content("Hello", None)
        assert result == "Hello"

    def test_empty_images_returns_string(self):
        result = _build_multimodal_content("Hello", [])
        assert result == "Hello"

    def test_single_image_returns_list(self):
        result = _build_multimodal_content("Describe this", ["https://example.com/img.jpg"])
        assert isinstance(result, list)
        assert len(result) == 2  # 1 image + 1 text
        assert result[0] == {"type": "image_url", "image_url": {"url": "https://example.com/img.jpg"}}
        assert result[1] == {"type": "text", "text": "Describe this"}

    def test_multiple_images(self):
        urls = ["https://example.com/a.jpg", "https://example.com/b.png"]
        result = _build_multimodal_content("Compare these", urls)
        assert isinstance(result, list)
        assert len(result) == 3  # 2 images + 1 text
        assert result[0]["type"] == "image_url"
        assert result[1]["type"] == "image_url"
        assert result[2] == {"type": "text", "text": "Compare these"}

    def test_image_urls_preserved_exactly(self):
        url = "https://abc.supabase.co/storage/v1/object/public/chat-uploads/user123/file.webp"
        result = _build_multimodal_content("Check this", [url])
        assert result[0]["image_url"]["url"] == url


# -- _build_db_content --

class TestBuildDbContent:
    def test_no_images_returns_original(self):
        result = _build_db_content("Hello world", None)
        assert result == "Hello world"

    def test_empty_images_returns_original(self):
        result = _build_db_content("Hello world", [])
        assert result == "Hello world"

    def test_single_image_prepends_markdown(self):
        result = _build_db_content("What is this?", ["https://example.com/img.jpg"])
        assert result == "![image](https://example.com/img.jpg)\n\nWhat is this?"

    def test_multiple_images_prepends_all(self):
        urls = ["https://example.com/a.jpg", "https://example.com/b.png"]
        result = _build_db_content("Compare", urls)
        expected = "![image](https://example.com/a.jpg)\n![image](https://example.com/b.png)\n\nCompare"
        assert result == expected

    def test_markdown_is_valid_for_rendering(self):
        result = _build_db_content("Test", ["https://example.com/img.jpg"])
        # Should contain standard markdown image syntax
        assert "![image](" in result
        assert result.endswith("Test")
