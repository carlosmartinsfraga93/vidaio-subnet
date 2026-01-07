"""
Configuration package for video compression services.
"""

# Make config modules importable
from . import advanced_encoding_config
from . import optimal_controller_config

__all__ = ['advanced_encoding_config', 'optimal_controller_config']

