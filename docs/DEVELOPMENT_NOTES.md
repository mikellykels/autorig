# Modular Rig System - Development Notes

## System Architecture

The Modular Rig System follows an object-oriented architecture designed for extensibility and reusability. This document outlines the technical details of the implementation and provides guidance for extending the system.

## Core Components

### Class Hierarchy

```
BaseModule (Abstract)
├── SpineModule
├── LimbModule
├── NeckModule
└── HeadModule
```

### ModuleManager

The `ModuleManager` class serves as the central coordinator for the auto-rigging system:

- Maintains references to all modules
- Creates the main rig structure (guides, joints, controls groups)
- Handles module registration
- Manages guide creation and rig building
- Provides save/load functionality for guide positions
- Manages module mirroring functionality
- Coordinates connection between modules

## System Workflow

1. **Initialization**: Creates the main rig groups
2. **Module Registration**: Modules are created and registered with the manager
3. **Guide Creation**: Guides are placed to define the character's structure
4. **Module Mirroring**: (Optional) Left side modules are mirrored to the right
5. **Rig Building**: Joints, controls, and constraints are created based on guide positions
6. **Root Joint Creation**: A root joint is created and hierarchy is finalized

## Module Implementation Details

### BaseModule (Abstract Class)

Located in `autorig/core/module_base.py`, this abstract base class defines the interface and common functionality for all rig modules:

```python
class BaseModule(ABC):
    def __init__(self, side, module_name, module_type)
    def set_manager(self, manager)
    def _create_module_groups()
    @abstractmethod
    def create_guides()
    @abstractmethod
    def build()
    def get_guide_positions()
    def set_guide_positions(positions)
    def validate_guides()
    def debug_log(message)
```

All modules must implement at least the `create_guides()` and `build()` methods.

### SpineModule

Located in `autorig/modules/spine.py`, this module implements a flexible spine system:

- Creates a chain of joints from root to chest
- Sets up a hierarchical control system
- Implements weighted constraints for natural spine movement

Implementation details:
- `_create_spine_joints_with_orientation()`: Creates the joint chain with proper orientation
- `_create_controls()`: Creates control curves
- `_setup_constraints()`: Sets up parent constraints

### LimbModule

Located in `autorig/modules/limb.py`, this module implements arm and leg systems:

- Creates IK and FK joint chains
- Sets up IK/FK blending system
- Implements specialized controls for arms and legs
- Creates pole vector visualization lines
- Implements side-specific coloring system

Implementation details:
- `_create_joints_with_orientation()`: Creates properly oriented joint chains
- `_create_ik_chain()`: Creates the IK system
- `_create_fk_chain()`: Creates the FK system
- `_create_arm/leg_controls()`: Creates the control curves
- `_setup_ikfk_blending()`: Sets up the blend between IK and FK
- `create_pole_vector_visualization()`: Creates and connects pole vector lines
- `_get_color_for_control_type()`: Returns color based on side and control type

### NeckModule

Located in `autorig/modules/neck.py`, this module implements a neck system:

- Creates a chain of joints from neck base to top
- Sets up a hierarchical control system
- Implements improved orientation for consistent neck movement

Implementation details:
- `_create_joints_with_orientation()`: Creates the joint chain with proper orientation
- `_create_controls()`: Creates neck controls
- `_setup_constraints()`: Sets up weighted constraints for smooth blending

### HeadModule

Located in `autorig/modules/head.py`, this module implements a head system:

- Creates head joints connected to neck
- Sets up head control
- Handles orientation consistency with neck

Implementation details:
- `_create_joints_with_orientation()`: Creates head joints with proper orientation
- `_create_controls()`: Creates head control
- `_connect_to_neck()`: Handles connection to neck module

## Utility Functions

### Core Utils

Located in `autorig/core/utils.py`, these functions provide common operations:

- `create_control()`: Creates control curves with various shapes
- `create_guide()`: Creates guide locators
- `create_joint()`: Creates joints in the correct hierarchy
- `set_color_override()`: Sets RGB color overrides
- `create_pole_vector_line()`: Creates visualization lines for pole vectors

### Joint Utils

Located in `autorig/core/joint_utils.py`, these functions provide joint-specific operations:

- `create_oriented_joint_chain()`: Creates joints with proper orientation
- `fix_joint_orientations()`: Fixes existing joint orientations
- `calculate_aim_up_vectors()`: Calculates vectors for joint orientation
- `is_planar_chain()`: Checks if a chain of joints is planar
- `make_planar()`: Adjusts joint positions to form a planar chain

### Vector Utils

Located in `autorig/core/vector_utils.py`, these functions provide vector math operations:

