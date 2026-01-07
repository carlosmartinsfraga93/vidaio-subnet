import os
import sys
import time
import torch
import pickle
import traceback
import subprocess
from sklearn.exceptions import NotFittedError
from sklearn.preprocessing import StandardScaler
from sklearn.utils.validation import check_is_fitted
from utils.processing_utils import (
    encode_scene_with_size_check,
    classify_scene_from_path
)
from utils.encode_video import encode_video
from utils.classify_scene import load_scene_classifier_model, CombinedModel
from netflix_per_title_encoder import should_use_netflix_per_title, netflix_per_title_encoding

def get_cq_from_lookup_table(scene_type, config, target_vmaf=None, target_quality_level=None):
    """
    Look up the recommended CQ (Constant Quality) value for a scene type and target quality.
      
    CQ values control encoding quality:
    - Lower CQ = Higher quality, bigger file size (CQ 15-20)
    - Higher CQ = Lower quality, smaller file size (CQ 30-35)
    
    The lookup table now supports two selection modes:
    - By explicit quality level via config['video_processing']['basic_cq_lookup_by_quality']
    - By VMAF-derived tiers via config['video_processing']['basic_cq_lookup_tiered']
    - High quality tier (VMAF 93+): Lower CQ values for better quality
    - Medium quality tier (VMAF ~88): Balanced CQ values
    - Low quality tier (VMAF ~85): Higher CQ values for smaller files
    
    Args:
        scene_type (str): Scene classification from AI model
        config (dict): Configuration containing CQ lookup tables
    target_vmaf (float, optional): Target VMAF score for quality tier (fallback)
    target_quality_level (str, optional): 'High'|'Medium'|'Low' to select from by-quality table
        
    Returns:
        int: Recommended CQ value for encoding this scene type at target quality
    """
    vp = config.get('video_processing', {})

    if target_quality_level:
        norm = {'high': 'High', 'medium': 'Medium', 'low': 'Low'}
        q_key = norm.get(str(target_quality_level).lower(), target_quality_level)
        by_quality = vp.get('basic_cq_lookup_by_quality', {})
        if isinstance(by_quality, dict):
            table = by_quality.get(q_key) or by_quality.get(q_key.lower()) or {}
            if isinstance(table, dict):
                return table.get(scene_type, table.get('default', 25))

    # Determine quality tier based on target VMAF (fallback)
    if target_vmaf is None:
        quality_tier = 'medium'  # Default to medium if no target specified
    elif target_vmaf >= 93:
        quality_tier = 'high'
    elif target_vmaf >= 88:
        quality_tier = 'medium'
    else:
        quality_tier = 'low'
    
    default_cq_map = {
        # High quality tier (lower CQ = higher quality)
        'high': {
            'animation': 28,      # VMAF 93 target - cartoons compress well
            'low-action': 26,     # VMAF 93 target - faces/people need clarity
            'medium-action': 24,  # VMAF 93 target - balanced content
            'high-action': 22,    # VMAF 93 target - high motion needs quality
            'default': 25         # VMAF 93 target - safe middle-ground
        },
        # Medium quality tier (balanced CQ)
        'medium': {
            'animation': 31,      # VMAF 89 target - cartoons compress well
            'low-action': 29,     # VMAF 89 target - faces/people (reduced from 33)
            'medium-action': 27,  # VMAF 89 target - balanced content
            'high-action': 25,    # VMAF 89 target - high motion needs quality
            'default': 28         # VMAF 89 target - safe middle-ground
        },
        # Low quality tier (higher CQ = smaller files) - Optimized for compression
        'low': {
            'animation': 34,      # VMAF 85 target - aggressive compression
            'low-action': 32,     # VMAF 85 target - aggressive compression
            'medium-action': 30,  # VMAF 85 target - aggressive compression
            'high-action': 28,    # VMAF 85 target - aggressive compression
            'default': 31         # VMAF 85 target - aggressive compression
        }
    }
    
    # Get the lookup table from config, or use our defaults
    tier_cq_maps = vp.get('basic_cq_lookup_tiered', default_cq_map)
    
    # Use the appropriate tier based on target quality
    cq_lookup_table = tier_cq_maps.get(quality_tier, tier_cq_maps.get('medium', default_cq_map['medium']))
    
    # Return the CQ for this scene type within the selected quality tier, with fallback to default
    return cq_lookup_table.get(scene_type, cq_lookup_table.get('default', 25))

