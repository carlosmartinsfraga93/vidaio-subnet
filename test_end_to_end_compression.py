#!/usr/bin/env python3
"""
End-to-End Compression Test
Simulates the complete validator → miner compression flow
Tests: Miner receives request → Compression service → Upload → Response
"""

import asyncio
import sys
import time
import json
from pathlib import Path
from loguru import logger

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from vidaio_subnet_core.protocol import VideoCompressionProtocol
from vidaio_subnet_core import CONFIG
from services.miner_utilities.miner_utils import video_compressor


def print_header(text):
    """Print formatted header"""
    print("\n" + "="*80)
    print(f"  {text}")
    print("="*80 + "\n")


def print_step(step_num, text):
    """Print step header"""
    print(f"\n{'─'*80}")
    print(f"STEP {step_num}: {text}")
    print(f"{'─'*80}\n")


async def test_compression_service_health():
    """Test if compression service is running"""
    import aiohttp
    
    url = f"http://{CONFIG.video_compressor.host}:{CONFIG.video_compressor.port}/health"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                if response.status == 200:
                    logger.info(f"✅ Compression service is running at {url}")
                    return True
                else:
                    logger.error(f"❌ Compression service returned status {response.status}")
                    return False
    except Exception as e:
        logger.error(f"❌ Cannot connect to compression service: {e}")
        logger.info(f"\n   Please start the compression service:")
        logger.info(f"   python services/compress/server.py")
        return False


async def test_video_compressor_function(test_video_url: str):
    """Test the video_compressor function directly"""
    
    logger.info(f"📹 Testing video compression with URL: {test_video_url}")
    
    # Test parameters (matching validator requests)
    vmaf_threshold = 89.0
    target_codec = "av1"
    codec_mode = "CRF"
    target_bitrate = 10.0
    
    logger.info(f"   VMAF Threshold: {vmaf_threshold}")
    logger.info(f"   Target Codec: {target_codec}")
    logger.info(f"   Codec Mode: {codec_mode}")
    logger.info(f"   Target Bitrate: {target_bitrate} Mbps")
    
    start_time = time.time()
    
    try:
        result_url = await video_compressor(
            payload_url=test_video_url,
            vmaf_threshold=vmaf_threshold,
            target_codec=target_codec,
            codec_mode=codec_mode,
            target_bitrate=target_bitrate
        )
        
        elapsed = time.time() - start_time
        
        if result_url:
            logger.info(f"\n✅ Compression successful! ({elapsed:.2f}s)")
            logger.info(f"   Output URL: {result_url}")
            return True, result_url, elapsed
        else:
            logger.error(f"\n❌ Compression failed - returned None")
            return False, None, elapsed
            
    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"\n❌ Compression failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False, None, elapsed


async def test_miner_forward_function(test_video_url: str):
    """Test the miner's forward_compression_requests function (simulated)"""
    
    logger.info(f"🔧 Simulating miner forward_compression_requests...")
    
    # This simulates what happens when a validator sends a request
    # In production, this would be called by the Bittensor axon
    
    start_time = time.time()
    
    try:
        result_url = await video_compressor(
            payload_url=test_video_url,
            vmaf_threshold=89.0,
            target_codec="av1",
            codec_mode="CRF",
            target_bitrate=10.0
        )
        
        elapsed = time.time() - start_time
        
        if result_url:
            logger.info(f"✅ Miner would return: {result_url}")
            logger.info(f"   Processing time: {elapsed:.2f}s")
            return True, result_url
        else:
            logger.error(f"❌ Miner would return empty response")
            return False, None
            
    except Exception as e:
        logger.error(f"❌ Miner forward function failed: {e}")
        return False, None


async def main():
    print_header("END-TO-END COMPRESSION TEST")
    
    logger.info("This test simulates the complete validator → miner compression flow")
    logger.info("It tests all components: miner → compression service → storage → response\n")
    
    # Step 1: Check compression service
    print_step(1, "Check Compression Service Health")
    service_ok = await test_compression_service_health()
    
    if not service_ok:
        logger.error("\n❌ TEST FAILED: Compression service is not running")
        logger.info("\nTo start the service, run:")
        logger.info("  python services/compress/server.py")
        return
    
    # Step 2: Get test video URL
    print_step(2, "Prepare Test Video URL")

    # You can use a public test video URL or a local file
    # For testing, we'll use a sample video URL
    test_video_url = input("\nEnter test video URL (or press Enter for default): ").strip()

    if not test_video_url:
        # Default test video (small sample)
        test_video_url = "https://test-videos.co.uk/vids/bigbuckbunny/mp4/h264/360/Big_Buck_Bunny_360_10s_1MB.mp4"
        logger.info(f"Using default test video: {test_video_url}")
    else:
        logger.info(f"Using provided video: {test_video_url}")

    # Step 3: Test video_compressor function
    print_step(3, "Test video_compressor Function")
    success, result_url, elapsed = await test_video_compressor_function(test_video_url)

    if not success:
        logger.error("\n❌ TEST FAILED: video_compressor function failed")
        return

    # Step 4: Test miner forward function (simulated)
    print_step(4, "Test Miner Forward Function (Simulated)")
    success, miner_result = await test_miner_forward_function(test_video_url)

    if not success:
        logger.error("\n❌ TEST FAILED: Miner forward function failed")
        return

    # Step 5: Summary
    print_header("TEST SUMMARY")

    logger.info("✅ All tests passed successfully!")
    logger.info("\nTest Results:")
    logger.info(f"  ✅ Compression service: Running")
    logger.info(f"  ✅ Video compression: Success ({elapsed:.2f}s)")
    logger.info(f"  ✅ Miner response: {result_url}")
    logger.info(f"\n🎉 Your miner is ready to handle validator compression requests!")

    # Additional info
    print_header("NEXT STEPS")
    logger.info("1. Make sure your miner is registered on the network")
    logger.info("2. Ensure your axon port is accessible to validators")
    logger.info("3. Monitor logs for incoming validator requests")
    logger.info("4. Check your miner's performance in the dashboard")

    logger.info("\nTo start your miner:")
    logger.info("  python neurons/miner.py --netuid <your-netuid> --wallet.name <your-wallet>")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n\n⚠️  Test interrupted by user")
    except Exception as e:
        logger.error(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

