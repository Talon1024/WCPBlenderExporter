# Blender Commander
Blender Commander is an exporter script for Blender 2.65+ that allows you to export a VISION engine ([Wing Commander: Prophecy](http://www.wcnews.com/wcpedia/Wing_Commander:_Prophecy), [Wing Commander: Secret Ops](http://www.wcnews.com/wcpedia/Wing_Commander:_Secret_Ops)) IFF mesh, or XMF source code that can be compiled into a VISION engine IFF mesh via WCPPascal.

This means you'll be able to do most of your work in Blender, and then simply export it to the game without having to pass the model through multiple conversion programs (3D Exploration, `peoview`, `ModelC`, etc.).

This project is the successor to [OBJ2WCP](http://www.ciinet.org/kevin/java), a crappy old OBJ converter written noobishly in Java.

## Features
 - Allows you to do most of the work on the model in Blender and then export it and compile it without the need to use external utilities to set the collision sphere, radius, or hardpoints.
 - If a texture's filename is numeric, you will be able to convert it straight to a MAT file without renaming it. For example, if you have a texture named `424242.jpg`, your model will reference `00424242.mat`
 - Converts Blender "empty" objects to hardpoints and other VISION engine mesh metadata.
 - Collision sphere position and radius is automatically calculated
 - LOD mesh support

## Installation
1. Download a release from the "releases" page.
2. Create a custom folder on your hard drive for Blender scripts.
3. Create an `addons` folder within that folder.
4. Unzip/extract the exporter scripts in there.
5. In Blender, go to User Preferences -> Addons -> Import-Export
6. You should see "WCP/SO IFF Mesh File" and "WCP/SO IFF Mesh Source File" if you scroll down.
7. Check off the checkbox beside either one or both to enable the exporter script.

For more information, see [this guide](http://wiki.blender.org/index.php/Doc:2.6/Manual/Extensions/Python/Add-Ons) on the Blender wiki.

## Usage

 1. LOD (Level of Detail) models must be named as such:  
 `detail-0`  
 `detail-1`  
 `detail-2`  

 2. You can make the converter use the active object as the LOD 0 mesh. If you don't turn this option on, or if the active object is not a mesh, the converter will try to use the object in the scene named `detail-0` as the LOD 0 mesh if it exists. Otherwise, nothing is exported.
 3. Each face must have a material assigned to it, and each material used by the model must have at least one image texture.
 4. If the image referenced by an image texture has a numeric filename (ex. 245292.png), the exporter script will force the faces to use the image's number as the texture number.
 5. At the top of the mesh file source code, you will see the texture filenames of the materials that your model uses and their associated texture numbers. Use this as a guide to convert the textures for WCSO.

 For example:
 
 		IFF "Duhiky.iff"
        
		// Duhiky.png     --> 00022000.mat
 		// Basicmetal.tga --> 00022001.mat
	 	// 424242.jpg     --> 00424242.mat
 
 This indicates that `Duhiky.png` should be converted to `00022000.mat`, `Basicmetal.tga` should be converted to `00022001.mat`, `424242.jpg` should be converted to `00424242.mat`, etc.
 6. Hardpoints must be empties named `hp-xxxx`, where `xxxx` is the name of the hardpoint. For example. `hp-gun1` will be exported as a hardpoint named `gun1`. The rotation matrix of the hardpoint is calculated automatically.
 7. Hidden hardpoint empties (hardpoint empties that are not visible in Blender's viewport) will not be exported.
 8. Optionally, you can override the calculated collision sphere and radius by using an empty named `collsphr`.

If you are using the .IFF exporter, you will need to do the following after exporting the mesh:
1. Read the text file to see which images should be converted, and what they should be named.
2. Convert the textures to WCP/SO .mat format, and place them in the `mat` folder under your WC Secret Ops root directory.
 
If you are using the .PAS exporter, you will need to do the following after exporting the mesh:
1. Compile the mesh using WCPPascal
2. Copy it to the `mesh` folder under your WC Secret Ops root directory
3. Read the first few lines of the .pas file to see which images should be converted, and what they should be named.
4. Convert the textures to WCP/SO .mat format, and place them in the `mat` folder under your WC Secret Ops root directory.

To use the mesh, you will need to reference the mesh file in a ship file.

For modders who want to use this exporter script, an example .blend file and accompanying test data is included in the "examples" folder of this repository, and an exported "game-ready" version of the test ship is in the `test` folder.

## Getting involved (Testing)

If you want to try out the latest version of this thing yourself:
1. Follow the installation instructions above, but instead of downloading a release, clone this repository to get the latest development version of the code
2. Copy all the .py files to the `addons` folder under your Blender scripts folder.

To clone the repository, open the Linux terminal/Command prompt/Git Bash/whatever you use, go to a directory outside of your Blender scripts folder, and type in `git clone https://github.com/Talon1024/WCPBlenderExporter`. This will create a folder named "WCPBlenderExporter" containing the latest versions of the code files.

To update to the latest development version of the code, go to the folder you cloned the repository into using the Linux terminal/Command prompt/Git Bash/whatever you use, and type in `git pull origin master`.

## Getting involved (Development)

If you want to contribute to this project, get the latest development version of the code, and check out the issues page, or the planned features below.

## Planned features
These are features planned for future versions of Blender Commander, and they are not implemented yet.
 - BSP tree generation for corvette and capital ship component meshes.
