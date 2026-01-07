#!/usr/bin/env python3
"""
Download datasets for compression model training.

Supports:
- YouTube videos (via yt-dlp)
- Pexels videos (via API)
- Kinetics dataset (via official download)
- Custom video URLs
"""

import os
import sys
import argparse
import json
import subprocess
import requests
from pathlib import Path
from tqdm import tqdm
import time

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

class DatasetDownloader:
    def __init__(self, output_dir="datasets/videos"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def download_youtube_videos(self, search_query, category="mixed", max_videos=100):
        """Download videos from YouTube using yt-dlp search"""
        print(f"\n📥 Downloading YouTube videos (category: {category}, query: {search_query})...")
        
        category_dir = self.output_dir / "youtube" / category
        category_dir.mkdir(parents=True, exist_ok=True)
        
        output_template = str(category_dir / "%(title)s.%(ext)s")
        
        try:
            # Use yt-dlp to search and download with flexible format selection
            # Check if Node.js is available for better YouTube extraction
            js_runtime = None
            try:
                result = subprocess.run(["which", "node"], capture_output=True, text=True)
                if result.returncode == 0:
                    js_runtime = "node"
            except:
                pass
            
            cmd = [
                "yt-dlp",
                f"ytsearch{max_videos}:{search_query}",
                # Flexible format: prefer 720p/480p/360p, fallback to any available format
                # Format codes: 22=720p, 18=360p, 136+140=720p separate streams
                "-f", "best[height<=720][ext=mp4][duration<=600]/best[height<=480][ext=mp4][duration<=600]/best[height<=360][ext=mp4][duration<=600]/22/18/136+140/best[height<=720][duration<=600]/best[height<=480][duration<=600]/best[duration<=600]",
                "-o", output_template,
                "--no-playlist",
                "--match-filter", "duration <= 600 & !is_live & !is_upcoming",  # Exclude shorts, live, upcoming
                "--ignore-errors",  # Continue on errors
                "--progress",
                "--max-downloads", str(max_videos),
                "--extract-flat", "false",  # Actually download, not just list
                "--merge-output-format", "mp4",  # Merge to mp4
                "--retries", "2",  # Retry failed downloads
                "--fragment-retries", "2",
                "--max-filesize", "500M",  # Max 500MB per video
                "--no-warnings"  # Suppress format warnings
            ]
            
            # Add JS runtime if available (reduces warnings)
            if js_runtime:
                cmd.extend(["--js-runtimes", js_runtime])
            
            print(f"   Running: yt-dlp ytsearch{max_videos}:{search_query}...")
            print(f"   (This may take a while, downloading {max_videos} videos...)")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=3600  # 1 hour timeout for batch downloads
            )
            
            # Count downloaded files (ignore errors, some videos may fail)
            downloaded = len(list(category_dir.glob("*.mp4")))
            
            if downloaded > 0:
                print(f"✅ Downloaded {downloaded} videos from YouTube")
                if result.returncode != 0:
                    print(f"   ⚠️  Some videos failed to download (this is normal)")
            else:
                print(f"⚠️  No videos downloaded. Possible issues:")
                print(f"   1. YouTube format restrictions (try updating yt-dlp)")
                print(f"   2. Network issues")
                print(f"   3. Try: pip install --upgrade yt-dlp")
                if result.stderr:
                    print(f"   Error: {result.stderr[:300]}")
            
            return downloaded
                
        except subprocess.TimeoutExpired:
            downloaded = len(list(category_dir.glob("*.mp4")))
            print(f"⚠️  Download timed out. Downloaded {downloaded} videos so far.")
            return downloaded
        except Exception as e:
            print(f"❌ Error downloading YouTube videos: {e}")
            downloaded = len(list(category_dir.glob("*.mp4")))
            return downloaded
        
    def download_pexels_videos(self, api_key, num_videos=100, category="mixed"):
        """Download videos from Pexels using API"""
        print(f"\n📥 Downloading Pexels videos (category: {category})...")
        
        if not api_key:
            print("⚠️  Pexels API key not provided. Skipping Pexels download.")
            print("   Get API key from: https://www.pexels.com/api/")
            return 0
        
        category_dir = self.output_dir / "pexels" / category
        category_dir.mkdir(parents=True, exist_ok=True)
        
        # Pexels search terms for different categories
        search_terms = {
            "gaming": ["gaming", "video game", "esports"],
            "animation": ["animation", "cartoon", "animated"],
            "faces": ["people", "portrait", "face"],
            "text": ["text", "document", "screen"],
            "mixed": ["nature", "city", "technology", "sports", "music"]
        }
        
        terms = search_terms.get(category, search_terms["mixed"])
        downloaded = 0
        
        for term in terms:
            if downloaded >= num_videos:
                break
                
            page = 1
            per_page = min(80, num_videos - downloaded)
            
            while downloaded < num_videos and page <= 10:  # Max 10 pages
                url = f"https://api.pexels.com/videos/search"
                headers = {"Authorization": api_key}
                params = {
                    "query": term,
                    "per_page": per_page,
                    "page": page,
                    "orientation": "landscape"
                }
                
                try:
                    response = requests.get(url, headers=headers, params=params, timeout=30)
                    response.raise_for_status()
                    data = response.json()
                    
                    for video in data.get("videos", []):
                        if downloaded >= num_videos:
                            break
                            
                        # Get best quality video file
                        video_files = video.get("video_files", [])
                        if not video_files:
                            continue
                            
                        # Prefer HD quality
                        hd_file = next((f for f in video_files if f.get("width", 0) >= 1280), None)
                        video_file = hd_file or video_files[0]
                        
                        video_url = video_file.get("link")
                        video_id = video.get("id")
                        
                        # Download video
                        output_path = category_dir / f"pexels_{video_id}.mp4"
                        if not output_path.exists():
                            try:
                                video_response = requests.get(video_url, timeout=60, stream=True)
                                video_response.raise_for_status()
                                
                                with open(output_path, "wb") as f:
                                    for chunk in video_response.iter_content(chunk_size=8192):
                                        f.write(chunk)
                                
                                downloaded += 1
                                time.sleep(0.5)  # Rate limiting
                                
                            except Exception as e:
                                print(f"Error downloading video {video_id}: {e}")
                    
                    page += 1
                    time.sleep(1)  # Rate limiting
                    
                except Exception as e:
                    print(f"Error fetching Pexels videos: {e}")
                    break
        
        print(f"✅ Downloaded {downloaded} videos from Pexels")
        return downloaded
    
    def download_from_urls_file(self, urls_file, category="custom"):
        """Download videos from a file containing URLs (one per line)"""
        print(f"\n📥 Downloading videos from URLs file...")
        
        category_dir = self.output_dir / "custom" / category
        category_dir.mkdir(parents=True, exist_ok=True)
        
        with open(urls_file, 'r') as f:
            urls = [line.strip() for line in f if line.strip()]
        
        downloaded = 0
        for url in tqdm(urls):
            try:
                if "youtube.com" in url or "youtu.be" in url:
                    output_template = str(category_dir / "%(title)s.%(ext)s")
                    cmd = [
                        "yt-dlp",
                        "-f", "best[height<=1080][ext=mp4]",
                        "-o", output_template,
                        url
                    ]
                else:
                    # Direct download
                    filename = url.split("/")[-1].split("?")[0]
                    output_path = category_dir / filename
                    cmd = ["wget", "-O", str(output_path), url]
                
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
                if result.returncode == 0:
                    downloaded += 1
            except Exception as e:
                print(f"Error downloading {url}: {e}")
        
        print(f"✅ Downloaded {downloaded} videos from URLs file")
        return downloaded


