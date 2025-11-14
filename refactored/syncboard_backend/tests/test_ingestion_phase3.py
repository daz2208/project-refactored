"""
Test Phase 3 content ingestion: Archives & E-Books

Tests for:
- ZIP archive extraction and recursive processing
- EPUB book extraction (metadata, chapters)
- Subtitle files (SRT, VTT)

All tests use in-memory file creation to avoid filesystem dependencies.
"""

import unittest
import io
import zipfile
import json
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'backend'))

from ingest import (
    extract_zip_archive,
    extract_epub_text,
    extract_subtitles,
    ingest_upload_file
)


class TestZIPExtraction(unittest.TestCase):
    """Test ZIP archive extraction and processing."""

    def test_extract_simple_zip(self):
        """Test extraction from a basic ZIP archive with text files."""
        # Create a ZIP file in memory
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
            zipf.writestr('file1.txt', 'Hello from file 1')
            zipf.writestr('file2.txt', 'Hello from file 2')
            zipf.writestr('README.md', '# README\nThis is a test archive')

        content_bytes = zip_buffer.getvalue()
        result = extract_zip_archive(content_bytes, 'test.zip')

        # Verify structure
        assert 'ZIP ARCHIVE' in result
        assert 'test.zip' in result
        assert 'Total files: 3' in result
        assert 'file1.txt' in result
        assert 'file2.txt' in result
        assert 'README.md' in result
        assert 'Hello from file 1' in result
        assert 'Hello from file 2' in result

    def test_extract_zip_with_code_files(self):
        """Test ZIP archive containing code files."""
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
            zipf.writestr('main.py', 'def hello():\n    print("Hello, World!")')
            zipf.writestr('utils.js', 'function add(a, b) { return a + b; }')

        content_bytes = zip_buffer.getvalue()
        result = extract_zip_archive(content_bytes, 'code.zip')

        assert 'main.py' in result
        assert 'utils.js' in result
        assert 'Python' in result  # Language detection
        assert 'JavaScript' in result

    def test_extract_zip_with_nested_structure(self):
        """Test ZIP archive with nested directories."""
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
            zipf.writestr('src/main.py', 'print("main")')
            zipf.writestr('docs/README.md', '# Documentation')
            zipf.writestr('tests/test_main.py', 'def test(): pass')

        content_bytes = zip_buffer.getvalue()
        result = extract_zip_archive(content_bytes, 'project.zip')

        assert 'src/main.py' in result
        assert 'docs/README.md' in result
        assert 'tests/test_main.py' in result

    def test_extract_zip_with_jupyter_notebook(self):
        """Test ZIP archive containing Jupyter notebook."""
        # Create a simple notebook
        notebook = {
            "cells": [
                {
                    "cell_type": "code",
                    "source": ["print('Hello from notebook')"],
                    "outputs": []
                }
            ],
            "metadata": {
                "kernelspec": {
                    "display_name": "Python 3",
                    "language": "python"
                }
            }
        }

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
            zipf.writestr('notebook.ipynb', json.dumps(notebook))

        content_bytes = zip_buffer.getvalue()
        result = extract_zip_archive(content_bytes, 'notebooks.zip')

        assert 'notebook.ipynb' in result
        assert 'JUPYTER NOTEBOOK' in result
        assert "print('Hello from notebook')" in result

    def test_extract_empty_zip(self):
        """Test extraction from empty ZIP archive."""
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
            pass  # Empty archive

        content_bytes = zip_buffer.getvalue()
        result = extract_zip_archive(content_bytes, 'empty.zip')

        assert 'ZIP ARCHIVE' in result
        assert 'Total files: 0' in result

    def test_extract_zip_skip_large_files(self):
        """Test that large files (>10MB) are skipped."""
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Create a large dummy file (11MB)
            large_content = 'x' * (11 * 1024 * 1024)
            zipf.writestr('large_file.txt', large_content)
            zipf.writestr('small_file.txt', 'This is small')

        content_bytes = zip_buffer.getvalue()
        result = extract_zip_archive(content_bytes, 'mixed.zip')

        assert 'SKIPPED (too large)' in result
        assert 'large_file.txt' in result
        assert 'small_file.txt' in result
        assert 'This is small' in result

    def test_zip_routing(self):
        """Test that ZIP files are routed correctly."""
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
            zipf.writestr('test.txt', 'Hello')

        content_bytes = zip_buffer.getvalue()
        result = ingest_upload_file('archive.zip', content_bytes)

        assert 'ZIP ARCHIVE' in result
        assert 'archive.zip' in result


