# Modular Auto-Rig System User Guide

## Table of Contents
1. [Overview](#overview)
2. [Quick Start Guide](#quick-start-guide)
3. [Detailed Usage Instructions](#detailed-usage-instructions)
   - [Setting Up a Character Rig](#setting-up-a-character-rig)
   - [Using the Generated Rig](#using-the-generated-rig)
4. [Module Types](#module-types)
   - [Spine Module](#spine-module)
   - [Limb Module (Arms)](#limb-module-arms)
   - [Limb Module (Legs)](#limb-module-legs)
5. [Customization](#customization)
6. [Troubleshooting](#troubleshooting)

## Overview

The Modular Auto-Rig System allows you to quickly build character rigs by combining reusable components. The system uses guide objects that you position on your character, and then automatically generates a complete animation rig with controls.

## Quick Start Guide

1. **Launch the tool** using the shelf button with this code:
   ```python
   import importlib; importlib.reload(sys.modules.get('startup')); import startup
   ```
2. **Initialize a rig**: Enter a character name and click "Initialize Rig"
3. **Add modules**: Add a spine and limbs as needed
4. **Create guides**: Click "Create All Guides" and position the orange locators on your character
5. **Build the rig**: Click "BUILD RIG" to generate the full rig with controls

## Detailed Usage Instructions

### Setting Up a Character Rig

#### 1. Initialize the Rig
- Enter a name for your character
- Click "Initialize Rig" to create the base structure
- This creates the main groups that will organize your rig

#### 2. Adding Modules
- Select module type (Spine, Arm, Leg)
- Choose side (Center, Left, Right)
- Configure module settings:
  - For Spine: Set number of joints (3-10)
  - For Limbs: Select type (Arm or Leg)
- Click "Add Module"
- Added modules will appear in the module list

#### 3. Working with Guides
- Click "Create All Guides" to generate orange guide locators
- Move the guides to match your character's skeleton:
  - For spine: Position root, hip, spine segments, and chest
  - For arms: Position shoulder, elbow, wrist, hand, and pole vector
  - For legs: Position hip, knee, ankle, foot, toe, heel, and pole vector
- **Tip**: The pole vector guide determines how the elbow/knee will bend
- Use "Save Guide Positions" to store guide placement for later use
- Use "Load Guide Positions" to recall stored guide positions

#### 4. Building the Rig
- After positioning all guides, click "BUILD RIG"
- The system will generate:
  - A joint hierarchy
  - Control curves
  - IK/FK systems for limbs
  - Connections between components

### Using the Generated Rig

#### Spine Controls
- **Root Control (Yellow cube)**: Controls the entire character
- **Hip Control (Yellow cube)**: Controls the hip region
- **Chest Control (Yellow cube)**: Controls the upper spine and chest

#### Limb Controls (Arms & Legs)
- **FK Mode**: Use the chain of circular controls (green)
- **IK Mode**: Use the cube control at the end of the chain and the square pole vector control (purple)
- **Switch between IK/FK**: Use the "ikFkBlend" attribute on the IK control
  - 0 = IK mode
  - 1 = FK mode
  - Values between 0-1 blend between both systems

#### Leg Controls (Additional Features)
- **Foot Control Attributes**:
  - `roll`: Controls foot roll (heel to toe)
  - `toe`: Controls toe bend
  - `tilt`: Controls foot tilt (side to side)
  - `heel`: Controls heel lift

## Module Types

### Spine Module
The spine module creates a flexible spine system with:
- Base/root control
- Hip control
- Multiple spine segments
- Chest control

Settings:
- **Number of Joints**: Controls spine flexibility (3-10 joints)

### Limb Module (Arms)
The arm module creates an arm rig with:
- FK controls for shoulder, elbow, and wrist
- IK control for the hand
- Pole vector control for elbow direction
- IK/FK blending system

### Limb Module (Legs)
The leg module creates a leg rig with:
- FK controls for hip, knee, and ankle
- IK control for the foot
- Pole vector control for knee direction
- Foot roll system with toe and heel controls
- IK/FK blending system

## Customization

### Joint Orientation
The current system doesn't explicitly set joint orientations to X-down-the-bone, Y-up. To modify this:

1. Open `autorig/core/utils.py`
2. Find the `create_joint` function
3. Add joint orientation code after joint creation:

```python
def create_joint(name, position=(0, 0, 0), parent=None):
    # ... existing code ...
    
    # Orient joints with X down the bone, Y up
    if parent:
        cmds.joint(joint, edit=True, orientJoint="xyz", secondaryAxisOrient="yup")
    
    return joint
```

### Control Shapes and Colors
You can modify the control shapes and colors in `autorig/core/utils.py`:

- Change the `CONTROL_COLORS` dictionary to update colors
- Modify the `create_control` function to add new shapes

## Troubleshooting

### Common Issues and Solutions

1. **UI doesn't reload**
   - Use the provided shelf command: `import importlib; importlib.reload(sys.modules.get('startup')); import startup`
   - This ensures proper reloading of all modules

2. **Guides not appearing**
   - Ensure you've initialized the rig and added modules
   - Check if the guides group exists in your Outliner

3. **Build fails**
   - Make sure all guides are properly positioned with no overlapping
   - Check the Script Editor for specific error messages

4. **Controls not properly oriented**
   - Ensure guides are oriented correctly, not just positioned
   - For limbs, make sure the pole vector guide is positioned in the direction you want the joint to bend

5. **IK/FK Switch not working**
   - Check if the "ikFkBlend" attribute exists on the IK control
   - Ensure the value is properly set (0 for IK, 1 for FK)