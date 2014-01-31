# Blender Commander
Blender Commander is an exporter script for Blender 2.65+ that allows you to export XMF source code from Blender that can be compiled into a VISION engine ([Wing Commander: Prophecy](http://www.wcnews.com/wcpedia/Wing_Commander:_Prophecy), [Wing Commander: Secret Ops](http://www.wcnews.com/wcpedia/Wing_Commander:_Secret_Ops)) IFF mesh.

This means you'll be able to do most of your work in Blender, and then simply export it to the game without having to pass the model through multiple conversion programs (3D Exploration, `peoview`, `ModelC`, etc.).

This project is the successor to [OBJ2WCP](http://www.ciinet.org/kevin/java), a crappy old OBJ converter written noobishly in Java.

## Features
 - Allows you to do most of the work on the model in Blender and then export it and compile it without the need to use external utilities to set the collision sphere, radius, or hardpoints.
 - If a texture's filename is numeric, you will be able to convert it straight to a MAT file without renaming it. For example, if you have a texture named `424242.jpg`, your model will reference `00424242.mat`
 - Converts Blender "empty" objects to hardpoints and other VISION engine mesh metadata.
 - Collision sphere position and radius is automatically calculated
 - LOD mesh support

## Installation
To install the exporter script, create a custom folder for Blender scripts, create an "addons" folder within that folder, and unzip/extract the exporter scripts in there.

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
 7. Optionally, you can override the calculated collision sphere and radius by using an empty named `collsphr`.

After you have exported the mesh, you will need to compile the mesh using WCPPascal, copy it to the `mesh` folder under your WC Secret Ops root directory, and then convert the textures to WCP/SO .mat format, and place them in the `mat` folder under your WC Secret Ops root directory.

To use the mesh, you will need to reference the mesh file in a ship file.
 
## Known issues

 - Rotation matrix is not calculated correctly for rotations on Blender's Z axis.

## Planned features
These are features planned for future versions of Blender Commander, and they are not implemented yet.
 - BSP tree generation for corvette and capital ship component meshes.
 - Binary IFF file export
