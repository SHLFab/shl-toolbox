# SHL Toolbox

**SHL Toolbox** is a set of workflow-enhancing tools for Rhino, with a particular focus on fabrication file preparation. Developed at [Schmidt Hammer Lassen Architects](https://www.shl.dk/), The toolbox is deployed as an IronPython plugin for Rhino and makes use of the [rhinoscriptsyntax](https://developer.rhino3d.com/api/RhinoScriptSyntax/) and [RhinoCommon](https://developer.rhino3d.com/guides/rhinocommon/) libraries.


## Getting Started

_Note: These instructions will get you a copy of the project up and running on your local machine for development and testing purposes. See deployment for notes on how to deploy the project on a live system._

- Clone the ```shl-toolbox``` repo to your local scripts folder. This is usually located at:
```
C:\Users\[YOUR_USER_NAME]\AppData\Roaming\McNeel\Rhinoceros\6.0\scripts
```
If you do not have a scripts directory, add one yourself to the 6.0 directory.

- You can now edit the commands in ```shl-toolbox/commands``` in the editor of your choice and test them by running them directly in the Rhino Python script editor.


### Compiling

The goal of compilation is a directory SHL_TOOLBAR containing everything the enduser needs:
- ```SHL_Toolbar_Installer_Part_1.rhi```: Installs the commands and toolbar
- ```SHL_Toolbar_Installer_Part_2.ps1```: Moves the required modules to the user's scripts directory ###NOTE LOCATION OF THIS###
- ```shl_toolbox_lib```: modules to be moved into the user's scripts directory
An RHI file is a compressed archive of a Rhino Python Plugin (.rhp) and a Rhino Toolbar (.rui) file. 

There are two ways to compile, manual compilations is described in case there are bugs in the process or the user is unclear on the automated method. In both methods the .rui is edited and saved within Rhino. See McNeel's [toolbar documentation](http://docs.mcneel.com/rhino/5/help/en-us/toolbarsandmenus/customize_toolbars.htm) for more information. 

#### Staging the commands before compiling:
Commands developed in the /commands directory should reference the in-development library in /lib with imports formatted like so:
import shl-toolbox.lib.layers
However, when the plugin is compiled, the referenced library will exist in the user's scripts folder, USER\AppData\Roaming\McNeel\Rhinoceros\6.0\scripts\shl_toolbox_lib. Therefore, when compiling the project, you must copy the commands to be included in the plugin to \command_staging and change the imports like so:
BEFORE: import shl-toolbox.lib.layers
AFTER: import shl_toolbox_lib.layers

#### Building the Plugin Installer:
_Manual Method:_
1. Make the .rui: Create Toolbar buttons as necessary and save out the toolbar. The macros for each command should have the same name as the .py files representing the individual commands. When exporting the toolbar, be sure to edit the toolbar name to update the version number.
2. Edit the .rhc and output a .rhp file:
a) A Rhino Compiler Project (.rhc) is read by buildhelpers\RhinoScriptCompiler.exe to generate the .rhp file. In the repository, in directory /build you should find the most recent .rhc file, SHL_Toolbar.rhc. Open RhinoscriptCompiler.exe and "open an existing project." Here you can edit the existing .rhc by adding or removing commands, changing plugin setting, etc.
b) Ensure to edit the plugin settings to update the version number.
c) Build the project and chose "just Plug-In". SHL_Toolbar.rhp should be built in the /build directory
3. Compress the .rhp and .rui files into a .zip archive SHL_Toolbar.zip and change the file extension to SHL_Toolbar.rhi to make the installer.

_Automated Method:_
The script build_shl_toolbar_installer.py can be run from the Python editor in Rhino 6. This script contains variables for version number and filenames in \command_staging to target for building commands. Place the most updated .rui in \build and run the code to automatically build the .rhc file and the .rhi file.  Note that command names in Rhino will automatically be generated from the python filenames in \command_staging. Therefore double check your .rui to make sure the command macro assigned to the toolbar button is correct!



## Releasing

The goal of releasing is a directory SHL_TOOLBAR containing everything the enduser needs:
- ```SHL_Toolbar_Installer_Part_1.rhi```: Installs the commands and toolbar
- ```SHL_Toolbar_Installer_Part_2.ps1```: Moves the required modules to the user's scripts directory ###NOTE LOCATION OF THIS###
- ```_INSTALLATION_.txt```: Installation instructions
- ```SHL_Toolbox_Guide.pdf```: Full documentation

SHL-SPECIFIC STUFF:
Distributing the library:
The library is not compiled, so it must be copied into the user's scripts folder in a directory named shl_toolbox_lib. This is typically done with a powershell script or manually.

## Built With

* [Dropwizard](http://www.dropwizard.io/1.0.2/docs/) - The web framework used
* [Maven](https://maven.apache.org/) - Dependency Management
* [ROME](https://rometools.github.io/rome/) - Used to generate RSS Feeds

## Contributing

Please read [CONTRIBUTING.md](https://gist.github.com/PurpleBooth/b24679402957c63ec426) for details on our code of conduct, and the process for submitting pull requests to us.

## Versioning

We use [SemVer](http://semver.org/) for versioning. For the versions available, see the [tags on this repository](https://github.com/your/project/tags). 

## Authors

* **Sean Lamb** - *Initial work - v0.1-0.3* - [sean-nl](https://github.com/sean-nl)
* **Ali Mirakbari** - *Main contact* - [sean-nl](https://github.com/sean-nl)

https://github.com/SHLFab

## License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details


