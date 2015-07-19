Blender Commander
=================

Blender Commander is an import/export script for Blender 2.65+ that allows you to export a VISION engine ([Wing Commander: Prophecy](http://www.wcnews.com/wcpedia/Wing_Commander:_Prophecy), [Wing Commander: Secret Ops](http://www.wcnews.com/wcpedia/Wing_Commander:_Secret_Ops)) IFF mesh, or XMF source code that can be compiled into a VISION engine IFF mesh via WCPPascal.

This means you'll be able to do most of your work in Blender, and then simply export it to the game without having to pass the model through multiple conversion programs (3D Exploration, `peoview`, `ModelC`, etc.).

This project is the successor to [OBJ2WCP](http://www.ciinet.org/kevin/java), a crappy old OBJ converter written noobishly in Java.

Features
--------

- Allows you to do most of the work on the model in Blender and then export it and compile it without the need to use external utilities to set the collision sphere, radius, or hardpoints.
- If a texture's filename is numeric, you will be able to convert it straight to a MAT file without renaming it. For example, if you have a texture named `424242.jpg`, your model will reference `00424242.mat`
- Converts Blender "empty" objects to hardpoints and other VISION engine mesh metadata.
- Collision sphere position and radius is automatically calculated
- LOD mesh support

Installation
------------

1. Download a release from the "releases" page.
2. Create a custom folder on your hard drive for Blender scripts.
3. Create an `addons` folder within the folder you created in step 2.
4. Create an `io_scene_wcp` folder within the `addons` folder.
5. Unzip, extract, or copy all of the `.py` files into the `io_scene_wcp`
   folder you created in the previous step.
6. If you haven't set up a custom path for Blender scripts already, open Blender,
   go to File -> User Preferences, click on the File tab, and set the "Scripts" folder
   to the folder you created in step 2. Then, save your settings and quit Blender.
7. In Blender, go to File -> User Preferences, click on the Addons tab, and select the Import-Export category.
8. You should see "Import-Export: WCP/SO Mesh File" if you scroll down.
9. Check off the checkbox at the far right to enable the exporter script.
10. Save your settings if you want to permanently enable the exporter script.

For more information, see [this guide](http://wiki.blender.org/index.php/Doc:2.6/Manual/Extensions/Python/Add-Ons) on the Blender wiki.

IFF Export Tutorial
-------------------

1. LOD (Level of Detail) models must be named as such:  
`detail-0`  
`detail-1`  
`detail-2`  

2. You can make the converter use the active object as the LOD 0 mesh. If you don't turn this option on, or if the active object is not a mesh, the converter will try to use the object in the scene named `detail-0` as the LOD 0 mesh if it exists. Otherwise, nothing is exported.
3. Each face must have a material assigned to it, and each material used by the model must have at least one image texture.
4. If the image referenced by an image texture has a numeric filename (ex. 245292.png), the exporter script will force the faces to use the image's number as the texture number.
5. In the text file accompanying the mesh file, you will see the texture filenames of the materials that your model uses and their associated texture numbers. Use this as a guide to convert the textures for WCSO.

   For example:

        Duhiky.png     --> 00022000.mat
        Basicmetal.tga --> 00022001.mat
        424242.jpg     --> 00424242.mat

   This indicates that `Duhiky.png` should be converted to `00022000.mat`, `Basicmetal.tga` should be converted to `00022001.mat`, `424242.jpg` should be converted to `00424242.mat`, etc.

6. Hardpoints must be empties named `hp-xxxx`, where `xxxx` is the name of the hardpoint. For example. `hp-gun1` will be exported as a hardpoint named `gun1`. The rotation matrix of the hardpoint is calculated automatically.
7. Hidden hardpoint empties (hardpoint empties that are not visible in Blender's viewport) will not be exported.
8. Optionally, you can override the calculated collision sphere and radius by using an empty named `collsphr`.

If you are using the .IFF exporter, you will need to do the following after exporting the mesh:

1. Go to where you exported the .IFF file. There should be a text file in that folder that has the same name as your IFF file, but with a different extension.
2. Read the text file mentioned in step 1 to see which images should be converted, and what they should be named.
3. Convert the textures to WCP/SO .mat format, and place them in the `mat` folder under your WC Secret Ops root directory.

If you are using the .PAS exporter, you will need to do the following after exporting the mesh:

1. Compile the mesh using WCPPascal.
2. Copy it to the `mesh` folder under your WC Secret Ops root directory.
3. Read the first few lines of the .pas file to see which images should be converted, and what they should be named.
4. Convert the textures to WCP/SO .mat format, and place them in the `mat` folder under your WC Secret Ops root directory.

To use the mesh, you will need to reference the mesh file in a ship file.

For modders who want to use this exporter script, an example .blend file and accompanying test data is included in the `examples` folder of this repository, and an exported "game-ready" version of the test ship is in the `test` folder.

Getting involved (Testing)
--------------------------

If you want to try out the latest version of this thing yourself:

1. Follow the installation instructions above, but instead of downloading a release, clone this repository to get the latest development version of the code.
2. Copy all the .py files to the `addons` folder under your Blender scripts folder.

To clone the repository:

1. Open the Linux terminal/Command prompt/Git Bash/whatever you use.
2. Go to a directory outside of your Blender scripts folder.
3. Type in `git clone https://github.com/Talon1024/WCPBlenderExporter`, and press enter.

This will create a folder named "WCPBlenderExporter" containing the latest versions of the code files.

To update to the latest development version of the code:

1. Go to the folder you cloned the repository into using the Linux terminal/Command prompt/Git Bash/whatever you use.
2. Type in `git pull origin master`, and press enter.

Getting involved (Development)
------------------------------

If you want to contribute to this project, get the latest development version of the code, and check out the issues page, or the [TODO Document](TODO.md).
