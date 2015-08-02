#!/bin/bash

# Export the scripts to the Blender scripts folder

homedir=`echo $HOME | sed 's/\ /\\\ /g'`

if [ ! -z $(uname | grep -E 'MINGW|Cygwin') ]; then
  # We're using Bash on Windows!
  homedir="$homedir/Documents"
fi

# if [ -e import_iff.py ]; then
# blender_scripts_folder="$homedir/BlenderScriptsDev/addons/io_scene_wcp" # Development script folder
# cp --target-directory=$blender_scripts_folder {__init__,export_iff,iff,iff_mesh,import_iff}.py
# else
blender_scripts_folder="$homedir/BlenderScripts/addons/io_scene_wcp" # Production script folder
cp --target-directory=$blender_scripts_folder {__init__,export_iff,iff,iff_mesh}.py
# fi

if [ -d $blender_scripts_folder/__pycache__ ]; then
  rm -r $blender_scripts_folder/__pycache__
fi