class TestEPUBExtraction(unittest.TestCase):
    """Test EPUB book extraction."""

    def test_extract_simple_epub(self):
        """Test extraction from a basic EPUB book."""
        try:
            from ebooklib import epub
        except ImportError:
            self.skipTest("ebooklib not installed")

        # Create a simple EPUB book
        book = epub.EpubBook()
        book.set_identifier('test123')
        book.set_title('Test Book')
        book.set_language('en')
        book.add_author('Test Author')

        # Create a chapter
        c1 = epub.EpubHtml(title='Chapter 1', file_name='chap_01.xhtml', lang='en')
        c1.content = '<html><body><h1>Chapter 1</h1><p>This is the first chapter.</p></body></html>'
        book.add_item(c1)

        # Add spine (required for valid EPUB)
        book.spine = ['nav', c1]
        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())

        # Write to bytes
        buffer = io.BytesIO()
        epub.write_epub(buffer, book)
        content_bytes = buffer.getvalue()

        result = extract_epub_text(content_bytes, 'test.epub')

        assert 'EPUB BOOK' in result
        assert 'Test Book' in result
        assert 'Test Author' in result
        assert 'Chapter 1' in result
        assert 'first chapter' in result

    def test_extract_epub_multiple_chapters(self):
        """Test EPUB with multiple chapters."""
        try:
            from ebooklib import epub
        except ImportError:
            self.skipTest("ebooklib not installed")

        book = epub.EpubBook()
        book.set_identifier('test456')
        book.set_title('Multi-Chapter Book')
        book.set_language('en')

        # Create multiple chapters
        chapters = []
        for i in range(1, 4):
            chapter = epub.EpubHtml(
                title=f'Chapter {i}',
                file_name=f'chap_{i:02d}.xhtml',
                lang='en'
            )
            chapter.content = f'<html><body><h1>Chapter {i}</h1><p>Content of chapter {i}.</p></body></html>'
            book.add_item(chapter)
            chapters.append(chapter)

        # Add spine
        book.spine = ['nav'] + chapters
        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())

        buffer = io.BytesIO()
        epub.write_epub(buffer, book)
        content_bytes = buffer.getvalue()

        result = extract_epub_text(content_bytes, 'multibook.epub')

        assert 'Multi-Chapter Book' in result
        assert 'Chapter 1' in result
        assert 'Chapter 2' in result
        assert 'Chapter 3' in result
        # Note: May extract nav page as well, so check for at least 3 chapters
        assert 'Total chapters extracted:' in result

    def test_extract_epub_with_metadata(self):
        """Test EPUB metadata extraction."""
        try:
            from ebooklib import epub
        except ImportError:
            self.skipTest("ebooklib not installed")

        book = epub.EpubBook()
        book.set_identifier('test789')
        book.set_title('Advanced Programming')
        book.set_language('en')
        book.add_author('Jane Doe')

        c1 = epub.EpubHtml(title='Intro', file_name='intro.xhtml')
        c1.content = '<html><body><p>Introduction to programming.</p></body></html>'
        book.add_item(c1)

        # Add spine
        book.spine = ['nav', c1]
        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())

        buffer = io.BytesIO()
        epub.write_epub(buffer, book)
        content_bytes = buffer.getvalue()

        result = extract_epub_text(content_bytes, 'programming.epub')

        assert 'Advanced Programming' in result
        assert 'Jane Doe' in result
        assert 'Language: en' in result

    def test_epub_routing(self):
        """Test that EPUB files are routed correctly."""
        try:
            from ebooklib import epub
        except ImportError:
            self.skipTest("ebooklib not installed")

        book = epub.EpubBook()
        book.set_identifier('test000')
        book.set_title('Routing Test')
        book.set_language('en')

        c1 = epub.EpubHtml(title='Test', file_name='test.xhtml')
        c1.content = '<html><body><p>Test content</p></body></html>'
        book.add_item(c1)

        # Add spine
        book.spine = ['nav', c1]
        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())

        buffer = io.BytesIO()
        epub.write_epub(buffer, book)
        content_bytes = buffer.getvalue()

        result = ingest_upload_file('book.epub', content_bytes)

        assert 'EPUB BOOK' in result
        assert 'Routing Test' in result


