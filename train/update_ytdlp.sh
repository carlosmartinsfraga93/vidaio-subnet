#!/bin/bash
# Update yt-dlp to latest version to fix YouTube download issues

echo "🔄 Updating yt-dlp to latest version..."

# Update yt-dlp
pip install --upgrade yt-dlp

# Verify version
echo ""
echo "✅ yt-dlp updated!"
yt-dlp --version

echo ""
echo "💡 If you still see errors, try:"
echo "   1. Update again: pip install --upgrade --force-reinstall yt-dlp"
echo "   2. Use alternative sources: python download_datasets.py --sources pexels --pexels_api_key YOUR_KEY"


