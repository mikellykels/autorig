# Modular Auto-Rig System

[WIP] A modular character rigging system for Maya that streamlines the rigging process through reusable components and a guide-based workflow.

## Features

- **Modular Design**: Create character rigs from reusable spine and limb components
- **Guide-Based Workflow**: Position guides on your model and the system builds the rig automatically
- **IK/FK Switching**: Seamless blending between IK and FK for all limbs
- **Intuitive UI**: User-friendly interface for rig creation and customization
- **Extensible Architecture**: Built for easy addition of new component types

## Overview

This repository contains the codebase for a Maya auto-rigging tool that I developed as part of my technical rigging portfolio. The tool demonstrates:

- Python programming for Maya rigging automation
- Object-oriented design for modular rig components
- UI development using PySide2/Qt
- Practical application of rigging concepts (IK/FK, modular rigging, guide-based workflow)

## Project Structure

```
autorig/
├── core/           # Core functionality
│   ├── utils.py    # Utility functions
│   ├── module_base.py # Base module class
│   └── manager.py  # Module manager
├── modules/        # Module implementations
│   ├── spine.py    # Spine module
│   └── limb.py     # Limb module (arms & legs)
└── ui/             # User interface
    └── main_ui.py  # UI implementation
```

## Documentation

- [User Guide](docs/USER_GUIDE.md) - Detailed instructions for using the system

## Development Process

This tool was developed over a 3-week period as a demonstration of rigging automation principles. The development phases included:

1. Core architecture design
2. Implementation of base module system
3. Development of specialized rig modules (spine, limbs)
4. UI development
5. Testing and refinement

## Technical Highlights

- **Modular Architecture**: Each rig component is a self-contained module
- **Guide-Based System**: Uses guide objects for intuitive rig placement
- **IK/FK Blending**: Seamless switching between animation techniques
- **UI Integration**: Clean UI implementation using PySide2/Qt

## Roadmap

This is a demonstration project, but future developments could include:

- Additional module types (fingers, facial controls)
- Enhanced joint orientation system
- Stretchy IK systems
- Space switching capabilities
- Control shape library expansion

## About Me

This tool was created by Mikaela Carino as part of a technical rigging portfolio. For more information about my work, visit [my portfolio website](https://mikaelacarino.com).