"""
Real multimodal content ingestion with YouTube transcription.

This module provides actual AI-powered content processing:
- YouTube video transcription using OpenAI Whisper (with audio compression)
- TikTok video processing
- PDF text extraction
- Audio file transcription
- Web article extraction

✅ FIXED: Added audio compression to handle files over Whisper's 25MB limit

Dependencies:
    pip install yt-dlp openai anthropic pypdf beautifulsoup4 requests
"""

import os
import tempfile
import logging
import subprocess
from typing import Optional
from pathlib import Path

logger = logging.getLogger(__name__)

# Check for required API keys
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    logger.warning("OPENAI_API_KEY not set - YouTube transcription will fail")

# Whisper API file size limit
WHISPER_MAX_SIZE_MB = 25
WHISPER_MAX_SIZE_BYTES = WHISPER_MAX_SIZE_MB * 1024 * 1024


def download_url(url: str) -> str:
    """
    Download and process content from a URL.
    
    Supports:
    - YouTube videos (transcription via Whisper)
    - TikTok videos (transcription via Whisper)
    - Web articles (text extraction)
    - Direct media files
    
    Args:
        url: The URL to process
        
    Returns:
        Extracted text content
        
    Raises:
        Exception: If processing fails
    """
    url_lower = url.lower()
    
    # YouTube video
    if 'youtube.com' in url_lower or 'youtu.be' in url_lower:
        return transcribe_youtube(url)
    
    # TikTok video
    elif 'tiktok.com' in url_lower:
        return transcribe_tiktok(url)
    
    # Regular web page
    else:
        return extract_web_article(url)


def compress_audio_for_whisper(input_path: Path, output_path: Path) -> None:
    """
    Compress audio file to meet Whisper's 25MB limit.
    
    Compression settings optimized for speech transcription:
    - 16kHz sample rate (Whisper's recommended format)
    - Mono channel (speech doesn't need stereo)
    - 64kbps bitrate (sufficient for clear speech)
    
    This typically reduces file size by 50-70% with no quality loss for transcription.
    
    Args:
        input_path: Path to original audio file
        output_path: Path to save compressed audio
        
    Raises:
        Exception: If FFmpeg compression fails
    """
    try:
        subprocess.run([
            'ffmpeg',
            '-i', str(input_path),
            '-ar', '16000',      # 16kHz sample rate (Whisper optimal)
            '-ac', '1',          # Mono audio (sufficient for speech)
            '-b:a', '64k',       # 64kbps bitrate (good quality speech)
            '-y',                # Overwrite output file
            str(output_path)
        ], check=True, capture_output=True, text=True)
        
        original_size = input_path.stat().st_size / (1024 * 1024)  # MB
        compressed_size = output_path.stat().st_size / (1024 * 1024)  # MB
        
        logger.info(
            f"Compressed audio: {original_size:.2f}MB → {compressed_size:.2f}MB "
            f"({100 * (1 - compressed_size/original_size):.1f}% reduction)"
        )
        
    except subprocess.CalledProcessError as e:
        raise Exception(f"Audio compression failed: {e.stderr}")


def chunk_audio_file(audio_path: Path, chunk_duration_seconds: int = 600) -> list[Path]:
    """
    Split audio file into chunks for very long videos.
    
    Only used as fallback if compression still exceeds 25MB limit.
    This typically only happens for videos over 90-120 minutes.
    
    Args:
        audio_path: Path to audio file
        chunk_duration_seconds: Length of each chunk (default 10 minutes)
        
    Returns:
        List of paths to audio chunks
    """
    chunk_pattern = audio_path.parent / f"{audio_path.stem}_chunk_%03d{audio_path.suffix}"
    
    try:
        subprocess.run([
            'ffmpeg',
            '-i', str(audio_path),
            '-f', 'segment',
            '-segment_time', str(chunk_duration_seconds),
            '-c', 'copy',
            '-y',
            str(chunk_pattern)
        ], check=True, capture_output=True, text=True)
        
        # Find all created chunks
        chunks = sorted(audio_path.parent.glob(f"{audio_path.stem}_chunk_*.{audio_path.suffix}"))
        logger.info(f"Split audio into {len(chunks)} chunks")
        return chunks
        
    except subprocess.CalledProcessError as e:
        raise Exception(f"Audio chunking failed: {e.stderr}")