def get_scalers_from_pipeline(pipeline_path='services/compress/models/preprocessing_pipeline.pkl', 
                             verbose=True, logging_enabled=True):
    """
    Load preprocessing pipeline and extract individual components with verbosity control.
    
    This function loads a complete scikit-learn preprocessing pipeline and extracts
    the individual components needed for VMAF prediction:
    - Feature scaler for normalizing video metrics
    - VMAF scaler for converting quality scores to model range
    - CQ (Constant Quality) parameter bounds for optimization
    
    The function also sets verbosity levels for all pipeline components to control
    the amount of output during batch processing operations.
    
    Pipeline Structure Expected:
        - feature_scaler: StandardScaler or similar for video features
        - vmaf_scaler: Custom scaler for VMAF quality scores  
        - cq_scaler: Custom scaler containing CQ parameter bounds
        
    Args:
        pipeline_path (str): Path to the saved preprocessing pipeline pickle file
        verbose (bool): Whether individual pipeline steps should produce verbose output
        logging_enabled (bool): Master logging control (overrides verbose if False)
        
    Returns:
        tuple: (pipeline_obj, feature_scaler_step, vmaf_scaler, cq_min, cq_max)
            - pipeline_obj: Complete fitted preprocessing pipeline
            - feature_scaler_step: Feature scaling component
            - vmaf_scaler: VMAF scaling component  
            - cq_min: Minimum CQ value for optimization bounds
            - cq_max: Maximum CQ value for optimization bounds
            Returns (None, None, None, None, None) if loading fails
    """
    
    try:
        from utils import ColumnDropper, VMAFScaler, TargetExtractor, CQScaler, ResolutionTransformer, FeatureScaler, FrameRateTransformer
        
        if logging_enabled:
            print(f"✅ Preprocessing classes are available through utils module")
            
    except ImportError as e:
        if logging_enabled:
            print(f"❌ ERROR: Could not access preprocessing classes: {e}")
            print(f"   💡 Check that utils/__init__.py properly imports data_preprocessing classes")
        return None, None, None, None, None
    
    actual_verbose = verbose and logging_enabled
    
    pipeline_obj = None
    feature_scaler_step = None
    vmaf_scaler = None
    cq_min_original, cq_max_original = None, None
    
    # =================================================================
    # PIPELINE FILE LOADING AND VALIDATION
    # =================================================================
    if not os.path.exists(pipeline_path):
        if actual_verbose:
            print(f"❌ ERROR: Pipeline file not found at '{pipeline_path}'")
            print(f"   💡 Suggestion: Ensure preprocessing pipeline exists in /models/ directory")
        return None, None, None, None, None
    
    try:
        # Load the pickled preprocessing pipeline
        if actual_verbose:
            print(f"📖 Loading preprocessing pipeline from: {pipeline_path}")
            
        # Load the pickled preprocessing pipeline with custom unpickler to handle module namespace issues
        class CustomUnpickler(pickle.Unpickler):
            def find_class(self, module, name):
                if module == '__main__':
                    if actual_verbose:
                        print(f"   🔧 Handling __main__ context for class: {name}")
                    # Try to get the class from utils module
                    try:
                        from utils import ColumnDropper, VMAFScaler, TargetExtractor, CQScaler, ResolutionTransformer, FeatureScaler, FrameRateTransformer
                        class_map = {
                            'ColumnDropper': ColumnDropper,
                            'VMAFScaler': VMAFScaler,
                            'TargetExtractor': TargetExtractor,
                            'CQScaler': CQScaler,
                            'ResolutionTransformer': ResolutionTransformer,
                            'FeatureScaler': FeatureScaler,
                            'FrameRateTransformer': FrameRateTransformer
                        }
                        if name in class_map:
                            if actual_verbose:
                                print(f"   ✅ Found {name} in utils module")
                            return class_map[name]
                        else:
                            if actual_verbose:
                                print(f"   ❌ Class {name} not found in utils module")
                    except ImportError as e:
                        if actual_verbose:
                            print(f"   ❌ Failed to import from utils: {e}")
                
                # Handle utils.data_preprocessing module context
                elif module == 'utils.data_preprocessing':
                    if actual_verbose:
                        print(f"   🔧 Handling utils.data_preprocessing context for class: {name}")
                    try:
                        from utils import ColumnDropper, VMAFScaler, TargetExtractor, CQScaler, ResolutionTransformer, FeatureScaler, FrameRateTransformer
                        class_map = {
                            'ColumnDropper': ColumnDropper,
                            'VMAFScaler': VMAFScaler,
                            'TargetExtractor': TargetExtractor,
                            'CQScaler': CQScaler,
                            'ResolutionTransformer': ResolutionTransformer,
                            'FeatureScaler': FeatureScaler,
                            'FrameRateTransformer': FrameRateTransformer
                        }
                        if name in class_map:
                            if actual_verbose:
                                print(f"   ✅ Found {name} in utils module")
                            return class_map[name]
                        else:
                            if actual_verbose:
                                print(f"   ❌ Class {name} not found in utils module")
                    except ImportError as e:
                        if actual_verbose:
                            print(f"   ❌ Failed to import from utils: {e}")

                # Handle services.compress.utils.data_preprocessing module context (from training)
                elif module == 'services.compress.utils.data_preprocessing':
                    if actual_verbose:
                        print(f"   🔧 Handling services.compress.utils.data_preprocessing context for class: {name}")
                    try:
                        from utils import ColumnDropper, VMAFScaler, TargetExtractor, CQScaler, ResolutionTransformer, FeatureScaler, FrameRateTransformer
                        class_map = {
                            'ColumnDropper': ColumnDropper,
                            'VMAFScaler': VMAFScaler,
                            'TargetExtractor': TargetExtractor,
                            'CQScaler': CQScaler,
                            'ResolutionTransformer': ResolutionTransformer,
                            'FeatureScaler': FeatureScaler,
                            'FrameRateTransformer': FrameRateTransformer
                        }
                        if name in class_map:
                            if actual_verbose:
                                print(f"   ✅ Found {name} in utils module (remapped from services.compress.utils)")
                            return class_map[name]
                        else:
                            if actual_verbose:
                                print(f"   ❌ Class {name} not found in utils module")
                    except ImportError as e:
                        if actual_verbose:
                            print(f"   ❌ Failed to import from utils: {e}")

                # For other modules, use the default behavior
                if actual_verbose:
                    print(f"   🔧 Using default unpickler for {module}.{name}")
                return super().find_class(module, name)
        
        # Try to load with custom unpickler
        try:
            with open(pipeline_path, 'rb') as f:
                unpickler = CustomUnpickler(f)
                pipeline_obj = unpickler.load()
            if actual_verbose:
                print(f"   ✅ Pipeline loaded with custom unpickler")
        except Exception as e:
            if actual_verbose:
                print(f"   ❌ Custom unpickler failed: {e}")
                print(f"   🔧 Attempting to load with standard pickle...")
            
            # Fallback to standard pickle loading
            with open(pipeline_path, 'rb') as f:
                pipeline_obj = pickle.load(f)
            
            if actual_verbose:
                print(f"   ✅ Pipeline loaded with standard pickle")
            
        if actual_verbose:
            print(f"✅ Pipeline loaded successfully")
        
        def set_pipeline_verbosity(pipeline, verbose_flag):
            """
            Recursively set verbose parameter for all pipeline components.
            
            Handles nested pipelines, feature unions, column transformers,
            and custom transformer classes.
            """
            if hasattr(pipeline, 'steps'):
                # Handle sklearn Pipeline objects
                for step_name, step_obj in pipeline.steps:
                    set_step_verbosity(step_obj, verbose_flag, step_name)
            elif hasattr(pipeline, 'named_steps'):
                # Handle pipelines with named step access
                for step_name, step_obj in pipeline.named_steps.items():
                    set_step_verbosity(step_obj, verbose_flag, step_name)
            else:
                # Handle single transformer objects
                set_step_verbosity(pipeline, verbose_flag, "pipeline")
        
        def set_step_verbosity(step_obj, verbose_flag, step_name="unknown"):
            """
            Set verbosity for a single pipeline step.
            
            Handles various transformer types and their verbosity parameters.
            """
            try:
                # ==========================================================
                # STANDARD VERBOSITY PARAMETERS
                # ==========================================================
                # Common verbose parameters found in sklearn and custom transformers
                verbose_attrs = ['verbose', 'verbose_', 'logging_enabled']
                
                for attr in verbose_attrs:
                    if hasattr(step_obj, attr):
                        setattr(step_obj, attr, verbose_flag)
                        if actual_verbose and verbose_flag:
                            print(f"   🔧 Set {attr}={verbose_flag} for step '{step_name}'")
                
                # ==========================================================
                # NESTED PIPELINE HANDLING
                # ==========================================================
                # Handle Pipeline objects nested within other pipelines
                if hasattr(step_obj, 'steps') or hasattr(step_obj, 'named_steps'):
                    set_pipeline_verbosity(step_obj, verbose_flag)
                
                # Handle wrapped transformers
                if hasattr(step_obj, 'transformer') and step_obj.transformer is not None:
                    set_step_verbosity(step_obj.transformer, verbose_flag, f"{step_name}.transformer")
                
                # ==========================================================
                # COMPOSITE TRANSFORMER HANDLING
                # ==========================================================
                # Handle FeatureUnion and ColumnTransformer which contain lists of transformers
                if hasattr(step_obj, 'transformer_list'):
                    for name, transformer in step_obj.transformer_list:
                        set_step_verbosity(transformer, verbose_flag, f"{step_name}.{name}")
                
                # ==========================================================
                # CUSTOM TRANSFORMER SPECIFIC PARAMETERS
                # ==========================================================
                # Handle verbosity parameters specific to our custom transformers
                custom_transformer_attrs = ['debug', 'show_warnings', 'print_info']
                for attr in custom_transformer_attrs:
                    if hasattr(step_obj, attr):
                        setattr(step_obj, attr, verbose_flag)
                        if actual_verbose and verbose_flag:
                            print(f"   🎛️ Set custom {attr}={verbose_flag} for step '{step_name}'")
                            
            except Exception as e:
                if actual_verbose:
                    print(f"  ⚠️ Warning: Could not set verbosity for step '{step_name}': {e}")
        
        # Apply verbosity settings to the entire pipeline
        if actual_verbose:
            print(f"🔧 Setting verbosity to {actual_verbose} for all pipeline components...")
        
        set_pipeline_verbosity(pipeline_obj, actual_verbose)
        
        # =================================================================
        # PIPELINE FITNESS VALIDATION
        # =================================================================
        # Check if the loaded pipeline has been fitted (trained)
        # Unfitted pipelines cannot be used for transformation
        try:
            check_is_fitted(pipeline_obj)
            if actual_verbose:
                print("✅ Loaded pipeline is fitted and ready for use")
        except NotFittedError:
            if actual_verbose:
                print("⚠️ WARNING: Loaded pipeline is NOT fitted!")
                print("   🔧 Attempting to extract components anyway for fallback creation...")
        except Exception as e:
            if actual_verbose:
                print(f"⚠️ Warning: Could not verify pipeline fitness: {e}")

        # =================================================================
        # FEATURE SCALER EXTRACTION
        # =================================================================
        # Extract the feature scaling component used for normalizing video metrics
        feature_scaler_step = None
        scaler_step_name = 'feature_scaler'
        
        # Try to find by name in named_steps
        if hasattr(pipeline_obj, 'named_steps') and scaler_step_name in pipeline_obj.named_steps:
            feature_scaler_step = pipeline_obj.named_steps[scaler_step_name]
            if actual_verbose:
                print(f"✅ Found feature scaler step: '{scaler_step_name}'")
        
        # Fallback: search through all steps by name or type
        elif hasattr(pipeline_obj, 'steps'):
            for name, step in pipeline_obj.steps:
                if scaler_step_name in name or isinstance(step, (StandardScaler)):
                    feature_scaler_step = step
                    if actual_verbose:
                        print(f"✅ Found feature scaler step: '{name}'")
                    break

        # Create default if not found
        if feature_scaler_step is None:
            if actual_verbose:
                print("⚠️ Warning: Could not find feature scaler step. Creating default StandardScaler...")
            feature_scaler_step = StandardScaler()

        # =================================================================
        # VMAF SCALER EXTRACTION
        # =================================================================
        # Extract the VMAF scaling component for quality score normalization
        vmaf_scaler = None
        vmaf_scaler_step_name = 'vmaf_scaler'
        
        if hasattr(pipeline_obj, 'named_steps') and vmaf_scaler_step_name in pipeline_obj.named_steps:
            vmaf_scaler = pipeline_obj.named_steps[vmaf_scaler_step_name]
            if actual_verbose:
                print(f"✅ Found VMAF scaler step: '{vmaf_scaler_step_name}'")

        # Create default VMAF scaler if not found
        if vmaf_scaler is None:
            if actual_verbose:
                print("⚠️ Warning: Could not find VMAF scaler. Creating default...")
                
            class DefaultVMAFScaler:
                """Default VMAF scaler with typical VMAF range."""
                def __init__(self): 
                    self.min_val, self.max_val = 20.0, 100.0  # Typical VMAF range
                    
            vmaf_scaler = DefaultVMAFScaler()
            if actual_verbose:
                print(f"   📊 Using default VMAF range: {vmaf_scaler.min_val}-{vmaf_scaler.max_val}")

        # =================================================================
        # CQ PARAMETER BOUNDS EXTRACTION
        # =================================================================
        # Extract CQ (Constant Quality) parameter bounds for optimization
        default_cq_min, default_cq_max = 10, 51  # Conservative CQ range
        cq_min, cq_max = default_cq_min, default_cq_max
        cq_scaler_step_name = 'cq_scaler'

        # Try to find CQ scaler component
        if hasattr(pipeline_obj, 'named_steps') and cq_scaler_step_name in pipeline_obj.named_steps:
            cq_scaler = pipeline_obj.named_steps[cq_scaler_step_name]
            
            # Check for CQ bounds in various attribute naming conventions
            if hasattr(cq_scaler, 'min_cq') and hasattr(cq_scaler, 'max_cq'):
                cq_min, cq_max = cq_scaler.min_cq, cq_scaler.max_cq
                if actual_verbose:
                    print(f"✅ Found CQ range in step '{cq_scaler_step_name}': {cq_min}-{cq_max}")
            elif hasattr(cq_scaler, 'min_val') and hasattr(cq_scaler, 'max_val'):
                cq_min, cq_max = cq_scaler.min_val, cq_scaler.max_val
                if actual_verbose:
                    print(f"✅ Found CQ range in scaler attributes: {cq_min}-{cq_max}")

        if actual_verbose:
            print(f"📊 Using CQ optimization range: {cq_min}-{cq_max}")
            print(f"   💡 This range will constrain the binary search for optimal quality parameters")

        return pipeline_obj, feature_scaler_step, vmaf_scaler, int(cq_min), int(cq_max)

    except Exception as e:
        if actual_verbose:
            print(f"❌ ERROR: Failed to load or extract from pipeline '{pipeline_path}': {e}")
            print("🔍 Detailed error information:")
            traceback.print_exc()
        return None, None, None, None, None

