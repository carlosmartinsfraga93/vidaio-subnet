"""
Request Logger for Video Compression Service

Maintains a rolling history of the most recent 100 compression requests,
including downloaded videos, compression results, and metadata.

This allows:
1. Testing compression code changes with real data
2. Monitoring what happened during compression
3. Debugging issues with actual request data
"""

import os
import json
import shutil
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from collections import deque


class RequestLogger:
    """Manages logging and retention of compression requests."""
    
    def __init__(self, max_requests: int = 100, log_dir: str = "compression_logs"):
        """
        Initialize the request logger.
        
        Args:
            max_requests: Maximum number of requests to keep (default: 100)
            log_dir: Directory to store logs and videos (default: compression_logs)
        """
        self.max_requests = max_requests
        self.log_dir = Path(log_dir)
        
        # Create directory structure
        self.videos_dir = self.log_dir / "videos"
        self.results_dir = self.log_dir / "results"
        self.metadata_dir = self.log_dir / "metadata"
        
        for directory in [self.videos_dir, self.results_dir, self.metadata_dir]:
            directory.mkdir(parents=True, exist_ok=True)
        
        # Load or create request index
        self.index_file = self.log_dir / "request_index.json"
        self.request_queue = self._load_index()
    
    def _load_index(self) -> deque:
        """Load the request index from disk."""
        if self.index_file.exists():
            try:
                with open(self.index_file, 'r') as f:
                    data = json.load(f)
                    return deque(data.get('requests', []), maxlen=self.max_requests)
            except Exception as e:
                print(f"⚠️ Error loading request index: {e}")
        return deque(maxlen=self.max_requests)
    
    def _save_index(self):
        """Save the request index to disk."""
        try:
            with open(self.index_file, 'w') as f:
                json.dump({
                    'requests': list(self.request_queue),
                    'last_updated': datetime.now(timezone.utc).isoformat(),
                    'max_requests': self.max_requests
                }, f, indent=2)
        except Exception as e:
            print(f"⚠️ Error saving request index: {e}")
    
    def log_request(
        self,
        request_id: str,
        downloaded_video_path: str,
        request_data: Dict[str, Any],
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        validator_uid: Optional[int] = None,
        validator_hotkey: Optional[str] = None
    ) -> str:
        """
        Log a compression request with all associated data.

        Args:
            request_id: Unique identifier for the request
            downloaded_video_path: Path to the downloaded video file
            request_data: Request parameters (URL, codec, quality, etc.)
            result: Compression result data (optional)
            error: Error message if compression failed (optional)
            validator_uid: Validator UID (optional)
            validator_hotkey: Validator hotkey (optional)

        Returns:
            str: Path to the logged video file
        """
        timestamp = datetime.now(timezone.utc).isoformat()

        # Determine environment based on video URL
        video_url = request_data.get('payload_url', '')
        environment = self._detect_environment(video_url)

        # Copy downloaded video to logs
        logged_video_path = self.videos_dir / f"{request_id}.mp4"
        try:
            if os.path.exists(downloaded_video_path):
                shutil.copy2(downloaded_video_path, logged_video_path)
                print(f"📝 Logged video: {logged_video_path}")
            else:
                print(f"⚠️ Downloaded video not found: {downloaded_video_path}")
                logged_video_path = None
        except Exception as e:
            print(f"⚠️ Error copying video to logs: {e}")
            logged_video_path = None

        # Save metadata
        metadata = {
            'request_id': request_id,
            'timestamp': timestamp,
            'environment': environment,
            'validator_uid': validator_uid,
            'validator_hotkey': validator_hotkey,
            'request_data': request_data,
            'result': result,
            'error': error,
            'video_path': str(logged_video_path) if logged_video_path else None
        }

        metadata_path = self.metadata_dir / f"{request_id}.json"
        try:
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            print(f"📝 Logged metadata: {metadata_path} [env={environment}]")
        except Exception as e:
            print(f"⚠️ Error saving metadata: {e}")

        # Add to request queue
        self.request_queue.append({
            'request_id': request_id,
            'timestamp': timestamp,
            'environment': environment,
            'validator_uid': validator_uid,
            'validator_hotkey': validator_hotkey,
            'status': 'error' if error else 'success',
            'video_path': str(logged_video_path) if logged_video_path else None,
            'metadata_path': str(metadata_path)
        })

        # Clean up old requests if we exceed max_requests
        self._cleanup_old_requests()

        # Save updated index
        self._save_index()

        return str(logged_video_path) if logged_video_path else ""

    def _detect_environment(self, video_url: str) -> str:
        """
        Detect environment based on video URL.

        Args:
            video_url: Video URL from request

        Returns:
            'production' if HTTPS URL, 'testing' if file path or local URL
        """
        if not video_url:
            return 'unknown'

        video_url_lower = video_url.lower()

        # Production: HTTPS URLs
        if video_url_lower.startswith('https://') or video_url_lower.startswith('http://'):
            return 'production'

        # Testing: File paths or local files
        if video_url_lower.startswith('file://') or '/' in video_url or '\\' in video_url:
            return 'testing'

        return 'unknown'

    def _cleanup_old_requests(self):
        """Remove old request files when exceeding max_requests."""
        if len(self.request_queue) < self.max_requests:
            return

        # Get list of current request IDs
        current_ids = {req['request_id'] for req in self.request_queue}

        # Clean up videos
        for video_file in self.videos_dir.glob("*.mp4"):
            request_id = video_file.stem
            if request_id not in current_ids:
                try:
                    video_file.unlink()
                    print(f"🗑️ Cleaned up old video: {video_file.name}")
                except Exception as e:
                    print(f"⚠️ Error deleting old video {video_file}: {e}")

        # Clean up metadata
        for metadata_file in self.metadata_dir.glob("*.json"):
            request_id = metadata_file.stem
            if request_id not in current_ids:
                try:
                    metadata_file.unlink()
                    print(f"🗑️ Cleaned up old metadata: {metadata_file.name}")
                except Exception as e:
                    print(f"⚠️ Error deleting old metadata {metadata_file}: {e}")

        # Clean up results
        for result_file in self.results_dir.glob("*"):
            # Extract request_id from result filename (format: {request_id}_final_*.mp4)
            request_id = result_file.name.split('_')[0]
            if request_id not in current_ids:
                try:
                    result_file.unlink()
                    print(f"🗑️ Cleaned up old result: {result_file.name}")
                except Exception as e:
                    print(f"⚠️ Error deleting old result {result_file}: {e}")

    def get_recent_requests(self, limit: int = 10) -> list:
        """
        Get the most recent compression requests.

        Args:
            limit: Number of recent requests to return

        Returns:
            List of recent request metadata
        """
        recent = list(self.request_queue)[-limit:]
        recent.reverse()  # Most recent first
        return recent

    def get_request_details(self, request_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific request.

        Args:
            request_id: The request ID to look up

        Returns:
            Request metadata dictionary, or None if not found
        """
        metadata_path = self.metadata_dir / f"{request_id}.json"
        if metadata_path.exists():
            try:
                with open(metadata_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"⚠️ Error loading request details: {e}")
        return None

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about logged requests.

        Returns:
            Dictionary with statistics
        """
        total_requests = len(self.request_queue)
        successful = sum(1 for req in self.request_queue if req['status'] == 'success')
        failed = total_requests - successful

        # Calculate disk usage
        videos_size = sum(f.stat().st_size for f in self.videos_dir.glob("*.mp4"))
        results_size = sum(f.stat().st_size for f in self.results_dir.glob("*"))
        total_size = videos_size + results_size

        return {
            'total_requests': total_requests,
            'successful': successful,
            'failed': failed,
            'success_rate': f"{(successful/total_requests*100):.1f}%" if total_requests > 0 else "N/A",
            'disk_usage_mb': round(total_size / (1024 * 1024), 2),
            'videos_size_mb': round(videos_size / (1024 * 1024), 2),
            'results_size_mb': round(results_size / (1024 * 1024), 2),
            'max_requests': self.max_requests
        }

    def list_available_videos(self) -> list:
        """
        List all available logged videos for testing.

        Returns:
            List of video file paths
        """
        videos = []
        for video_file in sorted(self.videos_dir.glob("*.mp4")):
            size_mb = video_file.stat().st_size / (1024 * 1024)
            videos.append({
                'request_id': video_file.stem,
                'path': str(video_file),
                'size_mb': round(size_mb, 2),
                'modified': datetime.fromtimestamp(video_file.stat().st_mtime).isoformat()
            })
        return videos

