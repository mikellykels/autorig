# Modular Rig System User Guide

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
   - [Neck Module](#neck-module)
   - [Head Module](#head-module)
5. [Advanced Features](#advanced-features)
   - [Module Mirroring](#module-mirroring)
   - [Pole Vector Visualization](#pole-vector-visualization)
   - [Control Coloring System](#control-coloring-system)
6. [Upcoming Features](#upcoming-features)
7. [Customization](#customization)
8. [Troubleshooting](#troubleshooting)

## Overview

The Modular Rig System allows you to quickly build character rigs by combining reusable components. The system uses guide objects that you position on your character, and then automatically generates a complete animation rig with controls.

## Quick Start Guide

1. **Launch the tool** using the shelf button with this code:
   ```python
   import importlib; importlib.reload(sys.modules.get('startup')); import startup
   ```
2. **Initialize a rig**: Enter a character name and click "Initialize Rig"
3. **Add modules**: Add a spine, limbs, neck, and head as needed
4. **Create guides**: Click "Create All Guides" and position the orange locators on your character
5. **Mirror modules**: Optionally click "Mirror Modules" to mirror left side modules to the right
6. **Build the rig**: Click "BUILD RIG" to generate the full rig with controls
7. **Add root joint**: Click "Add Root Joint" to create the root joint and finalize the hierarchy

## Detailed Usage Instructions

### Setting Up a Character Rig

#### 1. Initialize the Rig
- Enter a name for your character
- Click "Initialize Rig" to create the base structure
- This creates the main groups that will organize your rig

#### 2. Adding Modules
- Select module type (Spine, Arm, Leg, Neck, Head)
- Choose side (Center, Left, Right)
- Configure module settings:
  - For Spine: Set number of joints (3-10)
  - For Limbs: Select type (Arm or Leg)
  - For Neck: Set number of joints (1-5)
  - For Head: No additional settings needed
- Click "Add Module"
- Added modules will appear in the module list

#### 3. Working with Guides
- Click "Create All Guides" to generate orange guide locators
- Move the guides to match your character's skeleton:
  - For spine: Position root, hip, spine segments, and chest
  - For arms: Position clavicle, shoulder, elbow, wrist, hand, and pole vector
  - For legs: Position hip, knee, ankle, foot, toe, heel, and pole vector
  - For neck: Position neck base and neck segments
  - For head: Position head base and head end
- **Tip**: The up vector guides (cyan color) help with joint orientation
- Use "Save Guide Positions" to store guide placement for later use
- Use "Load Guide Positions" to recall stored guide positions

#### 4. Mirroring Modules
- After setting up left side modules (arm/leg), click "Mirror Modules"
- This will create corresponding right side modules with mirrored settings

#### 5. Building the Rig
- After positioning all guides, click "BUILD RIG"
- The system will generate:
  - A joint hierarchy
  - Control curves
  - IK/FK systems for limbs
  - Pole vector visualizations
  - Connections between components

#### 6. Finalizing the Rig
- Click "Add Root Joint" to create the root joint and finalize hierarchy
- This will:
  - Create a root joint at the origin
  - Organize the joint hierarchy properly
  - Connect modules together (spine to root, limbs to spine, etc.)
  - Turn off guide visibility
  - Organize visualization elements

### Using the Generated Rig

#### Spine Controls
- **Root Control (Yellow cube)**: Controls the entire character
- **Hip Control (Yellow cube)**: Controls the hip region
- **Chest Control (Yellow cube)**: Controls the upper spine and chest

#### Limb Controls (Arms & Legs)
- **FK Mode**: Use the chain of circular controls
  - Left side: Blue color
  - Right side: Red color
- **IK Mode**: Use the cube control at the end of the chain and the sphere pole vector control
  - Left side: Blue color with blue pole vector line
  - Right side: Red color with red pole vector line
- **Switch between IK/FK**: Use the "FkIkBlend" attribute on the yellow IK/FK switch control
  - 0 = FK mode
  - 1 = IK mode
  - Values between 0-1 blend between both systems

#### Neck and Head Controls
- **Neck Base Control**: Connected to the chest, controls the base of the neck
- **Top Neck Control**: Controls the top of the neck
- **Head Control**: Connected to the top neck control, controls the head movement

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
- FK controls for clavicle, shoulder, elbow, and wrist
- IK control for the hand
- Pole vector control for elbow direction with visualization line
- IK/FK blending system

### Limb Module (Legs)
The leg module creates a leg rig with:
- FK controls for hip, knee, and ankle
- IK control for the foot
- Pole vector control for knee direction with visualization line
- Foot roll system with toe and heel controls
- IK/FK blending system

### Neck Module
The neck module creates a neck rig with:
- Neck base control
- Optional mid-neck control
- Top neck control
- Smooth blending between controls

Settings:
- **Number of Joints**: Controls neck flexibility (1-5 joints)

### Head Module
The head module creates a simple head rig with:
- Head control connected to the neck

## Advanced Features

### Module Mirroring
The system can automatically mirror left side modules to the right side:
- Only limb modules (arms and legs) are mirrored
- Controls are colored differently for each side (blue for left, red for right)
- All constraints and connections are set up automatically

### Pole Vector Visualization
For IK limbs, the system automatically creates visualization lines:
- Shows the connection between the middle joint (elbow/knee) and its pole vector
- Visibility toggles with IK/FK switch (only visible in IK mode)
- Color-coded to match the control scheme (blue for left, red for right)

### Control Coloring System
The rig uses a consistent color scheme for easy identification:
- **Center components**: Yellow
- **Left side components**: Blue
- **Right side components**: Red
- **IK/FK switch controls**: Yellow (all sides)

## Upcoming Features

The following features are currently in development:

### FK/IK Matching
- One-click switching between FK and IK modes without losing pose information
- Automatically matches FK controls to current IK pose and vice versa
- Useful for animation workflows requiring both IK and FK control

### Space Switching
- Multiple reference spaces for controls (world, COG, etc.)
- Ability to switch parent spaces without affecting animation
- Custom attribute to control space blending

### Stretchy IK Systems
- Elastic IK chains for more flexible animation
- Length preservation with stretching capabilities
- Prevents foot/hand sliding while maintaining natural movement

### Custom Control Colors
- User-defined color schemes
- Ability to change colors after rig creation
- Color presets for different character types

### Control Shape Library
- Additional control curve shapes for varied aesthetics
- Shape variations for different joint types
- Customizable control size and orientation

### Control Shape Swapping
- Change control shapes after rig creation
- Preserves all constraints and connections
- Maintains animation data when changing shapes

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
   - Check if up vector guides (cyan color) are properly positioned
   - For limbs, make sure the pole vector guide is positioned in the direction you want the joint to bend

5. **IK/FK Switch not working**
   - Check if the "FkIkBlend" attribute exists on the IK/FK switch control
   - Ensure the value is properly set (0 for FK, 1 for IK)

6. **Pole vector visualization not visible**
   - Make sure you're in IK mode (FkIkBlend attribute = 1)
   - Check if the visualizations group exists and is visible