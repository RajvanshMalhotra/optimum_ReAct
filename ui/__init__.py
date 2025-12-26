# from .console import (
#     console,
#     print_intro,
#     print_result,
#     print_success,
#     print_warning,
#     print_error,
#     print_info,
#     print_dim,
#     get_input
# )

# __all__ = [
#     'console',
#     'print_intro',
#     'print_result',
#     'print_success',
#     'print_warning',
#     'print_error',
#     'print_info',
#     'print_dim',
#     'get_input'
# ]

"""UI package for agent interface and visualization."""

# Console UI components
from .console import (
    console,
    print_intro,
    print_result,
    print_success,
    print_warning,
    print_error,
    print_info,
    print_dim,
    get_input
)

# Memory visualization
try:
    from .visualize import MemoryVisualizer
    VISUALIZER_AVAILABLE = True
except ImportError:
    # Visualization dependencies not installed
    VISUALIZER_AVAILABLE = False
    MemoryVisualizer = None

__all__ = [
    # Console functions
    'console',
    'print_intro',
    'print_result',
    'print_success',
    'print_warning',
    'print_error',
    'print_info',
    'print_dim',
    'get_input',
    
    # Visualization
    'MemoryVisualizer',
    'VISUALIZER_AVAILABLE'
]

__version__ = '1.0.0'