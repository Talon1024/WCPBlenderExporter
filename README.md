Wing Blender
============

Wing Blender is an import/export script for Blender 2.65+ that allows you to export a VISION engine ([Wing Commander: Prophecy](http://www.wcnews.com/wcpedia/Wing_Commander:_Prophecy), [Wing Commander: Secret Ops](http://www.wcnews.com/wcpedia/Wing_Commander:_Secret_Ops)) IFF 3D model, or import a VISION engine IFF 3D model into Blender.

This means you'll be able to do most of your work in Blender, and then simply export it to the game without having to pass the model through multiple conversion programs (3D Exploration, `peoview`, `ModelC`, etc.).

This project is the successor to [OBJ2WCP](http://www.ciinet.org/kevin/java), a crappy old OBJ converter written noobishly in Java.

Features
--------

- Allows you to do most of the work on the model in Blender and then export it without the need to use external utilities to set the collision sphere, radius, or hardpoints.
- If a texture's filename is numeric, you will be able to convert it straight to a MAT file without renaming it. For example, if you have a texture named `424242.jpg`, your model will reference `00424242.mat`
- Converts Blender "empty" objects to hardpoints and other VISION engine mesh metadata.
- Collision sphere position and radius is automatically calculated, but can be manually overridden.
- Child objects can now be exported along with the main object.
- LOD mesh support

Installation
------------

1. Download a release from the "releases" page.
2. Create a custom folder on your hard drive for Blender scripts.
3. Create an `addons` folder within the folder you created in step 2.
4. Create an `io_scene_wcp` folder within the `addons` folder.
5. Unzip, extract, or copy all of the `.py` files into the `io_scene_wcp` folder you created in the previous step.
6. If you haven't set up a custom path for Blender scripts already, open Blender, go to File -> User Preferences, click on the File tab, and set the "Scripts" folder to the folder you created in step 2. Then, save your settings and quit Blender.
7. In Blender, go to File -> User Preferences, click on the Addons tab, and select the Import-Export category.
8. You should see "Import-Export: WCP/SO Mesh File" if you scroll down.
9. Check off the checkbox at the far right to enable the exporter script.
10. Save your settings if you want to permanently enable the exporter script.

For more information, see [this guide](https://www.blender.org/manual/advanced/scripting/python/add_ons.html) on the Blender wiki.

IFF Import Tutorial
-------------------

1. Obtain a VISION engine IFF 3D model from somewhere. You can extract an IFF 3D model from the game (or your favourite WC:SO mod, such as [Standoff](http://standoff.solsector.net) or [Unknown Enemy](http://unknownenemy.solsector.net)) using HCl's [treman](http://hcl.solsector.net/archive/treman1.zip). (You'll need to run it in [DOSBox](http://www.dosbox.com/) on modern systems, however.)

2. Extract the textures for this model. If you are using MAT files, place them in the `mat` folder, and the 3D model in the `mesh` folder.

3. If you are using PNG, BMP, GIF, or another high-quality image format, place the images in the same folder as the 3D model, and give them the same name as the 3D model, except with numbers after them. For example, if the 3D model is named `GRIKATH.IFF`, and you want to use high-quality images as textures, name the images `GRIKATH1.PNG`, `GRIKATH2.PNG`, etc.

3. Run the importer script to import the mesh into Blender.

IFF Export Tutorial
-------------------

1. The first LOD of main mesh, by default, should be named `detail-0`, unless you are using the active object as the first LOD of the main mesh.

2. The converter will, by default, use an object in the scene named `detail-0` as the LOD 0 mesh. You can make the converter use the active object as the LOD 0 mesh. If you turn this option off, or if the active object is not a mesh, the converter will try to use the object in the scene named `detail-0` as the LOD 0 mesh if it exists. Otherwise, nothing is exported.

3. a. If you are using materials, you must assign a material to each face on the model, and you must have at least one UV-mapped image texture in the material.

   b. If you are using face textures, you must assign a texture to each face on the model.

  If neither of these criteria are met, you may get an error like this:
  ![Wing Blender error](http://www.wcnews.com/chatzone/attachments/mat_error-jpg.8326/)

4. If the image referenced by an image texture has a numeric filename (ex. 245292.png), the exporter script will force the faces to use the image's number as the texture number.

5. In the text file accompanying the mesh file, you will see the texture filenames of the materials that your model uses and their associated texture numbers. Use this as a guide to convert the textures for WCSO.

   For example:

        Duhiky.png     --> 00022000.mat
        Basicmetal.tga --> 00022001.mat
        424242.jpg     --> 00424242.mat

   This indicates that `Duhiky.png` should be converted to `00022000.mat`, `Basicmetal.tga` should be converted to `00022001.mat`, `424242.jpg` should be converted to `00424242.mat`, etc.

6. Hardpoints must be empties named `hp-xxxx`, where `xxxx` is the name of the hardpoint. For example. `hp-gun1` will be exported as a hardpoint named `gun1`. The rotation matrix of the hardpoint is calculated automatically.

7. Hidden hardpoint empties (hardpoint empties that are not visible in Blender's viewport) will not be exported.

8. Optionally, you can override the calculated collision sphere and radius by using a spherical empty object named `collsphr`.

9. Go to where you exported the .IFF file. There should be a text file in that folder that has the same name as your IFF file, but with a
different extension.

10. Read the text file mentioned in step 5 to see which images should be converted, and what they should be named.

11. Convert the textures to WCP/SO .mat format, and place them in the `mat` folder under your WC Secret Ops root directory.

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

Note that the latest version may not be usable.

Getting involved (Development)
------------------------------

If you want to contribute to this project, get the latest development version of the code, and check out the issues page, or the [TODO Document](TODO.md).

Projects using Wing Blender
---------------------------

### WCPSO Model Upgrade Pack ###
![MUP Piranha](http://www.wcnews.com/chatzone/attachments/pir_update2-jpg.8236/)
![MUP Excalibur](http://www.wcnews.com/chatzone/attachments/excal_viewerfinal2-jpg.8266/)
![MUP Tigershark](http://www.wcnews.com/chatzone/attachments/tshark_ingame4-jpg.8260/)
![MUP Vesuvius](http://www.wcnews.com/chatzone/attachments/shot0004-jpg.8339/)
![MUP Manta](http://www.wcnews.com/chatzone/attachments/shot0001-jpg.8246/)

WC CIC Forums member DefianceIndustries is using Wing Blender to create the new models for his [WCPSO Model Upgrade Pack](http://www.wcnews.com/chatzone/threads/wing-commander-prophecy-secret-ops-model-update-pack.28103/).
