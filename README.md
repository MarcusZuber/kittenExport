# Kitten Export

[![Build Extension](https://github.com/MarcusZuber/kittenExport/actions/workflows/build-and-release.yml/badge.svg)](https://github.com/MarcusZuber/kittenExport/actions/workflows/build-and-release.yml)

A Blender addon for exporting spacecraft models to Kitten Space Agency (KSA) format with support for thrusters, engines, meshes, and materials.

## Features

- **Thruster Management**: Create and configure thrusters with customizable properties
  - Location and exhaust direction
  - Thrust (in Newtons)
  - Specific impulse
  - Minimum pulse time
  - Control mapping (translation and rotation)
  - Sound events and volumetric effects

- **Engine Management**: Create and configure engines with detailed parameters
  - Location and exhaust direction
  - Thrust (in kilonewtons)
  - Specific impulse
  - Minimum throttle
  - Sound events and volumetric effects

- **Mesh Export**: Automatically export all mesh objects as individual GLB files
  - Organized in a dedicated `Meshes/` folder
  - Automatic filename collision handling
  - Selection preservation during export

- **Material Export**: Extract and export material textures
  - Automatic detection of diffuse, normal, and roughness/metallic/AO maps
  - Support for Principled BSDF materials
  - PNG export with organized naming
  - Organized in a dedicated `Textures/` folder

- **XML Generation**: Create comprehensive part.xml files with proper structure
  - Assets definition with mesh and material references
  - Part configuration with subparts
  - Windows-compatible line endings (CRLF)
  - Configurable coordinate precision
  - Pretty-formatted output

## Installation

1. Download the latest release from the [Releases](../../releases) page
2. Open Blender and go to **Edit** → **Preferences** → **Add-ons**
3. Click **Install from Disk** and select the downloaded `kittenExport-*.zip`
4. Enable the addon by checking the checkbox
5. Restart Blender if needed

## Usage

### Adding Thrusters

1. In the 3D viewport, press **Shift+A** to open the Add menu
2. Navigate to **KSA** → **Thruster**
3. An Empty object with arrow visualization will be created
4. In the Properties panel, configure thruster parameters:
   - **FxLocation**: Particle effect origin offset
   - **Thrust N**: Thrust in Newtons (default: 40)
   - **Specific Impulse Seconds**: ISP in seconds
   - **Minimum Pulse Time**: Minimum fire duration
   - **VolumetricExhaust_id**: Visual effect ID
   - **Sound event on**: Sound effect ID
   - **Control Map**: Translation and rotation axes this thruster responds to
   - **Export**: Enable/disable this thruster in exports

### Adding Engines

1. In the 3D viewport, press **Shift+A** to open the Add menu
2. Navigate to **KSA** → **Engine**
3. An Empty object with cone visualization will be created
4. In the Properties panel, configure engine parameters:
   - **Thrust kN**: Thrust in kilonewtons (default: 650)
   - **Specific Impulse Seconds**: ISP in seconds
   - **Minimum Throttle**: Minimum throttle fraction (0-1)
   - **VolumetricExhaust_id**: Visual effect ID
   - **SoundEventAction_On**: Sound effect ID
   - **Export**: Enable/disable this engine in exports

### Exporting to KSA Format

1. Select a target directory or create a new one
2. Go to **File** → **Export** → **KSA Part**
3. Configure export options:
   - **Part ID**: The identifier for your part (default: "MyRocket")
   - **Coordinate Decimal Places**: Precision for coordinates (default: 3 = 0.001)
4. Select the output folder and click **Export**

The exporter will:
- Create a `Meshes/` folder with individual GLB files for each mesh
- Create a `Textures/` folder with extracted material textures
- Generate a `part.xml` file with all configuration

### XML Structure

The generated `part.xml` follows this structure:

```xml
<?xml version="1.0" encoding="utf-8"?>
<Assets>
  <MeshFile Id="mesh_name" Path="Meshes/mesh_name.glb" Category="Vessel"/>
  
  <PbrMaterial Id="material_nameTextureFile">
    <Diffuse Path="Textures/material_name_Diffuse.png" Category="Vessel"/>
    <Normal Path="Textures/material_name_Normal.png" Category="Vessel"/>
    <RoughMetaAo Path="Textures/material_name_RoughMetaAo.png" Category="Vessel"/>
  </PbrMaterial>
  
  <Part Id="MyRocket">
    <SubPart Id="mesh_name">
      <SubPartModel Id="mesh_nameModel">
        <Mesh Id="mesh_nameMeshFile"/>
        <Material Id="material_nameTextureFile"/>
      </SubPartModel>
    </SubPart>
    
    <Thruster Id="thruster_name">
      <Location X="0.0" Y="0.0" Z="0.0"/>
      <ExhaustDirection X="1.0" Y="0.0" Z="0.0"/>
      <Thrust N="40"/>
      <SpecificImpulse Seconds="220"/>
      <MinimumPulseTime Seconds="0.008"/>
      <ControlMap CSV="TranslateForward,PitchUp"/>
      <VolumetricExhaust Id="ApolloRCS"/>
      <SoundEvent Action="On" SoundId="DefaultRcsThruster"/>
    </Thruster>
    
    <Engine Id="engine_name">
      <Location X="0.0" Y="0.0" Z="0.0"/>
      <ExhaustDirection X="1.0" Y="0.0" Z="0.0"/>
      <Thrust N="650000"/>
      <SpecificImpulse Seconds="452"/>
      <MinimumThrottle Value="0.05"/>
      <VolumetricExhaust Id="ApolloCSM"/>
      <SoundEvent Action="On" SoundId="DefaultEngineSoundBehavior"/>
    </Engine>
  </Part>
</Assets>
```

## Project Structure

The addon is organized into modular components:

- **`__init__.py`**: Main addon file with registration and imports
- **`thruster.py`**: Thruster-related classes and functions
- **`engine.py`**: Engine-related classes and functions
- **`export.py`**: Export operators and XML generation
- **`utils.py`**: Shared utility functions
- **`menu.py`**: UI menu definitions
- **`blender_manifest.toml`**: Addon metadata for Blender extension system

## Requirements

- **Blender**: 4.2.0 or later
- **Python**: 3.10+ (included with Blender)

## Contributing

Contributions are welcome! Please feel free to submit issues and pull requests.

## License

This project is licensed under the GNU General Public License v3.0 or later - see the [LICENSE](LICENSE) file for details.

## Author

**Marcus Zuber** and all [contributors](https://github.com/MarcusZuber/kittenExport/graphs/contributors).

## Support

For issues, questions, or suggestions, please open an issue on the [GitHub repository](../../issues).

## Version History

### 0.0.4
- Modularized code into separate modules (thruster, engine, export, utils, menu)
- Added `permissions: contents: write` to GitHub Actions for releases
- Improved code organization and maintainability

### 0.0.3
- Previous improvements and fixes

### 0.0.2
- Earlier version

### 0.0.1
- Initial release