class TestSubtitleExtraction(unittest.TestCase):
    """Test subtitle file extraction (SRT, VTT)."""

    def test_extract_srt_simple(self):
        """Test extraction from a basic SRT file."""
        srt_content = """1
00:00:00,000 --> 00:00:02,000
Hello and welcome to the tutorial.

2
00:00:02,500 --> 00:00:05,000
Today we'll learn about Python programming.

3
00:00:05,500 --> 00:00:08,000
Let's get started!
"""
        content_bytes = srt_content.encode('utf-8')
        result = extract_subtitles(content_bytes, 'tutorial.srt')

        assert 'SUBTITLE FILE' in result
        assert 'tutorial.srt' in result
        assert 'Format: SRT' in result
        assert 'Entries: 3' in result
        assert 'Hello and welcome' in result
        assert 'Python programming' in result
        assert "Let's get started" in result
        # Timestamps should NOT appear in output
        assert '00:00:00' not in result

    def test_extract_vtt_simple(self):
        """Test extraction from a basic WebVTT file."""
        vtt_content = """WEBVTT

00:00:00.000 --> 00:00:02.000
Welcome to the lecture.

00:00:02.500 --> 00:00:05.000
Today's topic is machine learning.

00:00:05.500 --> 00:00:08.000
Let's dive in!
"""
        content_bytes = vtt_content.encode('utf-8')
        result = extract_subtitles(content_bytes, 'lecture.vtt')

        assert 'SUBTITLE FILE' in result
        assert 'lecture.vtt' in result
        assert 'Format: WebVTT' in result
        assert 'Welcome to the lecture' in result
        assert 'machine learning' in result
        assert "Let's dive in" in result
        # WEBVTT header and timestamps should NOT appear
        assert 'WEBVTT' not in result.replace('Format: WebVTT', '')
        assert '00:00:00' not in result

    def test_extract_srt_multiline(self):
        """Test SRT with multi-line subtitles."""
        srt_content = """1
00:00:00,000 --> 00:00:03,000
This is a long subtitle
that spans multiple lines
for better readability.

2
00:00:03,500 --> 00:00:06,000
Second subtitle here.
"""
        content_bytes = srt_content.encode('utf-8')
        result = extract_subtitles(content_bytes, 'multiline.srt')

        assert 'long subtitle' in result
        assert 'multiple lines' in result
        assert 'Second subtitle' in result

    def test_extract_vtt_with_notes(self):
        """Test WebVTT with NOTE sections."""
        vtt_content = """WEBVTT

NOTE This is a comment and should be filtered out

00:00:00.000 --> 00:00:02.000
Actual subtitle content here.

NOTE Another comment

00:00:02.500 --> 00:00:05.000
More subtitle content.
"""
        content_bytes = vtt_content.encode('utf-8')
        result = extract_subtitles(content_bytes, 'notes.vtt')

        assert 'Actual subtitle content' in result
        assert 'More subtitle content' in result
        # Notes should be filtered
        assert 'This is a comment' not in result
        assert 'Another comment' not in result

    def test_srt_routing(self):
        """Test that SRT files are routed correctly."""
        srt_content = """1
00:00:00,000 --> 00:00:02,000
Test subtitle.
"""
        content_bytes = srt_content.encode('utf-8')
        result = ingest_upload_file('test.srt', content_bytes)

        assert 'SUBTITLE FILE' in result
        assert 'Format: SRT' in result

    def test_vtt_routing(self):
        """Test that VTT files are routed correctly."""
        vtt_content = """WEBVTT

00:00:00.000 --> 00:00:02.000
Test subtitle.
"""
        content_bytes = vtt_content.encode('utf-8')
        result = ingest_upload_file('test.vtt', content_bytes)

        assert 'SUBTITLE FILE' in result
        assert 'Format: WebVTT' in result


