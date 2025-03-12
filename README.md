# Modular Rig System

A modular character rigging system for Maya that streamlines the rigging process through reusable components and a guide-based workflow.

## Features

- **Modular Design**: Create character rigs from reusable spine, limb, neck, and head components
- **Guide-Based Workflow**: Position guides on your model and the system builds the rig automatically
- **IK/FK Switching**: Seamless blending between IK and FK for all limbs
- **Module Mirroring**: Easily mirror left side components to the right side
- **Visual Feedback**: Automatic pole vector visualization lines for IK systems
- **Color-Coding**: Intuitive color system (yellow for center, blue for left, red for right)
- **Intuitive UI**: User-friendly interface for rig creation and customization
- **Extensible Architecture**: Built for easy addition of new component types

## Overview

This repository contains the codebase for a Maya modular rigging tool that demonstrates:

- Python programming for Maya rigging automation
- Object-oriented design for modular rig components
- UI development using PySide2/Qt
- Practical application of rigging concepts (IK/FK, modular rigging, guide-based workflow)

## Project Structure

```
autorig/
├── core/           # Core functionality
│   ├── utils.py    # Utility functions
│   ├── joint_utils.py # Joint orientation utilities
│   ├── vector_utils.py # Vector math operations
│   ├── module_base.py # Base module class
│   └── manager.py  # Module manager
├── modules/        # Module implementations
│   ├── spine.py    # Spine module
│   ├── limb.py     # Limb module (arms & legs)
│   ├── neck.py     # Neck module 
│   └── head.py     # Head module
└── ui/             # User interface
    └── main_ui.py  # UI implementation
```

## Documentation

- [User Guide](docs/USER_GUIDE.md) - Detailed instructions for using the system
- [Development Notes](docs/DEVELOPMENT_NOTES.md) - Technical details for extending the system

## In Development

The following features are planned for future development:

- **FK/IK Matching**: Seamlessly switch between FK and IK without animation loss
- **Space Switching**: Add multiple parent spaces for controls
- **Stretchy IK Systems**: Create elasticity for limbs and spine
- **Custom Control Colors**: User-defined color schemes for controls
- **Control Shape Library**: Additional control shapes for varied aesthetics
- **Control Shape Swapping**: Change control shapes while preserving constraints and connections

## About Me

This tool was created by Mikaela Carino as part of a technical rigging portfolio. For more information about my work, visit [my portfolio website](https://mikaelacarino.com).