def transcribe_youtube(url: str) -> str:
    """
    Transcribe a YouTube video using OpenAI Whisper.
    
    Process:
    1. Download audio using yt-dlp
    2. Compress audio to meet Whisper's 25MB limit
    3. If still too large, split into chunks
    4. Transcribe with Whisper API
    5. Return transcript with metadata
    
    ✅ FIXED: Now handles videos over 25MB by compressing audio first
    
    Args:
        url: YouTube URL
        
    Returns:
        Full transcript with title and metadata
    """
    try:
        import yt_dlp
        from openai import OpenAI
    except ImportError:
        raise Exception(
            "Missing dependencies. Install with: "
            "pip install yt-dlp openai"
        )
    
    if not OPENAI_API_KEY:
        raise Exception("OPENAI_API_KEY environment variable not set")
    
    logger.info(f"Transcribing YouTube video: {url}")
    
    # Create temporary directory for audio
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        audio_path = temp_path / "audio.mp3"
        compressed_path = temp_path / "audio_compressed.mp3"
        
        # Download audio with yt-dlp
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'outtmpl': str(audio_path.with_suffix('')),
            'quiet': True,
            'no_warnings': True,
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                title = info.get('title', 'Unknown')
                duration = info.get('duration', 0)
                channel = info.get('channel', 'Unknown')
                
            original_size = audio_path.stat().st_size
            logger.info(
                f"Downloaded: {title} ({duration}s, {original_size/(1024*1024):.2f}MB)"
            )
            
        except Exception as e:
            raise Exception(f"Failed to download YouTube video: {e}")
        
        # Check if compression is needed
        if original_size > WHISPER_MAX_SIZE_BYTES:
            logger.info(
                f"Audio file ({original_size/(1024*1024):.2f}MB) exceeds Whisper limit "
                f"({WHISPER_MAX_SIZE_MB}MB). Compressing..."
            )
            compress_audio_for_whisper(audio_path, compressed_path)
            transcription_path = compressed_path
        else:
            logger.info("Audio file within Whisper limit, no compression needed")
            transcription_path = audio_path
        
        # Check if chunking is needed (for very long videos)
        final_size = transcription_path.stat().st_size
        if final_size > WHISPER_MAX_SIZE_BYTES:
            logger.warning(
                f"Even after compression ({final_size/(1024*1024):.2f}MB), "
                f"file exceeds limit. Splitting into chunks..."
            )
            chunks = chunk_audio_file(transcription_path)
            return transcribe_audio_chunks(chunks, title, channel, duration, url)
        
        # Transcribe with Whisper (single file)
        try:
            client = OpenAI(api_key=OPENAI_API_KEY)
            
            logger.info(f"Sending to Whisper API ({final_size/(1024*1024):.2f}MB)...")
            with open(transcription_path, 'rb') as audio_file:
                transcript = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    response_format="text"
                )
            
            # Format result with metadata
            result = f"""YOUTUBE VIDEO TRANSCRIPT
Title: {title}
Channel: {channel}
Duration: {duration} seconds
URL: {url}

TRANSCRIPT:
{transcript}
"""
            
            logger.info(f"Successfully transcribed {len(transcript)} characters")
            return result
            
        except Exception as e:
            raise Exception(f"Whisper transcription failed: {e}")


def transcribe_audio_chunks(chunks: list[Path], title: str, channel: str, 
                            duration: int, url: str) -> str:
    """
    Transcribe multiple audio chunks and combine results.
    
    Only used for very long videos (90+ minutes) where even compression
    doesn't bring the file under 25MB.
    
    Args:
        chunks: List of audio chunk paths
        title: Video title
        channel: Channel name
        duration: Video duration in seconds
        url: Original video URL
        
    Returns:
        Combined transcript with metadata
    """
    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
        
        transcripts = []
        for i, chunk_path in enumerate(chunks, 1):
            logger.info(f"Transcribing chunk {i}/{len(chunks)}...")
            
            with open(chunk_path, 'rb') as audio_file:
                transcript = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    response_format="text"
                )
            
            transcripts.append(f"[Part {i}]\n{transcript}")
        
        combined_transcript = "\n\n".join(transcripts)
        
        result = f"""YOUTUBE VIDEO TRANSCRIPT
Title: {title}
Channel: {channel}
Duration: {duration} seconds
URL: {url}
Note: Video was split into {len(chunks)} parts for transcription

TRANSCRIPT:
{combined_transcript}
"""
        
        logger.info(f"Successfully transcribed {len(combined_transcript)} characters from {len(chunks)} chunks")
        return result
        
    except Exception as e:
        raise Exception(f"Chunked transcription failed: {e}")