- `vector_from_two_points()`: Creates a vector between two points
- `vector_length()`: Calculates vector magnitude
- `normalize_vector()`: Creates a unit vector
- `dot_product()`: Calculates dot product between vectors
- `cross_product()`: Calculates cross product between vectors
- `project_vector_onto_plane()`: Projects vectors onto a plane
- `create_rotation_matrix()`: Creates a rotation matrix from aim and up vectors

## UI Implementation

Located in `autorig/ui/main_ui.py`, the UI is implemented using PySide2:

- `ModularRigUI`: Main dialog class
- `show_ui()`: Function to display the UI

The UI uses Qt's signals and slots to connect user actions to the rigging system. It provides visual feedback and input for the rigging process.

## Advanced Features

### Module Mirroring

The system provides functionality to mirror left side modules to right side:

- `mirror_modules()`: Creates corresponding right side modules
- `_mirror_joints_only()`: Mirrors joint structure
- `_mirror_fk_ik_joints()`: Mirrors FK and IK chains
- `_setup_mirrored_constraints()`: Sets up constraints for mirrored modules
- `_create_mirrored_arm/leg_controls()`: Creates mirrored controls with proper orientation

### Pole Vector Visualization

The system creates visual lines showing pole vector influence:

- `create_pole_vector_visualization()`: Creates curve between joint and pole vector
- Automatically connects to IK/FK switching for visibility
- Uses the same color scheme as the controls

### Color Coding System

The system uses a color coding scheme for visual clarity:

- Center controls: Yellow
- Left side controls: Blue (Z-axis blue)
- Right side controls: Red
- IK/FK Switches: Yellow

## Extending the System

### Adding a New Module Type

To add a new module type (e.g., a finger module):

1. Create a new class that extends `BaseModule`
2. Implement the required abstract methods
3. Add the module to the UI

Example skeleton for a new module:

```python
from autorig.core.module_base import BaseModule
from autorig.core.utils import create_guide, create_joint, create_control, CONTROL_COLORS

class FingerModule(BaseModule):
    def __init__(self, side="c", module_name="finger", num_joints=4):
        super().__init__(side, module_name, "finger")
        self.num_joints = num_joints
    
    def create_guides(self):
        self._create_module_groups()
        # Create guides for finger
        
    def build(self):
        # Create finger joints
        # Create finger controls
        # Set up finger constraints
```

## Future Development

The following features are planned for future implementation:

### FK/IK Matching

Implementation plan:
1. Add new methods to `LimbModule`:
   - `match_fk_to_ik()`: Match FK controls to current IK pose
   - `match_ik_to_fk()`: Match IK controls to current FK pose
2. Update UI to add FK/IK match buttons
3. Implement position and rotation calculations for accurate matching

Technical considerations:
- Need to compute proper orientation differences between control spaces
- Must handle pole vector position calculation
- Maintain consistent joint stretching during matching

### Space Switching

Implementation plan:
1. Create a new utility function for space switch setup:
   - `create_space_switch()`: Add multiple spaces to a control
2. Add space switch attributes to controls
3. Create additional parent constraints for each space

Technical considerations:
- Need to handle constraint blending between spaces
- Maintain animation data when switching spaces
- Create intuitive UI for space switching

### Stretchy IK Systems

Implementation plan:
1. Add stretch functionality to `_create_ik_chain()` method:
   - Measure chain length
   - Create distance node between root and tip
   - Connect to joint scaling
2. Add stretch toggle attribute to IK controls
3. Create utility nodes for stretch calculations

Technical considerations:
- Need to maintain volume during stretching
- Allow for stretch limits and non-uniform stretching
- Handle IK/FK blending with stretchy chains

### Custom Control Colors

Implementation plan:
1. Expand the `_get_color_for_control_type()` method
2. Add color selection UI to the main interface
3. Create a color preset system

Technical considerations:
- Store color preferences in the rig
- Allow for hierarchical color schemes
- Handle color updates on existing rigs

### Control Shape Library

Implementation plan:
1. Expand the `create_control()` function with more shapes
2. Create a shape browser UI
3. Enable per-module shape customization

Technical considerations:
- Maintain consistent scale and orientation across shapes
- Create visually distinctive shapes for different control types
- Optimize curve density for performance

### Control Shape Swapping

Implementation plan:
1. Create a new utility function:
   - `swap_control_shape()`: Replace curves while preserving connections
2. Add shape swapping UI to the main interface
3. Implement undo/redo functionality for shape changes

Technical considerations:
- Preserve all constraints and connections
- Maintain control pivots and transformations
- Handle multi-shape controls

## Code Style and Best Practices

This project follows these Python coding standards:

- **Naming**: CamelCase for classes, snake_case for functions and variables
- **Documentation**: Docstrings for all classes and functions
- **Error Handling**: Appropriate checks and error messages
- **UI Design**: Clean, modular UI code separated from core functionality
- **Debugging**: Verbose logging with optional debug flags
- **Performance**: Optimization of heavy operations and memory usage