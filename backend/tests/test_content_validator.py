import pytest
from processor_app.validators.content_validator import ContentValidator


class TestContentValidator:
    
    def setup_method(self):
        self.validator = ContentValidator()
    
    def test_valid_content(self):
        assert self.validator.validate("Hello123abc") == True
        assert self.validator.validate("Test content 99") == True
        assert self.validator.validate("0123456789") == True
    
    def test_content_too_short(self):
        assert self.validator.validate("short") == False
        assert self.validator.validate("abc1") == False
        assert self.validator.validate("") == False
    
    def test_content_without_digit(self):
        assert self.validator.validate("nobdigithere") == False
        assert self.validator.validate("thisisnotgood") == False
    
    def test_content_exactly_10_chars_with_digit(self):
        assert self.validator.validate("abcdefgh1i") == True
    
    def test_content_exactly_9_chars_with_digit(self):
        assert self.validator.validate("abcdefgh1") == False
    
    def test_content_with_special_chars_and_digit(self):
        assert self.validator.validate("test@123#abc") == True
        assert self.validator.validate("hello-world-5") == True
    
    def test_content_with_spaces_and_digit(self):
        assert self.validator.validate("hello world 123") == True
        assert self.validator.validate("test content 1") == True
    
    def test_content_with_multiple_digits(self):
        assert self.validator.validate("abc123defgh456") == True
    
    def test_content_only_digits(self):
        assert self.validator.validate("1234567890") == True
    
    def test_content_with_unicode(self):
        assert self.validator.validate("héllo wörld 123") == True