def get_youtube_search_queries():
    """Get YouTube search queries by category"""
    queries = {
        "gaming": [
            "gaming gameplay",
            "video game playthrough",
            "esports highlights",
            "gaming montage"
        ],
        "animation": [
            "animation cartoon",
            "animated short film",
            "2d animation",
            "3d animation"
        ],
        "faces": [
            "people talking",
            "portrait video",
            "face close up",
            "interview video"
        ],
        "text": [
            "screen recording tutorial",
            "text document",
            "presentation slides",
            "code programming"
        ],
        "mixed": [
            "nature landscape",
            "city time lapse",
            "technology review",
            "music performance",
            "sports highlights"
        ]
    }
    return queries


def main():
    parser = argparse.ArgumentParser(description="Download datasets for compression model training")
    parser.add_argument("--sources", type=str, default="youtube,pexels",
                       help="Comma-separated list of sources: youtube,pexels,custom")
    parser.add_argument("--num_videos", type=int, default=1000,
                       help="Total number of videos to download")
    parser.add_argument("--output_dir", type=str, default="datasets/videos",
                       help="Output directory for videos")
    parser.add_argument("--pexels_api_key", type=str, default=None,
                       help="Pexels API key (get from https://www.pexels.com/api/)")
    parser.add_argument("--urls_file", type=str, default=None,
                       help="File containing video URLs (one per line)")
    parser.add_argument("--categories", type=str, default="gaming,animation,faces,text,mixed",
                       help="Comma-separated list of categories")
    
    args = parser.parse_args()
    
    downloader = DatasetDownloader(args.output_dir)
    sources = [s.strip() for s in args.sources.split(",")]
    categories = [c.strip() for c in args.categories.split(",")]
    
    total_downloaded = 0
    
    # Calculate videos per category
    videos_per_category = args.num_videos // len(categories)
    
    # Get YouTube search queries
    youtube_queries = get_youtube_search_queries()
    
    for category in categories:
        print(f"\n{'='*60}")
        print(f"Category: {category.upper()}")
        print(f"{'='*60}")
        
        if "youtube" in sources:
            # Download from YouTube using search
            queries = youtube_queries.get(category, youtube_queries["mixed"])
            # Use first query for this category
            search_query = queries[0] if queries else category
            downloaded = downloader.download_youtube_videos(
                search_query=search_query,
                category=category,
                max_videos=videos_per_category
            )
            total_downloaded += downloaded
            
        if "pexels" in sources:
            downloaded = downloader.download_pexels_videos(
                api_key=args.pexels_api_key,
                num_videos=videos_per_category,
                category=category
            )
            total_downloaded += downloaded
        
        if "custom" in sources and args.urls_file:
            downloaded = downloader.download_from_urls_file(args.urls_file, category)
            total_downloaded += downloaded
    
    print(f"\n{'='*60}")
    print(f"✅ Total videos downloaded: {total_downloaded}")
    print(f"📁 Videos saved to: {args.output_dir}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()

