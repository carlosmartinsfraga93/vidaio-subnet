import time
import httpx
import os
import sys
import uuid
import shutil
from urllib.parse import urlparse, unquote
from firerequests import FireRequests
from loguru import logger
from pathlib import Path
from rich.progress import Progress, TaskID

fire_downloader = FireRequests()

def clean_tmp_directory():
    """Clean the tmp directory if running as validator and delete only .mp4 files."""
    if (
        __name__ != "__main__"
        and os.path.basename(os.path.abspath(sys.argv[0])) == "validator.py"
    ):
        tmp_dir = Path("tmp")
        tmp_dir.mkdir(exist_ok=True)  # Create the tmp directory if it doesn't exist
        
        # Iterate over all files in the tmp directory
        for file in track(tmp_dir.iterdir(), description="Cleaning .mp4 files in tmp directory"):
            if file.suffix == ".mp4":  # Only delete .mp4 files
                os.remove(file)
                print(f"Deleted: {file}").remove(os.path.join("tmp", file))

def _generate_filename(url: str) -> str:
    """Generate a unique filename for downloaded file."""
    tmp_dir = Path("tmp")
    tmp_dir.mkdir(exist_ok=True)  # Create the tmp directory if it doesn't exist
    return os.path.join("tmp", str(uuid.uuid4()) + ".mp4")

async def download_video(url: str) -> str:
    """
    Download a video file from a URL or copy from local file.

    Supports:
    - HTTP/HTTPS URLs: Downloads from remote server
    - file:// URLs: Copies from local filesystem (e.g., file:///workspace/vidaio-subnet/tmp/video.mp4)
    - Local paths: Copies from local filesystem (e.g., tmp/video.mp4)

    Args:
        url (str): The URL or path of the video to download/copy.

    Returns:
        str: The local file path of the downloaded/copied video.
    """
    # Parse URL to detect scheme
    parsed = urlparse(url)

    # Handle file:// URLs or local paths
    if parsed.scheme == 'file' or (not parsed.scheme or parsed.scheme == ''):
        # Extract local file path
        if parsed.scheme == 'file':
            # file:///path/to/file -> /path/to/file
            local_path = unquote(parsed.path)
            # On Windows, remove leading slash if path starts with drive letter
            if os.name == 'nt' and local_path.startswith('/') and len(local_path) > 2 and local_path[2] == ':':
                local_path = local_path[1:]
        else:
            # Direct path
            local_path = url

        # Check if file exists
        if not os.path.exists(local_path):
            raise FileNotFoundError(f"Local file not found: {local_path}")

        # Generate output path
        file_path = _generate_filename(url)

        # Copy file with progress
        file_size = os.path.getsize(local_path)
        print(f"Copying local file: {local_path} ({file_size / 1024 / 1024:.2f} MB)")

        with open(local_path, 'rb') as src, open(file_path, 'wb') as dst:
            with Progress() as progress:
                task = progress.add_task("[cyan]Copying...", total=file_size)
                while True:
                    chunk = src.read(1024 * 1024)  # 1MB chunks
                    if not chunk:
                        break
                    dst.write(chunk)
                    progress.update(task, advance=len(chunk))

        print(f"Video copied to: {file_path}")
        return file_path

    # Handle HTTP/HTTPS URLs (original behavior)
    else:
        file_path = _generate_filename(url)

        # Use longer timeout for video downloads (30s connect, 300s read)
        timeout = httpx.Timeout(30.0, read=300.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            async with client.stream("GET", url) as response:
                response.raise_for_status()
                total_size = int(response.headers.get("Content-Length", 0))

                with open(file_path, "wb") as f:
                    with Progress() as progress:
                        task = progress.add_task("[cyan]Downloading...", total=total_size)
                        async for chunk in response.aiter_bytes(chunk_size=1024 * 1024):
                            f.write(chunk)
                            progress.update(task, advance=len(chunk))

        print(f"Video downloaded to: {file_path}")
        return file_path