def load_encoding_resources(config, logging_enabled=True):
    """

    1. Scene classifier AI model - to identify content type (animation, gaming, etc.)
    2. Preprocessing pipeline - to prepare video frames for the AI model
    3. GPU/CPU device selection - for running the AI inference


    Args:
        config (dict): Configuration containing model file paths
        logging_enabled (bool): Whether to print loading status messages

    Returns:
        tuple: (scene_model, preprocessing_pipeline, device) ready for encoding
    """
    # Check if CLIP is enabled
    from utils.processing_utils import USE_CLIP_CLASSIFICATION

    # Get model file paths from config
    model_paths = config.get('model_paths', {})
    scene_model_path = model_paths.get('scene_classifier_model', "services/compress/models/scene_classifier_model.pth")
    preprocessing_pipeline_path = model_paths.get('preprocessing_pipeline', "services/compress/models/preprocessing_pipeline.pkl")

    # Choose GPU if available, otherwise use CPU
    device = 'cuda' if torch.cuda.is_available() else 'cpu'

    # Skip loading old scene classifier model if CLIP is enabled
    if USE_CLIP_CLASSIFICATION:
        if logging_enabled:
            print(f"   ⚡ CLIP classification enabled - skipping MobileNetV3 model load")
            print(f"   💡 Using CLIP for scene classification (faster, no model file needed)")

        scene_classifier_model = None
        available_metrics = []
        class_mapping = {}
        image_size = 384
        confidence_threshold = 0.5  # Default confidence threshold for CLIP
        model_type = None
    else:
        # Resolve absolute path and validate file exists
        scene_model_path_abs = os.path.abspath(scene_model_path)
        if not os.path.exists(scene_model_path_abs):
            error_msg = f"❌ ERROR: Scene classifier model not found at: {scene_model_path_abs}"
            if logging_enabled:
                print(error_msg)
                # Check if alternative file exists
                alt_path = os.path.abspath("services/compress/models/scene_classifier_model_1.pth")
                if os.path.exists(alt_path):
                    print(f"   💡 Found alternative model at: {alt_path}")
                    print(f"   💡 Consider updating config or renaming file to: scene_classifier_model.pth")
            raise FileNotFoundError(error_msg)

        if logging_enabled:
            print(f"   📂 Loading scene classifier model from: {scene_model_path_abs}")
            file_size_mb = os.path.getsize(scene_model_path_abs) / (1024 * 1024)
            print(f"   📊 Model file size: {file_size_mb:.2f} MB")

        # Load scene classifier AI model
        model_state_dict, available_metrics, class_mapping, image_size, confidence_threshold, model_type = load_scene_classifier_model(scene_model_path_abs, device, logging_enabled)
        print(f"   ✅ Scene classifier model loaded from {scene_model_path_abs} on {device}")
        # Use model_type from the loaded checkpoint (already extracted in load_scene_classifier_model)
        scene_classifier_model = CombinedModel(
            num_classes=len(class_mapping),
            metrics_dim=len(available_metrics),
            model_type=model_type,
            use_pretrained=False  # Don't use pretrained weights when loading from checkpoint
        )
        # Load state dict with strict=False to handle minor architecture differences
        try:
            scene_classifier_model.load_state_dict(model_state_dict, strict=True)
        except RuntimeError as e:
            if logging_enabled:
                print(f"   ⚠️ Warning: Strict loading failed, trying with strict=False...")
            scene_classifier_model.load_state_dict(model_state_dict, strict=False)
            if logging_enabled:
                print(f"   ⚠️ Model loaded with strict=False - some weights may not match")
        scene_classifier_model.to(device)
        scene_classifier_model.eval()
    
    pipeline_obj, feature_scaler_step, vmaf_scaler, cq_min, cq_max = get_scalers_from_pipeline(preprocessing_pipeline_path, verbose=logging_enabled, logging_enabled=logging_enabled)
    print(f"   ✅ Preprocessing pipeline loaded from {preprocessing_pipeline_path}")
    
    return {
        "scene_classifier_model": scene_classifier_model, 
        "available_metrics": available_metrics,           
        "device": device,                                 
        "class_mapping": class_mapping,                   
        "image_size": image_size,  # Add image size to resources
        "confidence_threshold": confidence_threshold,  # Add confidence threshold
        "pipeline_obj": pipeline_obj,                     
        "feature_scaler_step": feature_scaler_step,       
        "vmaf_scaler": vmaf_scaler,                       
        "cq_min": cq_min,                                 
        "cq_max": cq_max                                  
    }