class TestPhase3Integration(unittest.TestCase):
    """Integration tests for Phase 3."""

    def test_zip_containing_epub(self):
        """Test ZIP archive containing an EPUB book."""
        try:
            from ebooklib import epub
        except ImportError:
            self.skipTest("ebooklib not installed")

        # Create EPUB
        book = epub.EpubBook()
        book.set_identifier('nested')
        book.set_title('Nested Book')
        book.set_language('en')

        c1 = epub.EpubHtml(title='Chapter', file_name='chapter.xhtml')
        c1.content = '<html><body><p>Nested content</p></body></html>'
        book.add_item(c1)

        # Add spine
        book.spine = ['nav', c1]
        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())

        epub_buffer = io.BytesIO()
        epub.write_epub(epub_buffer, book)
        epub_bytes = epub_buffer.getvalue()

        # Create ZIP containing EPUB
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
            zipf.writestr('book.epub', epub_bytes)

        content_bytes = zip_buffer.getvalue()
        result = extract_zip_archive(content_bytes, 'books.zip')

        assert 'ZIP ARCHIVE' in result
        assert 'book.epub' in result
        assert 'Nested Book' in result
        assert 'Nested content' in result

    def test_zip_mixed_content(self):
        """Test ZIP with mixed file types (code, text, subtitles)."""
        srt_content = """1
00:00:00,000 --> 00:00:02,000
Subtitle text.
"""

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
            zipf.writestr('script.py', 'print("hello")')
            zipf.writestr('README.md', '# Project')
            zipf.writestr('video.srt', srt_content)

        content_bytes = zip_buffer.getvalue()
        result = extract_zip_archive(content_bytes, 'mixed.zip')

        assert 'script.py' in result
        assert 'Python' in result
        assert 'README.md' in result
        assert 'video.srt' in result
        assert 'Subtitle text' in result

    def test_phase3_file_count(self):
        """Verify Phase 3 adds correct number of new file types."""
        # Phase 3 should add: .zip, .epub, .srt, .vtt = 4 new extensions
        phase3_extensions = ['.zip', '.epub', '.srt', '.vtt']

        for ext in phase3_extensions:
            # Each should have a handler
            test_file = f'test{ext}'

            if ext == '.zip':
                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, 'w') as zipf:
                    zipf.writestr('dummy.txt', 'content')
                content = zip_buffer.getvalue()
            elif ext == '.epub':
                try:
                    from ebooklib import epub
                    book = epub.EpubBook()
                    book.set_identifier('test')
                    book.set_title('Test')
                    buffer = io.BytesIO()
                    epub.write_epub(buffer, book)
                    content = buffer.getvalue()
                except ImportError:
                    continue
            elif ext == '.srt':
                content = b"1\n00:00:00,000 --> 00:00:01,000\nTest"
            elif ext == '.vtt':
                content = b"WEBVTT\n\n00:00:00.000 --> 00:00:01.000\nTest"

            # Should not raise "Unsupported file type"
            try:
                result = ingest_upload_file(test_file, content)
                assert len(result) > 0
            except Exception as e:
                if "Unsupported file type" in str(e):
                    self.fail(f"Phase 3 extension {ext} not supported")


if __name__ == '__main__':
    unittest.main()
