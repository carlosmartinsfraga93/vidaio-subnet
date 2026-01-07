#!/usr/bin/env python3
"""
Convert existing log files from local time to UTC.

This script:
1. Scans all JSON log files in compression_logs
2. Converts timestamps from local time (GMT+9) to UTC
3. Creates backups before modifying files
4. Updates both request logs and VMAF logs
"""

import json
import shutil
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Dict, Any


# Assume logs were created in GMT+9 (JST)
LOCAL_TIMEZONE = timezone(timedelta(hours=9))


def convert_local_to_utc(timestamp_str: str) -> str:
    """
    Convert local time (GMT+9) timestamp to UTC.
    
    Args:
        timestamp_str: ISO format timestamp string (assumed to be GMT+9)
        
    Returns:
        UTC timestamp string in ISO format
    """
    try:
        # Parse the timestamp
        dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        
        # If no timezone info, assume it's local time (GMT+9)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=LOCAL_TIMEZONE)
        
        # Convert to UTC
        dt_utc = dt.astimezone(timezone.utc)
        
        # Return as ISO format string
        return dt_utc.isoformat()
    except Exception as e:
        print(f"   ⚠️ Error converting timestamp '{timestamp_str}': {e}")
        return timestamp_str


def backup_file(file_path: Path) -> Path:
    """Create a backup of the file."""
    backup_path = file_path.with_suffix(file_path.suffix + '.backup')
    shutil.copy2(file_path, backup_path)
    return backup_path


def convert_json_file(file_path: Path, dry_run: bool = False) -> bool:
    """
    Convert timestamps in a JSON file from local time to UTC.
    
    Args:
        file_path: Path to the JSON file
        dry_run: If True, only show what would be changed without modifying files
        
    Returns:
        True if file was modified, False otherwise
    """
    try:
        # Load the JSON file
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        # Track if we made any changes
        modified = False
        
        # Convert timestamp field if it exists
        if 'timestamp' in data:
            old_timestamp = data['timestamp']
            new_timestamp = convert_local_to_utc(old_timestamp)
            
            if old_timestamp != new_timestamp:
                if dry_run:
                    print(f"   Would convert: {old_timestamp} → {new_timestamp}")
                else:
                    data['timestamp'] = new_timestamp
                    print(f"   Converted: {old_timestamp} → {new_timestamp}")
                modified = True
        
        # Convert last_updated field if it exists (for request_index.json)
        if 'last_updated' in data:
            old_timestamp = data['last_updated']
            new_timestamp = convert_local_to_utc(old_timestamp)
            
            if old_timestamp != new_timestamp:
                if dry_run:
                    print(f"   Would convert last_updated: {old_timestamp} → {new_timestamp}")
                else:
                    data['last_updated'] = new_timestamp
                modified = True
        
        # Convert timestamps in request queue (for request_index.json)
        if 'requests' in data and isinstance(data['requests'], list):
            for request in data['requests']:
                if 'timestamp' in request:
                    old_timestamp = request['timestamp']
                    new_timestamp = convert_local_to_utc(old_timestamp)
                    
                    if old_timestamp != new_timestamp:
                        if not dry_run:
                            request['timestamp'] = new_timestamp
                        modified = True
        
        # Save the modified file
        if modified and not dry_run:
            # Create backup
            backup_path = backup_file(file_path)
            print(f"   📦 Backup created: {backup_path}")
            
            # Save updated file
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2)
            print(f"   ✅ Updated: {file_path}")
        
        return modified
        
    except Exception as e:
        print(f"   ❌ Error processing {file_path}: {e}")
        return False


def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Convert log timestamps from local time to UTC')
    parser.add_argument('--dry-run', action='store_true', 
                       help='Show what would be changed without modifying files')
    parser.add_argument('--log-dir', type=str, default='compression_logs',
                       help='Log directory path (default: compression_logs)')
    
    args = parser.parse_args()
    
    log_dir = Path(args.log_dir)
    
    if not log_dir.exists():
        print(f"❌ Log directory not found: {log_dir}")
        print(f"   Please make sure the directory exists or specify --log-dir")
        return
    
    print(f"🔍 Scanning log directory: {log_dir}")
    if args.dry_run:
        print("   🔎 DRY RUN MODE - No files will be modified")
    print()
    
    # Find all JSON files
    json_files = list(log_dir.rglob("*.json"))
    
    if not json_files:
        print(f"📭 No JSON files found in {log_dir}")
        return
    
    print(f"📄 Found {len(json_files)} JSON files\n")
    
    # Process each file
    modified_count = 0
    for json_file in json_files:
        print(f"Processing: {json_file.relative_to(log_dir)}")
        if convert_json_file(json_file, dry_run=args.dry_run):
            modified_count += 1
        print()
    
    # Summary
    print("=" * 80)
    if args.dry_run:
        print(f"✅ Dry run complete: {modified_count} files would be modified")
        print(f"\nRun without --dry-run to apply changes")
    else:
        print(f"✅ Conversion complete: {modified_count} files updated")
        print(f"📦 Backups created with .backup extension")
        print(f"\n💡 Tip: You can restore from backups if needed")


if __name__ == "__main__":
    main()