def ai_encoding(scene_metadata, config, resources, target_vmaf=None, target_quality_level=None, logging_enabled=True):
    """
    
    1. Use AI to classify the scene content (animation, gaming, text, etc.)
    2. Look up a pre-determined CQ value from a table based on scene type AND quality tier
    3. Encode the scene once with that CQ value
    
    - High quality tier (VMAF ~93): Lower CQ values for better quality
    - Medium quality tier (VMAF ~89): Balanced CQ values
    - Low quality tier (VMAF ~85): Higher CQ values for smaller files
    
    - Runs multiple encoding attempts with different CQ values
    - Uses AI to predict VMAF quality for each attempt
    - Uses binary search to find the optimal CQ
    
    Args:
        scene_metadata (dict): Contains scene file path, duration, etc.
        config (dict): Configuration settings for encoding
        resources (dict): Pre-loaded AI models and preprocessing tools
        target_vmaf (float): Target quality used to select appropriate quality tier
        target_quality_level (str): Desired quality level ('High', 'Medium', 'Low') used for CQ lookup
        logging_enabled (bool): Whether to print progress messages
        
    Returns:
        tuple: (success_status, scene_data_dict)
            - success_status: True if encoding succeeded, False otherwise
            - scene_data_dict: Contains encoding results, file sizes, CQ used, etc.
    """
    logging_enabled=True
    
    if not scene_metadata:
        return None, {
            'scene_number': 0,
            'encoding_success': False,
            'error_reason': 'Scene metadata is None or empty',
            'processing_time_seconds': 0.0,
            'encoded_path': None,
            'path': None
        }
    
    def safe_float(value, default=0.0):
        """Convert value to float, return default if invalid"""
        if value is None: return default
        try:
            result = float(value)
            return result if not (result != result) else default
        except (TypeError, ValueError):
            return default
    
    def safe_positive_float(value, default=1.0):
        """Convert to float and ensure it's positive"""
        result = safe_float(value, default)
        return max(result, 0.1)
    
    scene_path = scene_metadata.get('path')
    scene_number = int(safe_float(scene_metadata.get('scene_number', 1), 1))
    start_time = safe_float(scene_metadata.get('start_time'), 0.0)
    end_time = safe_float(scene_metadata.get('end_time'), 0.0)
    scene_duration = safe_positive_float(scene_metadata.get('duration'), 1.0)
    
    if end_time <= start_time or scene_duration <= 0:
        if end_time > start_time:
            scene_duration = end_time - start_time
        else:
            try:
                cmd = ['ffprobe', '-v', 'quiet', '-show_entries', 'format=duration', '-of', 'csv=p=0', scene_path]
                result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=10)
                if result.returncode == 0 and result.stdout.strip():
                    scene_duration = safe_positive_float(result.stdout.strip(), 1.0)
                    end_time = start_time + scene_duration
                else:
                    scene_duration = 1.0
            except Exception:
                scene_duration = 1.0

    is_very_short_scene = scene_duration < 1.0
    if is_very_short_scene and logging_enabled:
        print(f"   ⚠️ Very short scene detected ({scene_duration:.1f}s) - using special handling")

    original_video_metadata = scene_metadata.get('original_video_metadata', {})
    
    if logging_enabled:
        print(f"\n🎬 Processing Scene {scene_number}")
        print(f"   📁 File: {os.path.basename(scene_path) if scene_path else 'None'}")
        print(f"   ⏱️ Timing: {start_time:.1f}s - {end_time:.1f}s (duration: {scene_duration:.1f}s)")

    if not scene_path or not os.path.exists(scene_path) or os.path.getsize(scene_path) == 0:
        return None, {
            'scene_number': scene_number,
            'encoding_success': False,
            'error_reason': 'Scene file is missing, empty, or inaccessible',
            'processing_time_seconds': 0.0,
            'encoded_path': None,
            'path': scene_path
        }

    processing_start_time = time.time()
    
    # Get temporary directory for intermediate files
    temp_dir = config.get('directories', {}).get('temp_dir', './videos/temp_scenes')
    
    if not target_quality_level:
        target_quality_level = original_video_metadata.get('target_quality') or config.get('video_processing', {}).get('target_quality')
    target_vmaf = safe_float(target_vmaf or original_video_metadata.get('target_vmaf') or 
                           config.get('video_processing', {}).get('target_vmaf', 0.0), 0.0)

    # Get codec from config (set by the request)
    # Priority: config['video_processing']['target_codec'] > metadata > fallback
    target_codec_from_config = config.get('video_processing', {}).get('target_codec')
    target_codec_from_part1 = original_video_metadata.get('target_codec', 'auto')
    original_codec = original_video_metadata.get('original_codec', 'unknown')
    current_codec = original_video_metadata.get('codec', original_codec)

    # Use target_codec from config (highest priority - comes from the request)
    if target_codec_from_config and target_codec_from_config != 'auto':
        codec = target_codec_from_config
        if logging_enabled:
            print(f"   🎯 Using target codec from request: {codec}")
    # Fallback to Part 1 metadata
    elif target_codec_from_part1 and target_codec_from_part1 != 'auto':
        codec = target_codec_from_part1
        if logging_enabled:
            print(f"   📋 Using target codec from metadata: {codec}")
    # Final fallback to upgrade map
    else:
        codec_upgrade_map = {'h264': 'av1_nvenc', 'hevc': 'av1_nvenc', 'vp9': 'av1_nvenc', 'av1': 'av1_nvenc'}
        codec = codec_upgrade_map.get(current_codec.lower(), 'av1_nvenc')
        if logging_enabled:
            print(f"   ⚡ Using fallback codec mapping: {current_codec} → {codec}")

    # Ensure codec is mapped to actual encoder name (e.g., 'av1' -> 'av1_nvenc')
    # Map standard codec names to actual FFmpeg encoder names
    codec_name_map = {
        'av1': 'av1_nvenc' if torch.cuda.is_available() else 'libsvtav1',
        'hevc': 'hevc_nvenc' if torch.cuda.is_available() else 'libx265',
        'h264': 'h264_nvenc' if torch.cuda.is_available() else 'libx264',
        'vp9': 'libvpx-vp9'
    }
    # If codec is a standard name, map it to the actual encoder
    if codec.lower() in codec_name_map:
        codec = codec_name_map[codec.lower()]
        if logging_enabled:
            print(f"   🔄 Mapped codec name to encoder: {codec}")

    if logging_enabled:
        print(f"   🎥 Final Selected Codec: {codec}")

    # Get codec_mode and target_bitrate from config (set by the request)
    codec_mode = config.get('video_processing', {}).get('codec_mode', 'CRF')
    target_bitrate = config.get('video_processing', {}).get('target_bitrate', 10.0)

    if logging_enabled:
        print(f"   ⚙️ Codec Mode: {codec_mode}, Target Bitrate: {target_bitrate} Mbps")

    # STEP 1: BASIC ANALYSIS - Classify scene and extract video features in one call
    if logging_enabled:
        print(f"   🤖 Running scene classification and feature extraction...")
    
    scene_type = 'default'
    confidence_score = 0.0
    video_features = {}
    detailed_results = {}
    try:
        image_size = resources.get('image_size', 224)  # Get image size from resources, default to 224
        confidence_threshold = resources.get('confidence_threshold', 0.5)  # Get confidence threshold
        
        # Validate image_size
        if not isinstance(image_size, int) or image_size <= 0:
            if logging_enabled:
                print(f"   ⚠️ Warning: Invalid image_size {image_size}, using default 224")
            image_size = 224
        
        if logging_enabled:
            print(f"   📐 Using image_size: {image_size}x{image_size} for scene classification")
        
        classification_result = classify_scene_from_path(
            scene_path=scene_path,
            temp_dir=temp_dir,
            scene_classifier_model=resources['scene_classifier_model'],
            available_metrics=resources['available_metrics'],
            device=resources['device'],
            metrics_scaler=resources['feature_scaler_step'],
            class_mapping=resources['class_mapping'],
            logging_enabled=logging_enabled,
            image_size=image_size,
            confidence_threshold=confidence_threshold
        )
        
        # Handle the tuple return from classify_scene_from_path (now returns 3 items)
        if isinstance(classification_result, tuple) and len(classification_result) == 3:
            scene_type, detailed_results, video_features = classification_result
            confidence_score = detailed_results.get('confidence_score', 0.0)
        elif isinstance(classification_result, tuple) and len(classification_result) == 2:
            # Fallback for older return format
            scene_type, detailed_results = classification_result
            confidence_score = detailed_results.get('confidence_score', 0.0)
            video_features = {}
        elif isinstance(classification_result, dict):
            # Fallback if it returns a dict instead of tuple
            scene_type = classification_result.get('scene_type', 'default')
            confidence_score = classification_result.get('confidence_score', 0.0)
            video_features = {}
        else:
            # Unknown return type, use defaults
            scene_type = 'default'
            confidence_score = 0.0
            video_features = {}

        if logging_enabled:
            print(f"   🎭 Scene classified as: '{scene_type}' (Confidence: {confidence_score:.2f})")
            if video_features:
                print(f"   📊 Video features extracted: {len(video_features)} metrics")

    except Exception as e:
        if logging_enabled:
            print(f"   ❌ Scene classification failed: {e}")
            traceback.print_exc()
    
    # Map the scene type to lookup table key
    original_scene_type = scene_type
    mapped_scene_type = map_scene_type_to_lookup_key(scene_type)

    if logging_enabled and original_scene_type != mapped_scene_type:
        print(f"   🔄 Mapped scene type '{original_scene_type}' -> '{mapped_scene_type}' for CQ lookup")

    # Get quality tier information for logging
    print(f"   🎯 Target quality level: {target_quality_level}")
    # If only quality level provided, derive indicative VMAF for logging purposes
    if target_quality_level and not target_vmaf:
        target_vmaf = get_target_vmaf_from_quality(target_quality_level)
        if logging_enabled:
            print(f"   ℹ️ Indicative VMAF from quality level '{target_quality_level}': {target_vmaf}")

    # ============================================================================
    # NETFLIX PER-TITLE ENCODING SWITCH
    # ============================================================================
    # Check if Netflix per-title encoding should be used
    if should_use_netflix_per_title(config):
        if logging_enabled:
            print(f"   🎬 Using Netflix Per-Title Encoding")

        # Prepare resources for Netflix encoding
        netflix_resources = {
            'temp_dir': temp_dir,
            'encoded_scenes_dir': config.get('directories', {}).get('encoded_scenes_dir', './videos/encoded_scenes')
        }

        # Update scene metadata with classification results
        scene_metadata.update({
            'scene_type': scene_type,
            'confidence_score': confidence_score,
            'video_features': video_features,
            'detailed_results': detailed_results
        })

        # Run Netflix per-title encoding
        result_metadata = netflix_per_title_encoding(
            scene_metadata=scene_metadata,
            config=config,
            resources=netflix_resources,
            target_vmaf=target_vmaf,
            target_quality_level=quality_level_normalized,
            logging_enabled=logging_enabled
        )

        # Extract results
        encoded_path = result_metadata.get('encoded_path')
        encoding_time = result_metadata.get('encoding_time', 0.0)
        final_cq = result_metadata.get('cq_used', 0)
        actual_vmaf = result_metadata.get('actual_vmaf')

        if encoded_path and os.path.exists(encoded_path):
            # Calculate file sizes and compression ratio
            original_size = os.path.getsize(scene_path)
            encoded_size = os.path.getsize(encoded_path)
            compression_ratio = original_size / encoded_size if encoded_size > 0 else 0.0

            processing_time = time.time() - processing_start_time

            if logging_enabled:
                print(f"\n✅ Scene {scene_number} Encoding Complete (Netflix Per-Title)")
                print(f"   📊 VMAF: {actual_vmaf:.2f if actual_vmaf else 'N/A'} (Target: {target_vmaf:.1f})")
                print(f"   🎯 CQ Used: {final_cq}")
                print(f"   📦 Compression: {compression_ratio:.2f}x")
                print(f"   ⏱️ Total Time: {processing_time:.1f}s")

            return True, {
                'scene_number': scene_number,
                'encoding_success': True,
                'encoded_path': encoded_path,
                'path': scene_path,
                'original_size_bytes': original_size,
                'encoded_size_bytes': encoded_size,
                'compression_ratio': compression_ratio,
                'cq_used': final_cq,
                'scene_type': scene_type,
                'confidence_score': confidence_score,
                'actual_vmaf': actual_vmaf,
                'target_vmaf': target_vmaf,
                'encoding_time_seconds': encoding_time,
                'processing_time_seconds': processing_time,
                'encoding_method': 'netflix_per_title',
                'probe_results': result_metadata.get('probe_results', []),
                'codec': codec,
                'codec_mode': codec_mode
            }
        else:
            if logging_enabled:
                print(f"   ❌ Netflix per-title encoding failed, falling back to lookup table")
            # Fall through to lookup table method

    # ============================================================================
    # OPTIMAL BITRATE CONTROLLER (SCENE-AWARE)
    # ============================================================================
    # Check if optimal controller should be used
    from config.optimal_controller_config import (
        should_use_optimal_controller,
        map_scene_type_for_optimal_controller,
        get_vmaf_threshold_from_quality
    )

    use_optimal_controller = should_use_optimal_controller(config)

    if use_optimal_controller:
        if logging_enabled:
            print(f"   🎯 Using OPTIMAL BITRATE CONTROLLER (Scene-Aware)")

        try:
            from utils.optimal_encoder_wrapper import encode_video_optimal

            # Map scene type for optimal controller
            optimal_scene_type = map_scene_type_for_optimal_controller(scene_type, confidence_score)

            # ASSERTION: Verify scene type mapping consistency
            # If classifier says "animation" and confidence is above threshold, controller must use "animation"
            # This catches plumbing bugs where scene type is lost in translation
            from config.optimal_controller_config import MIN_SCENE_CONFIDENCE
            if confidence_score >= MIN_SCENE_CONFIDENCE:
                scene_lower = str(scene_type).lower()
                if 'animation' in scene_lower and optimal_scene_type != 'animation':
                    if logging_enabled:
                        print(f"   ⚠️ WARNING: Scene type mapping inconsistency!")
                        print(f"      Classifier: '{scene_type}' (confidence: {confidence_score:.3f})")
                        print(f"      Mapped to: '{optimal_scene_type}' (expected: 'animation')")
                        print(f"      This indicates a plumbing bug in scene type mapping.")
                elif 'gaming' in scene_lower and optimal_scene_type != 'gaming':
                    if logging_enabled:
                        print(f"   ⚠️ WARNING: Scene type mapping inconsistency!")
                        print(f"      Classifier: '{scene_type}' → Mapped: '{optimal_scene_type}' (expected: 'gaming')")
                elif 'screen' in scene_lower and optimal_scene_type != 'screen':
                    if logging_enabled:
                        print(f"   ⚠️ WARNING: Scene type mapping inconsistency!")
                        print(f"      Classifier: '{scene_type}' → Mapped: '{optimal_scene_type}' (expected: 'screen')")
                elif 'face' in scene_lower and optimal_scene_type != 'faces':
                    if logging_enabled:
                        print(f"   ⚠️ WARNING: Scene type mapping inconsistency!")
                        print(f"      Classifier: '{scene_type}' → Mapped: '{optimal_scene_type}' (expected: 'faces')")

            # Get VMAF threshold
            if not target_vmaf or target_vmaf == 0:
                target_vmaf = get_vmaf_threshold_from_quality(quality_level_normalized if 'quality_level_normalized' in locals() else 'Medium')

            if logging_enabled:
                print(f"   🎭 Optimal controller scene type: {optimal_scene_type}")
                print(f"   🎯 VMAF threshold: {target_vmaf}")
                print(f"   ⚙️ Codec mode: {codec_mode}")

            # Prepare output path
            # BUG FIX #5: Add unique identifier to prevent cross-request contamination
            import uuid
            unique_id = str(uuid.uuid4())[:8]  # Use first 8 chars of UUID for brevity

            if scene_duration < 1.0:
                output_scene_path = os.path.join(
                    temp_dir,
                    f"encoded_scene_{scene_number:03d}_{start_time:.1f}s-{end_time:.1f}s_{codec.lower()}_{unique_id}.mp4"
                )
            else:
                output_scene_path = os.path.join(
                    temp_dir,
                    f"encoded_scene_{scene_number:03d}_{start_time:.0f}s-{end_time:.0f}s_{codec.lower()}_{unique_id}.mp4"
                )
            os.makedirs(temp_dir, exist_ok=True)

            # Encode with optimal controller
            encoded_path, encoding_time = encode_video_optimal(
                input_path=scene_path,
                output_path=output_scene_path,
                codec=codec,
                vmaf_threshold=target_vmaf,
                codec_mode=codec_mode,
                target_bitrate=target_bitrate,
                scene_type=optimal_scene_type,
                contrast_value=0.5,
                duration=scene_duration,
                skip_cq_mapping=True,
                logging_enabled=logging_enabled,
                use_optimal_controller=True
            )

            if encoded_path and os.path.exists(encoded_path):
                # Success! Calculate metrics
                original_size = os.path.getsize(scene_path)
                encoded_size = os.path.getsize(encoded_path)
                compression_ratio = original_size / encoded_size if encoded_size > 0 else 0.0
                processing_time = time.time() - processing_start_time

                if logging_enabled:
                    print(f"\n✅ Scene {scene_number} Encoding Complete (Optimal Controller)")
                    print(f"   📦 Compression: {compression_ratio:.2f}x")
                    print(f"   ⏱️ Total Time: {processing_time:.1f}s")

                # Return success with optimal controller results
                # IMPORTANT: Return (encoded_path, dict) not (True, dict) to match expected format
                return encoded_path, {
                    'scene_number': scene_number,
                    'encoding_success': True,
                    'encoded_path': encoded_path,
                    'path': scene_path,
                    'original_size_bytes': original_size,
                    'encoded_size_bytes': encoded_size,
                    'compression_ratio': compression_ratio,
                    'scene_type': scene_type,
                    'optimal_scene_type': optimal_scene_type,
                    'confidence_score': confidence_score,
                    'target_vmaf': target_vmaf,
                    'encoding_time_seconds': encoding_time,
                    'processing_time_seconds': processing_time,
                    'encoding_method': 'optimal_controller',
                    'codec': codec,
                    'codec_mode': codec_mode,
                    'model_training_data': {
                        'raw_video_features': video_features,
                        'scene_classifier_probabilities': detailed_results,
                        'processing_timings': {
                            'total_processing_time': processing_time,
                            'encoding_time': encoding_time
                        }
                    }
                }
            else:
                if logging_enabled:
                    print(f"   ⚠️ Optimal controller encoding failed, falling back to lookup table")
                # Fall through to lookup table method

        except Exception as e:
            if logging_enabled:
                print(f"   ❌ Optimal controller error: {e}")
                traceback.print_exc()
                print(f"   🔄 Falling back to lookup table method")
            # Fall through to lookup table method

    # ============================================================================
    # LOOKUP TABLE ENCODING (DEFAULT/FALLBACK)
    # ============================================================================

    if logging_enabled and use_optimal_controller:
        print(f"   📋 Using lookup table method (fallback)")

    # Get CQ from lookup table using mapped scene type, target quality/VMAF, and codec
    # Use codec-specific CQ values from advanced_encoding_config to avoid double-mapping
    from config.advanced_encoding_config import get_cq_value

    # Map quality level to config format
    quality_level_map = {'high': 'High', 'medium': 'Medium', 'low': 'Low'}
    quality_level_normalized = quality_level_map.get(str(target_quality_level).lower(), target_quality_level) if target_quality_level else 'Medium'

    # Get codec-specific CQ value with granular override support
    # Extract input bitrate from metadata if available
    input_bitrate_kbps = original_video_metadata.get('bitrate', 0)
    input_bitrate_mbps = input_bitrate_kbps / 1000.0 if input_bitrate_kbps else target_bitrate

    base_cq = get_cq_value(
        codec=codec,
        quality_level=quality_level_normalized,
        scene_type=mapped_scene_type,
        input_bitrate_mbps=input_bitrate_mbps
    )
    
    # Log quality tier and CQ selection
    if logging_enabled:
        # Determine label for logging
        if target_quality_level:
            tier_label = str(target_quality_level).upper()
        else:
            if target_vmaf >= 93:
                tier_label = "HIGH"
            elif target_vmaf >= 88:
                tier_label = "MEDIUM"
            else:
                tier_label = "LOW"

        print(f"   🎯 Using quality tier: {tier_label} (Indicative VMAF: {target_vmaf if target_vmaf else 'n/a'})")

        # Check if granular override was used
        try:
            from config.granular_cq_overrides import has_granular_override, get_override_key
            if has_granular_override(mapped_scene_type, codec, codec_mode, input_bitrate_mbps, target_vmaf):
                override_key = get_override_key(mapped_scene_type, codec, codec_mode, input_bitrate_mbps, target_vmaf)
                print(f"   ⭐ Using GRANULAR OVERRIDE: {override_key} → CQ={base_cq}")
            else:
                print(f"   🎚️ Base CQ from lookup table for '{mapped_scene_type}' at {tier_label} quality: {base_cq}")
        except ImportError:
            print(f"   🎚️ Base CQ from lookup table for '{mapped_scene_type}' at {tier_label} quality: {base_cq}")
    
    # Apply conservative adjustment from config
    conservative_cq_adjustment = safe_float(config.get('video_processing', {}).get('conservative_cq_adjustment', 2), 2)
    final_cq = min(base_cq + conservative_cq_adjustment, 51.0)
    if logging_enabled:
        print(f"   🔧 Applied conservative adjustment: +{conservative_cq_adjustment} -> Final CQ: {final_cq}")

    # Create a placeholder scene_data object
    scene_data = {
        'path': scene_path,
        'scene_number': scene_number,
        'start_time': start_time,
        'end_time': end_time,
        'duration': scene_duration,
        'original_video_metadata': original_video_metadata,
        'scene_type': original_scene_type,  # Keep original scene type from classifier
        'mapped_scene_type': mapped_scene_type,  # Add mapped scene type for CQ lookup
        'confidence_score': confidence_score,
    'optimal_cq': base_cq,
        'adjusted_cq': final_cq,
        'final_adjusted_cq': final_cq,
        'codec_selection_process': {'final_selected_codec': codec},
    'model_training_data': {}, # Placeholder
        'target_quality_level': target_quality_level,
    'base_cq_for_quality': base_cq,
    }

    # BUG FIX #5: Add unique identifier to prevent cross-request contamination
    import uuid
    unique_id = str(uuid.uuid4())[:8]  # Use first 8 chars of UUID for brevity

    if scene_duration < 1.0:
        output_scene_path = os.path.join(
            temp_dir,
            f"encoded_scene_{scene_number:03d}_{start_time:.1f}s-{end_time:.1f}s_{codec.lower()}_{unique_id}.mp4"
        )
    else:
        output_scene_path = os.path.join(
            temp_dir,
            f"encoded_scene_{scene_number:03d}_{start_time:.0f}s-{end_time:.0f}s_{codec.lower()}_{unique_id}.mp4"
        )
    os.makedirs(temp_dir, exist_ok=True)

    size_increase_protection = config.get('video_processing', {}).get('size_increase_protection', True)
    max_encoding_retries = int(safe_float(config.get('video_processing', {}).get('max_encoding_retries', 2), 2))
    
    encoding_start_time = time.time()
    encoded_path = None
    encoding_time = 0

    if size_increase_protection:
        if logging_enabled:
            print(f"   🛡️ Size increase protection enabled")
        try:
            encoded_path, encoding_time = encode_scene_with_size_check(
                scene_path=scene_path,
                output_path=output_scene_path,
                codec=codec,
                adjusted_cq=final_cq,
                content_type=scene_type,
                contrast_value=0.5,
                codec_mode=codec_mode,
                target_bitrate=target_bitrate,
                duration=scene_duration,  # Pass scene duration for duration-based preset selection
                max_retries=max_encoding_retries,
                skip_cq_mapping=True,  # CQ is already codec-specific from advanced_encoding_config
                logging_enabled=logging_enabled
            )
        except Exception as e:
            if logging_enabled:
                print(f"   ❌ Size-protected encoding failed: {e}")
    else:
        if logging_enabled:
            print(f"   ⚡ Standard encoding (size protection disabled)")
        try:
            _, encoding_time = encode_video(
                input_path=scene_path,
                output_path=output_scene_path,
                codec=codec,
                rate=final_cq,
                scene_type=scene_type,
                contrast_value=0.5,  # Default contrast
                codec_mode=codec_mode,
                target_bitrate=target_bitrate,
                duration=scene_duration,  # Pass scene duration for duration-based preset selection
                skip_cq_mapping=True,  # CQ is already codec-specific from advanced_encoding_config
                logging_enabled=logging_enabled
            )
            encoded_path = output_scene_path
        except Exception as e:
            if logging_enabled:
                print(f"   ❌ Standard encoding failed: {e}")

    # Final update of scene_data
    encoding_success = bool(encoded_path and os.path.exists(encoded_path) and os.path.getsize(encoded_path) > 0)
    scene_data['encoding_success'] = encoding_success
    scene_data['encoded_path'] = encoded_path if encoding_success else None
    scene_data['encoding_time'] = safe_float(encoding_time, 0)
    scene_data['processing_time_seconds'] = time.time() - processing_start_time
    
    # Add file size information and codec details
    if encoding_success:
        # Calculate file sizes in MB
        input_file_size = os.path.getsize(scene_path) if os.path.exists(scene_path) else 0
        output_file_size = os.path.getsize(encoded_path) if os.path.exists(encoded_path) else 0
        
        scene_data['input_size_mb'] = input_file_size / (1024 * 1024)
        scene_data['encoded_file_size_mb'] = output_file_size / (1024 * 1024)
        
        # Calculate compression ratio
        if input_file_size > 0:
            compression_ratio = ((output_file_size - input_file_size) / input_file_size) * 100
            scene_data['compression_ratio'] = compression_ratio
        else:
            scene_data['compression_ratio'] = 0
        
        # Store codec information for filename generation
        scene_data['codec_used'] = codec
    else:
        scene_data['input_size_mb'] = 0
        scene_data['encoded_file_size_mb'] = 0
        scene_data['compression_ratio'] = 0
        scene_data['codec_used'] = 'unknown'


    scene_data['model_training_data'] = {
        'raw_video_features': video_features,
        'processed_video_features': {},  
        'vmaf_model_features': {},       
        'scene_classifier_features': video_features,
        'scene_classifier_probabilities': detailed_results,
        'processing_timings': {
            'total_processing_time': time.time() - processing_start_time,
            'encoding_time': safe_float(encoding_time, 0) if 'encoding_time' in locals() else 0
        }
    }

    if encoding_success:
        if logging_enabled:
            print(f"   ✅ Scene {scene_number} encoded successfully.")
        return encoded_path, scene_data
    else:
        if logging_enabled:
            print(f"   ❌ Encoding failed for scene {scene_number}.")
        scene_data['error_reason'] = 'Encoding process failed or produced an empty file'
        return None, scene_data

