#!/bin/bash
# Install JavaScript runtime for yt-dlp to reduce YouTube warnings

echo "🔧 Installing JavaScript runtime for yt-dlp..."

# Option 1: Install Node.js (recommended)
if command -v node &> /dev/null; then
    echo "✅ Node.js already installed: $(node --version)"
else
    echo "📦 Installing Node.js..."
    curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
    sudo apt-get install -y nodejs
    echo "✅ Node.js installed: $(node --version)"
fi

# Option 2: Install Deno (alternative, lighter)
if command -v deno &> /dev/null; then
    echo "✅ Deno already installed: $(deno --version)"
else
    echo "📦 Installing Deno (optional, lighter alternative)..."
    curl -fsSL https://deno.land/install.sh | sh
    export DENO_INSTALL="$HOME/.deno"
    export PATH="$DENO_INSTALL/bin:$PATH"
    echo "✅ Deno installed"
fi

echo ""
echo "✅ JavaScript runtime installed!"
echo ""
echo "💡 To use with yt-dlp, add to your command:"
echo "   --js-runtimes node"
echo "   or"
echo "   --js-runtimes deno"


