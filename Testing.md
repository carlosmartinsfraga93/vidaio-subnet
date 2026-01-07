0|video-compressor  | ================================================================================
0|video-compressor  | 📥 NEW COMPRESSION REQUEST: 7623e776-d001-4667-9eb9-07b9911e534d
0|video-compressor  | ================================================================================
0|video-compressor  | video url: file:///workspace/vidaio-subnet/compression_logs/videos/c14b663a-43ea-42ca-9f21-31ab9d8f8cb7.mp4
0|video-compressor  | vmaf threshold: 85.0
0|video-compressor  | target codec: av1
0|video-compressor  | codec mode (requested): VBR
0|video-compressor  | target bitrate: 25.0 Mbps
0|video-compressor  | ✅ Using VBR mode as requested
0|video-compressor  | Copying local file: /workspace/vidaio-subnet/compression_logs/videos/c14b663a-43ea-42ca-9f21-31ab9d8f8cb7.mp4 (109.83 MB)
0|video-compressor  | Copying... ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00
0|video-compressor  | Video copied to: tmp/57b4792f-ea50-4601-991a-74f92109bd9d.mp4
0|video-compressor  | 2026-01-07 18:02:57.332 | INFO     | __main__:map_codec_name:312 - Mapped codec 'av1' → 'av1_nvenc' (GPU=True)
0|video-compressor  | 🎬 Early Scene Classification (for bitrate calculation)
0|video-compressor  | 🎬 CLIP Scene Classification
0|video-compressor  |    Video: tmp/57b4792f-ea50-4601-991a-74f92109bd9d.mp4
0|video-compressor  |    Frames to extract: 3
0|video-compressor  |    Extracting 3 frames...
0|video-compressor  |    ✅ Extracted 3 frames in 1.64s
0|video-compressor  | ✅ Using cached CLIP classifier (already loaded)
0|video-compressor  | 📊 CLIP Classification Results:
0|video-compressor  |    Best Category: Screen Content / Text
0|video-compressor  |    Confidence: 0.090
0|video-compressor  |    Animation: 0.031
0|video-compressor  |    Faces: 0.042
0|video-compressor  |    Screen: 0.090
0|video-compressor  |    Gaming: 0.037
0|video-compressor  | ⏱️ Timing:
0|video-compressor  |    Frame extraction: 1.64s
0|video-compressor  |    CLIP classification: 2.93s
0|video-compressor  |    Total: 4.57s
0|video-compressor  |    Classification: Screen Content / Text → Scene type: low-action
0|video-compressor  |    📐 Formula-based target: 3.50 Mbps
0|video-compressor  |       Scene: low-action, Resolution: 1920x1080, FPS: 30.0
0|video-compressor  |    ⚠️ Content complexity detected: medium motion (0.100), high texture (7.1)
0|video-compressor  |    📈 Adjusted minimum bitrate: 3.50 → 4.62 Mbps (1.32x)
0|video-compressor  | 📊 VBR Bitrate Calculation:
0|video-compressor  |    Scene type: low-action
0|video-compressor  |    Input bitrate: 30.91 Mbps
0|video-compressor  |    Codec efficiency: 25%
0|video-compressor  |    Quality multiplier: 0.5x
0|video-compressor  |    Calculated target: 3.86 Mbps
0|video-compressor  |    User requested: 25.00 Mbps
0|video-compressor  |    Picked (min of above): 3.86 Mbps
0|video-compressor  |    Minimum required: 4.62 Mbps (for low-action + Low)
0|video-compressor  |    Selection: Picked 3.86 < minimum 4.62, using minimum
0|video-compressor  |    Final target: 4.62 Mbps
0|video-compressor  | ⚠️ Config file not found, using default configuration
0|video-compressor  | 🎬 === AI Video Compression Pipeline ===
0|video-compressor  |    📁 Input: 57b4792f-ea50-4601-991a-74f92109bd9d.mp4
0|video-compressor  |    🎯 Target Quality: Low
0|video-compressor  |    ⏱️ Max Duration: 3600s
0|video-compressor  |    📁 Output Dir: output
0|video-compressor  |    🕐 Started: 2026-01-07 18:03:21
0|video-compressor  | ⚡ === Part 1: Pre-processing (SKIPPED - Lightweight Metadata) ===
0|video-compressor  |    📏 Extracting metadata from already-compressed video
0|video-compressor  |    ✅ Duration: 29.8s
0|video-compressor  |    ✅ Codec: h264
0|video-compressor  |    🎯 Target: Low (VMAF: 85.0)
0|video-compressor  |    🎥 Target codec: av1_nvenc
0|video-compressor  |    ⏱️ Metadata extraction: 0.20s
0|video-compressor  | ⚡ === Part 2: Scene Detection (SKIPPED) ===
0|video-compressor  |    📏 Treating entire video as single scene (pre-chunked input)
0|video-compressor  |    ⏱️ Scene setup: 0.00s
0|video-compressor  |    ✅ 1 scene created (0.0s - 29.8s)
0|video-compressor  | 🧠 === Part 3: AI Encoding ===
0|video-compressor  |    📋 Using quality-based CQ lookup tables for Low quality
0|video-compressor  |    🎯 Target Quality Level: Low
0|video-compressor  |    🎚️ CQ Range for Low: 22-28 (Target VMAF: 85)
0|video-compressor  |    🔧 Loading AI models and resources...
0|video-compressor  |    🔧 Loading AI models for the first time...
0|video-compressor  |    ⚡ CLIP classification enabled - skipping MobileNetV3 model load
0|video-compressor  |    💡 Using CLIP for scene classification (faster, no model file needed)
0|video-compressor  | ✅ Preprocessing classes are available through utils module
0|video-compressor  | 📖 Loading preprocessing pipeline from: services/compress/models/preprocessing_pipeline.pkl
0|video-compressor  |    🔧 Using default unpickler for sklearn.pipeline.Pipeline
0|video-compressor  |    🔧 Handling services.compress.utils.data_preprocessing context for class: ColumnDropper
0|video-compressor  |    ✅ Found ColumnDropper in utils module (remapped from services.compress.utils)
0|video-compressor  |    🔧 Handling services.compress.utils.data_preprocessing context for class: ResolutionTransformer
0|video-compressor  |    ✅ Found ResolutionTransformer in utils module (remapped from services.compress.utils)
0|video-compressor  |    🔧 Handling services.compress.utils.data_preprocessing context for class: FrameRateTransformer
0|video-compressor  |    ✅ Found FrameRateTransformer in utils module (remapped from services.compress.utils)
0|video-compressor  |    🔧 Using default unpickler for numpy._core.multiarray.scalar
0|video-compressor  |    🔧 Using default unpickler for numpy.dtype
0|video-compressor  |    🔧 Handling services.compress.utils.data_preprocessing context for class: CQScaler
0|video-compressor  |    ✅ Found CQScaler in utils module (remapped from services.compress.utils)
0|video-compressor  |    🔧 Handling services.compress.utils.data_preprocessing context for class: FeatureScaler
0|video-compressor  |    ✅ Found FeatureScaler in utils module (remapped from services.compress.utils)
0|video-compressor  |    🔧 Using default unpickler for sklearn.preprocessing._data.MinMaxScaler
0|video-compressor  |    🔧 Using default unpickler for numpy._core.multiarray._reconstruct
0|video-compressor  |    🔧 Using default unpickler for numpy.ndarray
0|video-compressor  |    🔧 Handling services.compress.utils.data_preprocessing context for class: VMAFScaler
0|video-compressor  |    ✅ Found VMAFScaler in utils module (remapped from services.compress.utils)
0|video-compressor  |    🔧 Handling services.compress.utils.data_preprocessing context for class: TargetExtractor
0|video-compressor  |    ✅ Found TargetExtractor in utils module (remapped from services.compress.utils)
0|video-compressor  |    🔧 Using default unpickler for sklearn.ensemble._gb.GradientBoostingRegressor
0|video-compressor  |    🔧 Using default unpickler for sklearn._loss.loss.HalfSquaredError
0|video-compressor  |    🔧 Using default unpickler for _loss.CyHalfSquaredError
0|video-compressor  |    🔧 Using default unpickler for sklearn._loss.link.IdentityLink
0|video-compressor  |    🔧 Using default unpickler for sklearn._loss.link.Interval
0|video-compressor  |    🔧 Using default unpickler for sklearn.dummy.DummyRegressor
0|video-compressor  |    🔧 Using default unpickler for sklearn.tree._classes.DecisionTreeRegressor
0|video-compressor  |    🔧 Using default unpickler for numpy.random._pickle.__randomstate_ctor
0|video-compressor  |    🔧 Using default unpickler for numpy.random._pickle.__bit_generator_ctor
0|video-compressor  |    🔧 Using default unpickler for numpy.random._mt19937.MT19937
0|video-compressor  |    🔧 Using default unpickler for sklearn.tree._tree.Tree
0|video-compressor  |    ✅ Pipeline loaded with custom unpickler
0|video-compressor  | ✅ Pipeline loaded successfully
0|video-compressor  | 🔧 Setting verbosity to True for all pipeline components...
0|video-compressor  |    🔧 Set verbose=True for step 'resolution_transformer'
0|video-compressor  |    🔧 Set verbose=True for step 'frame_rate_transformer'
0|video-compressor  |    🔧 Set verbose=True for step 'cq_scaler'
0|video-compressor  |    🔧 Set verbose=True for step 'feature_scaler'
0|video-compressor  |    🔧 Set verbose=True for step 'vmaf_scaler'
0|video-compressor  |    🔧 Set verbose=True for step 'vmaf_predictor'
0|video-compressor  | ✅ Loaded pipeline is fitted and ready for use
0|video-compressor  | ✅ Found feature scaler step: 'feature_scaler'
0|video-compressor  | ✅ Found VMAF scaler step: 'vmaf_scaler'
0|video-compressor  | ✅ Found CQ range in step 'cq_scaler': 0-63
0|video-compressor  | 📊 Using CQ optimization range: 0-63
0|video-compressor  |    💡 This range will constrain the binary search for optimal quality parameters
0|video-compressor  |    ✅ Preprocessing pipeline loaded from services/compress/models/preprocessing_pipeline.pkl
0|video-compressor  |    ✅ AI models loaded and cached successfully (0.6s)
0|video-compressor  |    💡 Subsequent requests will reuse cached models
0|video-compressor  |    ✅ AI resources loaded successfully
0|video-compressor  |    🧠 Mode: Scene classification + CQ lookup table
0|video-compressor  |    📊 Processing 1 scenes with AI approach...
0|video-compressor  |    🎬 Scene 1/1: 57b4792f-ea50-4601-991a-74f92109bd9d.mp4
0|video-compressor  |       ⏱️ Duration: 29.8s
0|video-compressor  |       🎯 Target Quality: Low (VMAF≈85.0)
0|video-compressor  |       🧠 Method: scene classification + CQ lookup
0|video-compressor  | 🎬 Processing Scene 1
0|video-compressor  |    📁 File: 57b4792f-ea50-4601-991a-74f92109bd9d.mp4
0|video-compressor  |    ⏱️ Timing: 0.0s - 29.8s (duration: 29.8s)
0|video-compressor  |    🎯 Using target codec from request: av1_nvenc
0|video-compressor  |    🎥 Final Selected Codec: av1_nvenc
0|video-compressor  |    ⚙️ Codec Mode: VBR, Target Bitrate: 4.62 Mbps
0|video-compressor  |    🤖 Running scene classification and feature extraction...
0|video-compressor  |    📐 Using image_size: 384x384 for scene classification
0|video-compressor  | 🚀 Using CLIP scene classification (fast mode)
0|video-compressor  | 🎬 CLIP Scene Classification
0|video-compressor  |    Video: tmp/57b4792f-ea50-4601-991a-74f92109bd9d.mp4
0|video-compressor  |    Frames to extract: 3
0|video-compressor  |    Extracting 3 frames...
0|video-compressor  |    ✅ Extracted 3 frames in 1.65s
0|video-compressor  | ✅ Using cached CLIP classifier (already loaded)
0|video-compressor  | 📊 CLIP Classification Results:
0|video-compressor  |    Best Category: Screen Content / Text
0|video-compressor  |    Confidence: 0.090
0|video-compressor  |    Animation: 0.031
0|video-compressor  |    Faces: 0.042
0|video-compressor  |    Screen: 0.090
0|video-compressor  |    Gaming: 0.037
0|video-compressor  | ⏱️ Timing:
0|video-compressor  |    Frame extraction: 1.65s
0|video-compressor  |    CLIP classification: 1.94s
0|video-compressor  |    Total: 3.59s
0|video-compressor  |    🎭 Scene classified as: 'Screen Content / Text' (Confidence: 0.09)
0|video-compressor  |    🔄 Mapped scene type 'Screen Content / Text' -> 'low-action' for CQ lookup
0|video-compressor  |    🎯 Target quality level: Low
0|video-compressor  |    🎯 Using OPTIMAL BITRATE CONTROLLER (Scene-Aware)
0|video-compressor  |    🎭 Optimal controller scene type: other
0|video-compressor  |    🎯 VMAF threshold: 85.0
0|video-compressor  |    ⚙️ Codec mode: VBR
0|video-compressor  | ================================================================================
0|video-compressor  | 🎯 OPTIMAL BITRATE CONTROLLER (SCENE-AWARE)
0|video-compressor  | ================================================================================
0|video-compressor  | Input: tmp/57b4792f-ea50-4601-991a-74f92109bd9d.mp4
0|video-compressor  | Codec: av1_nvenc (av1)
0|video-compressor  | Mode: VBR
0|video-compressor  | Scene Type: other
0|video-compressor  | VMAF Threshold: 85.0
0|video-compressor  | 🎯 VBR Mode - Settings: {'b:v': 2.485537387731939, 'maxrate': 2.609814257118536, 'bufsize': 6.213843469329847} (scene: other)
0|video-compressor  | 📊 Optimal Encoding Parameters:
0|video-compressor  |    Scene type: other
0|video-compressor  |    Original bitrate: 30.92 Mbps
0|video-compressor  |    Complexity score: 5.03
0|video-compressor  |    Target ratio: 17.5x
0|video-compressor  |    Target bitrate: 2.49 Mbps
0|video-compressor  |    Min safe bitrate: 2.49 Mbps
0|video-compressor  |    Grain: 3.1428, Texture: 7.0540, Motion: 0.0377
0|video-compressor  | 📝 Encoding with:
0|video-compressor  |    Rate parameter: 2.485537387731939
0|video-compressor  |    Target bitrate: 2.49 Mbps
0|video-compressor  |    Expected ratio: 17.5x
0|video-compressor  |    Complexity: 5.03
0|video-compressor  | Encoding video using codec: av1_nvenc, scene: other, model_predicted_rate: 2.485537387731939
0|video-compressor  | Using contrast value: 0.50
0|video-compressor  | Video duration: 29.8s
0|video-compressor  | Applying scene-specific params for 'other': {'keyint': 100}
0|video-compressor  | ⚡ Duration-based preset selection: 29.8s → preset 'p4'
0|video-compressor  |    Strategy: Balance speed/quality for validator timeout (~60-120s)
0|video-compressor  | Applying contrast-specific params: {'aq': 1}
0|video-compressor  | Applying codec_mode='VBR' with target_bitrate=2.485537387731939 Mbps
0|video-compressor  | Set NVENC/QSV rate control to VBR with CQ quality control
0|video-compressor  | VBR mode: avg bitrate=2485k, maxrate=2485k, bufsize=4970k
0|video-compressor  |    CQ will control quality floor, bitrate will be capped at maxrate
0|video-compressor  | Applying codec-specific CQ directly for av1_nvenc: 2
0|video-compressor  | ⚠️ VBR mode detected for av1_nvenc: Removing CQ=2 (incompatible with VBR)
0|video-compressor  |    Quality will be controlled by spatial-aq, temporal-aq, and aq-strength
0|video-compressor  | Audio detected: False
0|video-compressor  | Final FFmpeg output args: {'vcodec': 'av1_nvenc', 'preset': 'p4', 'g': 100, 'pix_fmt': 'yuv420p', 'aq': 1, 'maxrate': '2485k', 'bufsize': '4970k', 'b:v': '2485k', 'rc:v': 'vbr', 'spatial-aq': 1, 'temporal-aq': 1, 'aq-strength': 8, 'map': '0:v:0'}
0|video-compressor  | ⏱️ [TIMING] Starting FFmpeg execution...
0|video-compressor  | ⏱️ [TIMING] FFmpeg command build: 0.002s
0|video-compressor  | ⏱️ [TIMING] Starting FFmpeg encoding process...
0|video-compressor  | ⏱️ [TIMING] FFmpeg encoding completed: 9.658s
0|video-compressor  | ⏱️ [TIMING] Result processing: 0.000s
0|video-compressor  | ⏱️ [TIMING] Total encode_video() time: 9.660s
0|video-compressor  | ⏱️ [TIMING] Breakdown: build=0.002s, encode=9.658s, process=0.000s
0|video-compressor  | Successfully encoded using av1_nvenc scene 'other': ./videos/temp_scenes/encoded_scene_001_0s-30s_av1_nvenc_6e171aef.mp4
0|video-compressor  | ✅ Encoding completed in 30.48s
0|video-compressor  | ================================================================================
0|video-compressor  | ✅ Scene 1 Encoding Complete (Optimal Controller)
0|video-compressor  |    📦 Compression: 12.35x
0|video-compressor  |    ⏱️ Total Time: 34.1s
0|video-compressor  |       ✅ Scene 1 encoded successfully
0|video-compressor  |          📁 Output: encoded_scene_001_0s-30s_av1_nvenc_6e171aef.mp4
0|video-compressor  |          📊 Size: 0.0 MB → 0.0 MB (+12.4% compression)
0|video-compressor  |          🎭 Scene type: Screen Content / Text
0|video-compressor  |          🎯 Quality: Low
0|video-compressor  |          🎚️ CQ used: N/A → unknown (after adjustment)
0|video-compressor  |          📋 Method: Quality-based lookup table CQ selection
0|video-compressor  |          ⏱️ Processing: 34.1s
0|video-compressor  |    📊 Part 3 Processing Summary:
0|video-compressor  |       ✅ Successful encodings: 1
0|video-compressor  |       ❌ Failed encodings: 0
0|video-compressor  |       📈 Success rate: 100.0%
0|video-compressor  |       ⏱️ Total processing time: 34.7s
0|video-compressor  |       🎯 Quality Level: Low
0|video-compressor  |       🧠 AI Method: Scene classification + quality-based CQ lookup
0|video-compressor  | ✅ Part 3 completed with 1 successful encodings
0|video-compressor  | 🔗 --- Part 4: Validation and Merging ---
0|video-compressor  |    🎬 Processing 1 scenes with VMAF data
0|video-compressor  | calculate_full_video_vmaf flag: True
0|video-compressor  |    📁 Output directory: output
0|video-compressor  |    📁 Temp directory: ./videos/temp_scenes
0|video-compressor  |    ✅ Output directory ready: output
0|video-compressor  |    🔍 Validating encoded scenes...
0|video-compressor  |       Validating scene 1...
0|video-compressor  |          ✅ Scene 1 valid (8.9 MB)
0|video-compressor  |    📊 Scene validation results:
0|video-compressor  |       ✅ Successfully encoded scenes: 1
0|video-compressor  |       📊 Scenes with VMAF data: 0
0|video-compressor  |       🔍 Scenes without VMAF: 1
0|video-compressor  |    ✅ Using VMAF data from Part 4 (or skipped if disabled)
0|video-compressor  |    🔗 Starting video merging process...
0|video-compressor  |       Merging 1 encoded scenes...
0|video-compressor  |       📁 Using default pattern: 57b4792f-ea50-4601-991a-74f92109bd9d_final_unknown_20260107_180355.mp4
0|video-compressor  |       📁 Output file: 57b4792f-ea50-4601-991a-74f92109bd9d_final_unknown_20260107_180355.mp4
0|video-compressor  |          Scene 1: encoded_scene_001_0s-30s_av1_nvenc_6e171aef.mp4 (8.9 MB)
0|video-compressor  |       🎬 Executing video merge...
0|video-compressor  | ✅ Single scene copied to output/57b4792f-ea50-4601-991a-74f92109bd9d_final_unknown_20260107_180355.mp4
0|video-compressor  |    ✅ Video merging completed in 0.0s
0|video-compressor  |    📁 Final video: 57b4792f-ea50-4601-991a-74f92109bd9d_final_unknown_20260107_180355.mp4 (8.9 MB)
0|video-compressor  |    🧹 Cleaning up encoded scene files...
0|video-compressor  |       🗑️ Deleted: encoded_scene_001_0s-30s_av1_nvenc_6e171aef.mp4
0|video-compressor  |    ✅ Encoded scenes cleanup: 1 deleted, 0 failed
0|video-compressor  |    ⏭️ Skipping full video VMAF calculation (disabled in config)
0|video-compressor  |    ⏭️ No scene VMAF data available for estimation
0|video-compressor  |    📋 Generating comprehensive report...
0|video-compressor  |    💾 Saving comprehensive processing report...
0|video-compressor  |       📁 Report filename: 57b4792f-ea50-4601-991a-74f92109bd9d_encoding_report.json
0|video-compressor  |       📊 Extracted from: 57b4792f-ea50-4601-991a-74f92109bd9d.mp4
0|video-compressor  |       📄 Saved comprehensive report: 57b4792f-ea50-4601-991a-74f92109bd9d_encoding_report.json
0|video-compressor  | 🎉 --- Part 4 Completed Successfully ---
0|video-compressor  |    📁 Final video: 57b4792f-ea50-4601-991a-74f92109bd9d_final_unknown_20260107_180355.mp4
0|video-compressor  |    🗜️ Overall compression: +0.0%
0|video-compressor  |    ⏱️ Total processing time: 0.0s
0|video-compressor  |    📊 Scenes meeting target: 0/0
0|video-compressor  |    🔍 VMAF data from Part 4: 0/1 scenes
0|video-compressor  | ✅ Part 4 completed successfully in 0.0s!
0|video-compressor  |    📁 Final video: 57b4792f-ea50-4601-991a-74f92109bd9d_final_unknown_20260107_180355.mp4
0|video-compressor  |    🗜️ Overall compression: +0.0%
0|video-compressor  |    📊 Final file size: 8.9 MB
0|video-compressor  | 🎉 === Pipeline Completed Successfully ===
0|video-compressor  |    📁 Input video: 57b4792f-ea50-4601-991a-74f92109bd9d.mp4
0|video-compressor  |    📁 Final video: 57b4792f-ea50-4601-991a-74f92109bd9d_final_unknown_20260107_180355.mp4
0|video-compressor  |    🎯 Target quality: Low (VMAF: 85.0)
0|video-compressor  |    📊 Scenes processed: 1 total, 1 successful
0|video-compressor  |    📁 Output directory: output
0|video-compressor  |    🕐 Completed: 2026-01-07 18:03:55
0|video-compressor  |    ⏱️ Performance Breakdown:
0|video-compressor  |       Part 1 (Pre-processing): 0.2s
0|video-compressor  |       Part 2 (Scene Detection): 0.0s
0|video-compressor  |       Part 3 (AI Encoding): 34.7s
0|video-compressor  |       Part 4 (Validation & Merging): 0.0s
0|video-compressor  |       Total Pipeline Time: 35.0s
0|video-compressor  |    📊 Final Size Comparison:
0|video-compressor  |       Input: 109.8 MB
0|video-compressor  |       Output: 8.9 MB
0|video-compressor  |       Compression: +91.9%
0|video-compressor  |       💾 Space saved: 100.9 MB
0|video-compressor  |    📄 Reports Generated:
0|video-compressor  |       📁 Output directory: output
0|video-compressor  |       📊 Comprehensive report: comprehensive_processing_report_*.json
0|video-compressor  |       📄 Individual scene reports: scene_reports/scene_*_report.json
0|video-compressor  |    🎉 Pipeline completed successfully!
0|video-compressor  |    🚀 Ready for playback: output/57b4792f-ea50-4601-991a-74f92109bd9d_final_unknown_20260107_180355.mp4
0|video-compressor  | compressed_video_path: output/57b4792f-ea50-4601-991a-74f92109bd9d_final_unknown_20260107_180355.mp4
0|video-compressor  | object_name: 57b4792f-ea50-4601-991a-74f92109bd9d_final_unknown_20260107_180355.mp4
0|video-compressor  | Video uploaded successfully.
0|video-compressor  | 📝 Logged video: compression_logs/videos/7623e776-d001-4667-9eb9-07b9911e534d.mp4
0|video-compressor  | 📝 Logged metadata: compression_logs/metadata/7623e776-d001-4667-9eb9-07b9911e534d.json [env=testing]
0|video-compressor  | 🔍 Looking for encoding report at: output/57b4792f-ea50-4601-991a-74f92109bd9d_encoding_report.json
0|video-compressor  |    Input path: tmp/57b4792f-ea50-4601-991a-74f92109bd9d.mp4
0|video-compressor  |    Output dir: output
0|video-compressor  |    Report exists: True
0|video-compressor  |    📊 Found 1 scenes in encoding report
0|video-compressor  | 📊 Scheduled async VMAF calculation for request 7623e776-d001-4667-9eb9-07b9911e534d
0|video-compressor  | 🗑️ Deleted compressed file: output/57b4792f-ea50-4601-991a-74f92109bd9d_final_unknown_20260107_180355.mp4
0|video-compressor  | 🗑️ Deleted downloaded file: tmp/57b4792f-ea50-4601-991a-74f92109bd9d.mp4
0|video-compressor  | sharing_link: https://s3.hippius.com/vidaio/57b4792f-ea50-4601-991a-74f92109bd9d_final_unknown_20260107_180355.mp4?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=hip_0baf07a6a481e5b09c842be9%2F20260107%2Fus-east-1%2Fs3%2Faws4_request&X-Amz-Date=20260107T180406Z&X-Amz-Expires=604800&X-Amz-SignedHeaders=host&X-Amz-Signature=25fb9bfbfed575d9b9dbee4450b6932f39450996c6b65d5975c72ee642323a10
0|video-compressor  | INFO:     ::1:52304 - "POST /compress-video HTTP/1.1" 200 OK
0|video-compressor  | 📊 [ASYNC VMAF] Starting VMAF calculation for request 7623e776-d001-4667-9eb9-07b9911e534d
0|video-compressor  |    🟢 Validator method (VMAFNEG) - 10 random frames...
0|video-compressor  |    📋 Sampled 10 frames: [238, 279, 325, 379, 393, 424, 455, 520, 532, 863]
0|video-compressor  | ⚠️ [ASYNC VMAF] Request 7623e776-d001-4667-9eb9-07b9911e534d [TESTING]:
0|video-compressor  |    👤 No validator info
0|video-compressor  |    📊 VMAF Score: 67.55 (Target: 85.00)
0|video-compressor  |    Margin: -17.45 points
0|video-compressor  |    Scene: Screen Content / Text, CQ: None
0|video-compressor  |    Mode: VBR
0|video-compressor  |    Bitrate: Original: 30.91 Mbps, Requested: 25.0 Mbps, Applied: 4.62 Mbps, Actual: 2.50 Mbps
0|video-compressor  |    Compression: 12.35x
0|video-compressor  |    Calculation time: 61.1s
0|video-compressor  |    Log saved: compression_logs/vmaf/7623e776-d001-4667-9eb9-07b9911e534d_vmaf.json
0|video-compressor  | 🗑️ [ASYNC VMAF] Cleaned up original copy: 7623e776-d001-4667-9eb9-07b9911e534d_original.mp4
0|video-compressor  | 🗑️ [ASYNC VMAF] Cleaned up compressed copy: 7623e776-d001-4667-9eb9-07b9911e534d_compressed.mp4