def map_scene_type_to_lookup_key(scene_type):
    """
    Convert AI scene classifier output to CQ lookup table keys.
    
    The AI scene classifier returns descriptive names like:
    - 'Screen Content / Text' 
    - 'Animation / Cartoon / Rendered Graphics'
    - 'Faces / People'
    - 'Gaming Content'
    - 'other'
    - 'unclear'
    
    But our CQ lookup table uses simpler keys:
    - 'animation' (for cartoons/rendered content)
    - 'low-action' (for text/faces - less motion)
    - 'medium-action' (for general content)
    - 'high-action' (for gaming/sports - lots of motion)
    - 'default' (fallback for unclear content)
    
    Args:
        scene_type (str): Output from AI scene classifier
        
    Returns:
        str: Corresponding lookup table key
    """
    scene_lower = scene_type.lower() if scene_type else 'default'
    
    scene_mapping = {
        'screen content / text': 'low-action',        # Text doesn't need high quality
        'animation / cartoon / rendered graphics': 'animation',  # Cartoons compress well
        'faces / people': 'low-action',               # Faces need clarity but less motion
        'gaming content': 'high-action',              # Games have lots of motion/detail
        'other': 'medium-action',                     # General content gets medium quality
        'unclear': 'default',                        # When unsure, use safe default
        'default': 'default'
    }
    
    if scene_lower in scene_mapping:
        return scene_mapping[scene_lower]
    
    for key, value in scene_mapping.items():
        if key in scene_lower or scene_lower in key:
            return value
    
    return 'default'

def get_target_vmaf_from_quality(quality_level):
    """
    Map quality level to target VMAF score for Basic AI encoding.
    

    Quality Level Mappings:
    - High: 93 VMAF (Maximum quality preservation)
    - Medium: 89 VMAF (Balanced quality and file size)
    - Low: 85 VMAF (Aggressive compression for smaller files)
    
    Args:
        quality_level (str): Target quality level ('High', 'Medium', 'Low')
    
    Returns:
        float: Target VMAF score for the specified quality level
    """
    quality_vmaf_map = {
        'High': 93.0,
        'Medium': 89.0,
        'Low': 85.0
    }
    
    return quality_vmaf_map.get(quality_level, 90.0)


