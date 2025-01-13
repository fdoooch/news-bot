import httpx
import tempfile
import os
from pathlib import Path
from contextlib import contextmanager, asynccontextmanager
import shutil
import urllib

@asynccontextmanager
async def temp_download_async(url: str, prefix: str = "download_"):
    """
    Async context manager for temporary file download
    
    Args:
        url (str): URL of the file to download
        prefix (str): Prefix for temp directory name
    
    Yields:
        Path: Path to downloaded temporary file
    """
    temp_dir = tempfile.mkdtemp(prefix=prefix)
    temp_path = None
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Referer': urllib.parse.urljoin(url, '/'),  # Add referrer from same domain
    }
    
    try:
        filename = os.path.basename(url)
        temp_path = Path(temp_dir) / filename
        
        async with httpx.AsyncClient() as client:
            async with client.stream('GET', url, headers=headers, follow_redirects=True) as response:
                response.raise_for_status()
                
                with open(temp_path, 'wb') as f:
                    async for chunk in response.aiter_bytes():
                        f.write(chunk)
        
        yield temp_path
        
    finally:
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

@contextmanager
def temp_download_sync(url: str, prefix: str = "download_"):
    """
    Sync context manager for temporary file download
    
    Args:
        url (str): URL of the file to download
        prefix (str): Prefix for temp directory name
    
    Yields:
        Path: Path to downloaded temporary file
    """
    temp_dir = tempfile.mkdtemp(prefix=prefix)
    temp_path = None
    
    try:
        filename = os.path.basename(url)
        temp_path = Path(temp_dir) / filename
        
        with httpx.Client() as client:
            with client.stream('GET', url) as response:
                response.raise_for_status()
                
                with open(temp_path, 'wb') as f:
                    for chunk in response.iter_bytes():
                        f.write(chunk)
        
        yield temp_path
        
    finally:
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

# Example usage with async
async def main():
    url = "https://example.com/image.jpg"
    
    try:
        async with temp_download_async(url) as temp_file:
            print(f"Downloaded to: {temp_file}")
            # Do something with the file here
            # File will be automatically deleted after this block
            
    except httpx.RequestError as e:
        print(f"Download failed: {e}")