def transcribe_tiktok(url: str) -> str:
    """
    Transcribe a TikTok video.
    
    Similar to YouTube but handles TikTok-specific URL format.
    ✅ Includes audio compression for files over 25MB.
    
    Args:
        url: TikTok URL
        
    Returns:
        Transcript with metadata
    """
    try:
        import yt_dlp
        from openai import OpenAI
    except ImportError:
        raise Exception(
            "Missing dependencies. Install with: "
            "pip install yt-dlp openai"
        )
    
    if not OPENAI_API_KEY:
        raise Exception("OPENAI_API_KEY environment variable not set")
    
    logger.info(f"Transcribing TikTok video: {url}")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        audio_path = temp_path / "audio.mp3"
        compressed_path = temp_path / "audio_compressed.mp3"
        
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'outtmpl': str(audio_path.with_suffix('')),
            'quiet': True,
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                title = info.get('title', 'TikTok Video')
                creator = info.get('creator', 'Unknown')
                
            original_size = audio_path.stat().st_size
            logger.info(f"Downloaded TikTok: {title} ({original_size/(1024*1024):.2f}MB)")
                
        except Exception as e:
            raise Exception(f"Failed to download TikTok video: {e}")
        
        # Compress if needed
        if original_size > WHISPER_MAX_SIZE_BYTES:
            logger.info("Compressing TikTok audio...")
            compress_audio_for_whisper(audio_path, compressed_path)
            transcription_path = compressed_path
        else:
            transcription_path = audio_path
        
        # Transcribe
        try:
            client = OpenAI(api_key=OPENAI_API_KEY)
            
            with open(transcription_path, 'rb') as audio_file:
                transcript = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    response_format="text"
                )
            
            result = f"""TIKTOK VIDEO TRANSCRIPT
Title: {title}
Creator: {creator}
URL: {url}

TRANSCRIPT:
{transcript}
"""
            logger.info(f"Successfully transcribed TikTok ({len(transcript)} characters)")
            return result
            
        except Exception as e:
            raise Exception(f"TikTok transcription failed: {e}")


def extract_web_article(url: str) -> str:
    """
    Extract text content from a web article.
    
    Uses BeautifulSoup to parse HTML and extract main content.
    
    Args:
        url: Web page URL
        
    Returns:
        Extracted text content
    """
    try:
        import requests
        from bs4 import BeautifulSoup
    except ImportError:
        raise Exception(
            "Missing dependencies. Install with: "
            "pip install requests beautifulsoup4"
        )
    
    logger.info(f"Extracting content from: {url}")
    
    try:
        # Fetch page
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        # Parse HTML
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style", "nav", "footer", "header"]):
            script.decompose()
        
        # Get title
        title = soup.find('title')
        title_text = title.get_text() if title else 'Unknown'
        
        # Extract main content
        # Try common content containers
        main_content = None
        for selector in ['article', 'main', '[role="main"]', '.content', '#content']:
            main_content = soup.select_one(selector)
            if main_content:
                break
        
        if not main_content:
            main_content = soup.find('body')
        
        # Get text
        text = main_content.get_text(separator='\n', strip=True) if main_content else ''
        
        # Clean up whitespace
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        text = '\n'.join(lines)
        
        result = f"""WEB ARTICLE
Title: {title_text}
URL: {url}

CONTENT:
{text}
"""
        
        logger.info(f"Extracted {len(text)} characters")
        return result
        
    except Exception as e:
        raise Exception(f"Failed to extract web content: {e}")


