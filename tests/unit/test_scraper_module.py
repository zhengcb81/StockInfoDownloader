"""
Scraper Module Tests
Tests for web scraper functionality
"""

from unittest.mock import MagicMock, patch

import pytest
from selenium.common.exceptions import NoSuchElementException, TimeoutException

from src.web.scraper import WebScraper


class TestWebScraper:
    """WebScraper class tests"""

    def test_init(self):
        """Test initialization"""
        mock_driver = MagicMock()
        scraper = WebScraper(mock_driver)
        assert scraper.driver is mock_driver

    def test_find_element_by_css_found(self):
        """Test finding element by CSS when element exists"""
        mock_driver = MagicMock()
        mock_element = MagicMock()
        mock_driver.find_element.return_value = mock_element

        with patch("src.web.scraper.WebDriverWait") as mock_wait:
            mock_wait_instance = MagicMock()
            mock_wait_instance.until.return_value = mock_element
            mock_wait.return_value = mock_wait_instance

            scraper = WebScraper(mock_driver)
            result = scraper.find_element_by_css("#test-element")

            assert result is mock_element

    def test_find_element_by_css_not_found(self):
        """Test finding element by CSS when element doesn't exist"""
        mock_driver = MagicMock()

        with patch("src.web.scraper.WebDriverWait") as mock_wait:
            mock_wait_instance = MagicMock()
            mock_wait_instance.until.side_effect = TimeoutException("Element not found")
            mock_wait.return_value = mock_wait_instance

            scraper = WebScraper(mock_driver)
            result = scraper.find_element_by_css("#non-existent")

            assert result is None

    def test_find_elements_by_css_found(self):
        """Test finding elements by CSS when elements exist"""
        mock_driver = MagicMock()
        mock_elements = [MagicMock(), MagicMock(), MagicMock()]

        with patch("src.web.scraper.WebDriverWait") as mock_wait:
            mock_wait_instance = MagicMock()
            mock_wait_instance.until.return_value = mock_elements
            mock_wait.return_value = mock_wait_instance

            scraper = WebScraper(mock_driver)
            result = scraper.find_elements_by_css(".test-class")

            assert result == mock_elements
            assert len(result) == 3

    def test_find_elements_by_css_not_found(self):
        """Test finding elements by CSS when no elements exist"""
        mock_driver = MagicMock()

        with patch("src.web.scraper.WebDriverWait") as mock_wait:
            mock_wait_instance = MagicMock()
            mock_wait_instance.until.side_effect = TimeoutException("Elements not found")
            mock_wait.return_value = mock_wait_instance

            scraper = WebScraper(mock_driver)
            result = scraper.find_elements_by_css(".non-existent")

            assert result == []

    def test_find_elements_by_xpath(self):
        """Test finding elements by XPath"""
        mock_driver = MagicMock()
        mock_elements = [MagicMock(), MagicMock()]

        with patch("src.web.scraper.WebDriverWait") as mock_wait:
            mock_wait_instance = MagicMock()
            mock_wait_instance.until.return_value = mock_elements
            mock_wait.return_value = mock_wait_instance

            scraper = WebScraper(mock_driver)
            result = scraper.find_elements_by_xpath("//div[@class='test']")

            assert result == mock_elements

    def test_get_text_by_css(self):
        """Test getting text by CSS selector"""
        mock_driver = MagicMock()
        mock_element = MagicMock()
        mock_element.text = "Test Text"

        with patch("src.web.scraper.WebDriverWait") as mock_wait:
            mock_wait_instance = MagicMock()
            mock_wait_instance.until.return_value = mock_element
            mock_wait.return_value = mock_wait_instance

            scraper = WebScraper(mock_driver)
            result = scraper.get_text_by_css("#test-element")

            assert result == "Test Text"

    def test_get_text_by_css_not_found(self):
        """Test getting text by CSS when element doesn't exist"""
        mock_driver = MagicMock()

        with patch("src.web.scraper.WebDriverWait") as mock_wait:
            mock_wait_instance = MagicMock()
            mock_wait_instance.until.side_effect = TimeoutException("Element not found")
            mock_wait.return_value = mock_wait_instance

            scraper = WebScraper(mock_driver)
            result = scraper.get_text_by_css("#non-existent")

            assert result is None

    def test_get_attribute_by_css(self):
        """Test getting attribute by CSS selector"""
        mock_driver = MagicMock()
        mock_element = MagicMock()
        mock_element.get_attribute.return_value = "attribute-value"

        with patch("src.web.scraper.WebDriverWait") as mock_wait:
            mock_wait_instance = MagicMock()
            mock_wait_instance.until.return_value = mock_element
            mock_wait.return_value = mock_wait_instance

            scraper = WebScraper(mock_driver)
            result = scraper.get_attribute_by_css("#test-element", "href")

            assert result == "attribute-value"
            mock_element.get_attribute.assert_called_once_with("href")

    def test_extract_links(self):
        """Test extracting links from page"""
        mock_driver = MagicMock()
        mock_element1 = MagicMock()
        mock_element1.text = "Link 1"
        mock_element1.get_attribute.return_value = "https://example.com/1"

        mock_element2 = MagicMock()
        mock_element2.text = "Link 2"
        mock_element2.get_attribute.return_value = "https://example.com/2"

        with patch("src.web.scraper.WebDriverWait") as mock_wait:
            mock_wait_instance = MagicMock()
            mock_wait_instance.until.return_value = [mock_element1, mock_element2]
            mock_wait.return_value = mock_wait_instance

            scraper = WebScraper(mock_driver)
            links = scraper.extract_links("a")

            assert len(links) == 2
            assert links[0] == {"text": "Link 1", "href": "https://example.com/1"}
            assert links[1] == {"text": "Link 2", "href": "https://example.com/2"}

    def test_extract_links_with_base_url(self):
        """Test extracting links with base URL for relative paths"""
        mock_driver = MagicMock()
        mock_element = MagicMock()
        mock_element.text = "Relative Link"
        mock_element.get_attribute.return_value = "/relative-path"

        with patch("src.web.scraper.WebDriverWait") as mock_wait:
            mock_wait_instance = MagicMock()
            mock_wait_instance.until.return_value = [mock_element]
            mock_wait.return_value = mock_wait_instance

            scraper = WebScraper(mock_driver)
            links = scraper.extract_links("a", base_url="https://example.com")

            assert len(links) == 1
            assert links[0]["href"] == "https://example.com/relative-path"

    def test_extract_links_skip_empty_href(self):
        """Test extracting links skips elements without href"""
        mock_driver = MagicMock()
        mock_element = MagicMock()
        mock_element.text = "No Link"
        mock_element.get_attribute.return_value = None

        with patch("src.web.scraper.WebDriverWait") as mock_wait:
            mock_wait_instance = MagicMock()
            mock_wait_instance.until.return_value = [mock_element]
            mock_wait.return_value = mock_wait_instance

            scraper = WebScraper(mock_driver)
            links = scraper.extract_links("a")

            assert len(links) == 0

    def test_extract_table_data(self):
        """Test extracting table data"""
        mock_driver = MagicMock()
        mock_table = MagicMock()

        # Create mock rows
        mock_row1 = MagicMock()
        mock_cell11 = MagicMock()
        mock_cell11.text = "Cell 1-1"
        mock_cell12 = MagicMock()
        mock_cell12.text = "Cell 1-2"

        mock_row1.find_elements.return_value = [mock_cell11, mock_cell12]

        mock_table.find_elements.return_value = [mock_row1]

        with patch("src.web.scraper.WebDriverWait") as mock_wait:
            mock_wait_instance = MagicMock()
            mock_wait_instance.until.return_value = mock_table
            mock_wait.return_value = mock_wait_instance

            scraper = WebScraper(mock_driver)
            table_data = scraper.extract_table_data("table")

            assert len(table_data) == 1
            assert table_data[0] == ["Cell 1-1", "Cell 1-2"]

    def test_extract_table_data_no_table(self):
        """Test extracting table data when no table exists"""
        mock_driver = MagicMock()

        with patch("src.web.scraper.WebDriverWait") as mock_wait:
            mock_wait_instance = MagicMock()
            mock_wait_instance.until.return_value = None
            mock_wait.return_value = mock_wait_instance

            scraper = WebScraper(mock_driver)
            table_data = scraper.extract_table_data("table")

            assert table_data == []

    def test_extract_form_data(self):
        """Test extracting form data"""
        mock_driver = MagicMock()
        mock_form = MagicMock()

        mock_input1 = MagicMock()
        mock_input1.get_attribute.side_effect = lambda attr: "username" if attr == "name" else "value"

        mock_input2 = MagicMock()
        mock_input2.get_attribute.side_effect = lambda attr: "password" if attr == "name" else ""

        mock_form.find_elements.return_value = [mock_input1, mock_input2]

        with patch("src.web.scraper.WebDriverWait") as mock_wait:
            mock_wait_instance = MagicMock()
            mock_wait_instance.until.return_value = mock_form
            mock_wait.return_value = mock_wait_instance

            scraper = WebScraper(mock_driver)
            form_data = scraper.extract_form_data("form")

            assert "username" in form_data
            assert "password" in form_data

    def test_wait_for_element_clickable(self):
        """Test waiting for element to be clickable"""
        mock_driver = MagicMock()

        with patch("src.web.scraper.WebDriverWait") as mock_wait:
            mock_wait_instance = MagicMock()
            mock_wait_instance.until.return_value = True
            mock_wait.return_value = mock_wait_instance

            scraper = WebScraper(mock_driver)
            result = scraper.wait_for_element_clickable("#button")

            assert result is True

    def test_wait_for_element_clickable_timeout(self):
        """Test waiting for element with timeout"""
        mock_driver = MagicMock()

        with patch("src.web.scraper.WebDriverWait") as mock_wait:
            mock_wait_instance = MagicMock()
            mock_wait_instance.until.side_effect = TimeoutException("Element not clickable")
            mock_wait.return_value = mock_wait_instance

            scraper = WebScraper(mock_driver)
            result = scraper.wait_for_element_clickable("#button")

            assert result is False

    def test_scroll_to_element(self):
        """Test scrolling to element"""
        mock_driver = MagicMock()
        mock_element = MagicMock()

        with patch("src.web.scraper.WebDriverWait") as mock_wait:
            mock_wait_instance = MagicMock()
            mock_wait_instance.until.return_value = mock_element
            mock_wait.return_value = mock_wait_instance

            scraper = WebScraper(mock_driver)
            result = scraper.scroll_to_element("#element")

            assert result is True
            mock_driver.execute_script.assert_called_once()

    def test_scroll_to_element_not_found(self):
        """Test scrolling to element when element doesn't exist"""
        mock_driver = MagicMock()

        with patch("src.web.scraper.WebDriverWait") as mock_wait:
            mock_wait_instance = MagicMock()
            mock_wait_instance.until.side_effect = TimeoutException("Element not found")
            mock_wait.return_value = mock_wait_instance

            scraper = WebScraper(mock_driver)
            result = scraper.scroll_to_element("#non-existent")

            assert result is False

    def test_get_page_source(self):
        """Test getting page source"""
        mock_driver = MagicMock()
        mock_driver.page_source = "<html><body>Test</body></html>"

        scraper = WebScraper(mock_driver)
        result = scraper.get_page_source()

        assert result == "<html><body>Test</body></html>"

    def test_get_page_source_exception(self):
        """Test getting page source with exception"""
        mock_driver = MagicMock()
        # Use PropertyMock for property access
        from unittest.mock import PropertyMock
        type(mock_driver).page_source = PropertyMock(side_effect=Exception("Driver error"))

        scraper = WebScraper(mock_driver)
        result = scraper.get_page_source()

        assert result == ""

    def test_has_next_page_true(self):
        """Test checking if next page exists returns true"""
        mock_driver = MagicMock()
        mock_button = MagicMock()
        mock_button.is_enabled.return_value = True
        mock_button.is_displayed.return_value = True
        mock_driver.find_element.return_value = mock_button

        scraper = WebScraper(mock_driver)
        result = scraper.has_next_page()

        assert result is True

    def test_has_next_page_false(self):
        """Test checking if next page exists returns false"""
        mock_driver = MagicMock()
        mock_driver.find_element.side_effect = NoSuchElementException("No next button")

        scraper = WebScraper(mock_driver)
        result = scraper.has_next_page()

        assert result is False

    def test_go_to_next_page_success(self):
        """Test going to next page successfully"""
        mock_driver = MagicMock()
        mock_button = MagicMock()
        mock_button.is_enabled.return_value = True
        mock_button.is_displayed.return_value = True
        mock_driver.find_element.return_value = mock_button

        with patch("src.web.scraper.WebDriverWait") as mock_wait:
            mock_wait_instance = MagicMock()
            mock_wait_instance.until.return_value = True
            mock_wait.return_value = mock_wait_instance

            scraper = WebScraper(mock_driver)
            result = scraper.go_to_next_page()

            assert result is True
            mock_button.click.assert_called_once()

    def test_go_to_next_page_no_next_page(self):
        """Test going to next page when no next page exists"""
        mock_driver = MagicMock()
        mock_driver.find_element.side_effect = NoSuchElementException("No next button")

        scraper = WebScraper(mock_driver)
        result = scraper.go_to_next_page()

        assert result is False

    def test_get_current_page_info(self):
        """Test getting current page info"""
        mock_driver = MagicMock()
        mock_element = MagicMock()
        mock_element.text = "1 / 10"
        mock_driver.find_element.return_value = mock_element

        with patch.object(WebScraper, "has_next_page", return_value=True):
            scraper = WebScraper(mock_driver)
            info = scraper.get_current_page_info()

            assert info["current_page"] == 1
            assert info["total_pages"] == 10
            assert info["has_next"] is True

    def test_get_current_page_info_no_element(self):
        """Test getting page info when no element exists"""
        mock_driver = MagicMock()
        mock_driver.find_element.side_effect = NoSuchElementException("No element")

        with patch.object(WebScraper, "has_next_page", return_value=False):
            scraper = WebScraper(mock_driver)
            info = scraper.get_current_page_info()

            assert info["current_page"] == 1
            assert info["total_pages"] == 1
            assert info["has_next"] is False

    def test_wait_for_page_load(self):
        """Test waiting for page load"""
        mock_driver = MagicMock()
        mock_driver.execute_script.return_value = "complete"

        with patch("src.web.scraper.WebDriverWait") as mock_wait:
            mock_wait_instance = MagicMock()
            mock_wait_instance.until.return_value = True
            mock_wait.return_value = mock_wait_instance

            scraper = WebScraper(mock_driver)
            result = scraper.wait_for_page_load()

            assert result is True

    def test_wait_for_page_load_timeout(self):
        """Test waiting for page load with timeout"""
        mock_driver = MagicMock()

        with patch("src.web.scraper.WebDriverWait") as mock_wait:
            mock_wait_instance = MagicMock()
            mock_wait_instance.until.side_effect = TimeoutException("Page load timeout")
            mock_wait.return_value = mock_wait_instance

            scraper = WebScraper(mock_driver)
            result = scraper.wait_for_page_load()

            assert result is False

    def test_has_table_content_changed(self):
        """Test checking if table content changed"""
        mock_driver = MagicMock()
        mock_table = MagicMock()
        mock_table.text = "New content different from old"
        mock_driver.find_element.return_value = mock_table

        scraper = WebScraper(mock_driver)
        result = scraper._has_table_content_changed("Old content")

        assert result is True

    def test_has_table_content_changed_same(self):
        """Test checking if table content changed when same"""
        mock_driver = MagicMock()
        mock_table = MagicMock()
        mock_table.text = "Same content"
        mock_driver.find_element.return_value = mock_table

        scraper = WebScraper(mock_driver)
        result = scraper._has_table_content_changed("Same content")

        assert result is False

    def test_has_table_content_changed_exception(self):
        """Test checking content changed handles exceptions"""
        mock_driver = MagicMock()
        mock_driver.find_element.side_effect = NoSuchElementException("No table")

        scraper = WebScraper(mock_driver)
        result = scraper._has_table_content_changed("Old content")

        assert result is False
