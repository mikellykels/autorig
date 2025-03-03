# Modular Auto-Rig System - Development Notes

## System Architecture

The Modular Auto-Rig System follows an object-oriented architecture designed for extensibility and reusability. This document outlines the technical details of the implementation and provides guidance for extending the system.

## Core Components

### Class Hierarchy

```
BaseModule (Abstract)
├── SpineModule
└── LimbModule
```

### ModuleManager

The `ModuleManager` class serves as the central coordinator for the auto-rigging system:

- Maintains references to all modules
- Creates the main rig structure (guides, joints, controls groups)
- Handles module registration
- Manages guide creation and rig building
- Provides save/load functionality for guide positions

## System Workflow

1. **Initialization**: Creates the main rig groups
2. **Module Registration**: Modules are created and registered with the manager
3. **Guide Creation**: Guides are placed to define the character's structure
4. **Rig Building**: Joints, controls, and constraints are created based on guide positions

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
    def set_guide_positions(self, positions)
```

All modules must implement at least the `create_guides()` and `build()` methods.

### SpineModule

Located in `autorig/modules/spine.py`, this module implements a flexible spine system:

- Creates a chain of joints from root to chest
- Sets up a hierarchical control system
- Implements weighted constraints for natural spine movement

Implementation details:
- `_create_spine_joints()`: Creates the joint chain
- `_create_spine_controls()`: Creates control curves
- `_setup_spine_constraints()`: Sets up parent and aim constraints

### LimbModule

Located in `autorig/modules/limb.py`, this module implements arm and leg systems:

- Creates IK and FK joint chains
- Sets up IK/FK blending system
- Implements specialized controls for arms and legs

Implementation details:
- `_create_ik_chain()`: Creates the IK system
- `_create_fk_chain()`: Creates the FK system
- `_setup_ikfk_blending()`: Sets up the blend between IK and FK
- Specialized methods for arms vs legs

## Utility Functions

Located in `autorig/core/utils.py`, these functions provide common operations:

- `create_control()`: Creates control curves with various shapes
- `create_guide()`: Creates guide locators
- `create_joint()`: Creates joints in the correct hierarchy
- `set_color_override()`: Sets RGB color overrides

## UI Implementation

Located in `autorig/ui/main_ui.py`, the UI is implemented using PySide2:

- `ModularRigUI`: Main dialog class
- `show_ui()`: Function to display the UI

The UI uses Qt's signals and slots to connect user actions to the rigging system.

## Extending the System

### Adding a New Module Type

To add a new module type (e.g., a neck module):

1. Create a new class that extends `BaseModule`
2. Implement the required abstract methods
3. Add the module to the UI

Example skeleton for a new module:

```python
from autorig.core.module_base import BaseModule
from autorig.core.utils import create_guide, create_joint, create_control, CONTROL_COLORS

class NeckModule(BaseModule):
    def __init__(self, side="c", module_name="neck", num_joints=3):
        super().__init__(side, module_name, "neck")
        self.num_joints = num_joints
    
    def create_guides(self):
        self._create_module_groups()
        # Create guides for neck
        
    def build(self):
        # Create neck joints
        # Create neck controls
        # Set up neck constraints
```

### Modifying Joint Orientations

To implement consistent joint orientations:

1. Modify the `create_joint()` function in `utils.py`
2. Add a post-processing step in each module's build method
3. Consider implementing a utility function for standardizing orientations

### Adding Space Switching

Space switching could be implemented by:

1. Extending the control creation to add space switch attributes
2. Creating parent constraints with multiple targets
3. Connecting constraint weights to the attributes

### Implementing Stretchy IK

Stretchy IK could be added to the limb module:

1. Measure the distance between IK root and end joints
2. Create utility nodes to calculate stretch factors
3. Connect stretch values to joint scale attributes

## Performance Considerations

- **Guide Creation**: Fast, minimal overhead
- **Rig Building**: More intensive, can take several seconds
- **Heavy Operations**: Creating constraints and connecting attributes
- **Memory Usage**: Minimal, primarily Maya scene objects

## Future Development

Areas for improvement and expansion:

1. **Enhanced Joint Orientation Control**
2. **Automated Module Connections**
3. **Finger/Toe Systems**
4. **Advanced Space Switching**
5. **Stretchy IK Systems**
6. **Ribbon Spine Option**
7. **Mirror Functionality**
8. **Control Shape Library**
9. **Export/Bind Skeleton Support**
10. **Twist Joint Systems**

## Code Style and Best Practices

This project follows these Python coding standards:

- **Naming**: CamelCase for classes, snake_case for functions and variables
- **Documentation**: Docstrings for all classes and functions
- **Error Handling**: Appropriate checks and error messages
- **UI Design**: Clean, modular UI code separated from core functionality