def ingest_upload_file(filename: str, content_bytes: bytes) -> str:
    """
    Process an uploaded file and extract text.
    
    Supports:
    - PDF files (text extraction)
    - Text files (.txt, .md)
    - Audio files (.mp3, .wav, .m4a) - transcription via Whisper
    - Word documents (.docx)
    
    ✅ Audio files now compressed if over 25MB limit.
    
    Args:
        filename: Original filename
        content_bytes: File content as bytes
        
    Returns:
        Extracted text content
    """
    file_ext = Path(filename).suffix.lower()
    
    logger.info(f"Processing uploaded file: {filename} ({len(content_bytes)} bytes)")
    
    # Text files
    if file_ext in ['.txt', '.md', '.csv', '.json']:
        try:
            return content_bytes.decode('utf-8')
        except UnicodeDecodeError:
            try:
                return content_bytes.decode('latin-1')
            except:
                raise Exception("Failed to decode text file")
    
    # PDF files
    elif file_ext == '.pdf':
        return extract_pdf_text(content_bytes)
    
    # Audio files
    elif file_ext in ['.mp3', '.wav', '.m4a', '.ogg', '.flac']:
        return transcribe_audio_file(content_bytes, filename)
    
    # Word documents
    elif file_ext == '.docx':
        return extract_docx_text(content_bytes)
    
    else:
        raise Exception(f"Unsupported file type: {file_ext}")


def extract_pdf_text(content_bytes: bytes) -> str:
    """Extract text from PDF file."""
    try:
        from pypdf import PdfReader
        import io
    except ImportError:
        raise Exception("Install pypdf: pip install pypdf")
    
    try:
        pdf_file = io.BytesIO(content_bytes)
        reader = PdfReader(pdf_file)
        
        text_parts = []
        for i, page in enumerate(reader.pages):
            text = page.extract_text()
            if text.strip():
                text_parts.append(f"--- Page {i+1} ---\n{text}")
        
        result = f"PDF DOCUMENT ({len(reader.pages)} pages)\n\n" + "\n\n".join(text_parts)
        
        logger.info(f"Extracted text from {len(reader.pages)} pages")
        return result
        
    except Exception as e:
        raise Exception(f"PDF extraction failed: {e}")


def transcribe_audio_file(content_bytes: bytes, filename: str) -> str:
    """
    Transcribe an audio file using Whisper.
    
    ✅ Now includes compression for files over 25MB.
    
    Args:
        content_bytes: Audio file content
        filename: Original filename
        
    Returns:
        Transcript with metadata
    """
    try:
        from openai import OpenAI
    except ImportError:
        raise Exception("Install openai: pip install openai")
    
    if not OPENAI_API_KEY:
        raise Exception("OPENAI_API_KEY not set")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Save original file
        original_path = temp_path / f"original{Path(filename).suffix}"
        with open(original_path, 'wb') as f:
            f.write(content_bytes)
        
        original_size = len(content_bytes)
        logger.info(f"Audio file size: {original_size/(1024*1024):.2f}MB")
        
        # Compress if needed
        if original_size > WHISPER_MAX_SIZE_BYTES:
            logger.info("Compressing audio file...")
            compressed_path = temp_path / f"compressed{Path(filename).suffix}"
            compress_audio_for_whisper(original_path, compressed_path)
            transcription_path = compressed_path
        else:
            transcription_path = original_path
        
        try:
            client = OpenAI(api_key=OPENAI_API_KEY)
            
            with open(transcription_path, 'rb') as audio_file:
                transcript = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    response_format="text"
                )
            
            result = f"""AUDIO FILE TRANSCRIPT
Filename: {filename}

TRANSCRIPT:
{transcript}
"""
            logger.info(f"Successfully transcribed audio file ({len(transcript)} characters)")
            return result
            
        except Exception as e:
            raise Exception(f"Audio transcription failed: {e}")


def extract_docx_text(content_bytes: bytes) -> str:
    """Extract text from Word document."""
    try:
        from docx import Document
        import io
    except ImportError:
        raise Exception("Install python-docx: pip install python-docx")
    
    try:
        doc_file = io.BytesIO(content_bytes)
        doc = Document(doc_file)
        
        text_parts = []
        for para in doc.paragraphs:
            if para.text.strip():
                text_parts.append(para.text)
        
        result = "WORD DOCUMENT\n\n" + "\n\n".join(text_parts)
        
        logger.info(f"Extracted text from Word document: {len(text_parts)} paragraphs")
        return result
        
    except Exception as e:
        raise Exception(f"Word document extraction failed: {e}")
