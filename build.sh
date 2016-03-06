#!/bin/bash

# Export the scripts to the Blender scripts folder

homedir=`echo $HOME | sed 's/\ /\\\ /g'`

if [ -n "$(uname -s | grep -i 'MINGW\|CYGWIN\|MSYS')" ]; then
  # We're using Bash on Windows!
  homedir="$homedir/Documents"
fi

vers=''
gvers=''

if [ $# -gt 0 -a $1 = '-d' ]; then # Copy to development folder
  vers='development'
  gvers="commit $(git log -n 1 --format=%h)"
  blender_scripts_folder="$homedir/BlenderScriptsDev/addons/io_scene_wcp" # Development script folder
else # Copy to production folder
  vers='production'
  blender_scripts_folder="$homedir/BlenderScripts/addons/io_scene_wcp" # Production script folder
fi

eval cp --target-directory=$blender_scripts_folder {__init__,export_iff,iff,iff_mesh,iff_read,mat_read,import_iff}.py
cat $blender_scripts_folder/__init__.py | sed "s/%\\x7BGIT_COMMIT\\x7D/$gvers/g" > $blender_scripts_folder/__init__.py
echo "Scripts copied to $vers folder."

if eval [ -d $blender_scripts_folder/__pycache__ ]; then
  eval rm -r $blender_scripts_folder/__pycache__
fi
