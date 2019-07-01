# SHL Toolbox

_text - part of shl etc etc etc_
SHL Toolbox is a set of workflow-enhancing tools for Rhino, with a particular focus on fabrication file preparation. The toolbox is deployed as an IronPython plugin for Rhino and makes use of the rhinoscriptsyntax and RhinoCommon libraries which are shipped with Rhino.

## Technologies Used
- Rhinoceros 6.0
- Ironpython 2.7 (?)
- Powershell
Libraries: rhinoscriptsyntax, RhinoCommon

## Getting Started

Note: These instructions will get you a copy of the project up and running on your local machine for development and testing purposes. See deployment for notes on how to deploy the project on a live system.

DRAFT:
1. Clone the shl toolbox repo to your local scripts folder. This is usually located at:
```
C:\Users\[YOUR_USER_NAME]\AppData\Roaming\McNeel\Rhinoceros\6.0\scripts
```
If you do not have a scripts directory, add one yourself to the 6.0 directory.

2. Copy shl_toolbox_lib directory to the scripts directory

3. You can now edit the commands in shl-toolbox/commands in the editor of your choice and run them directly in the Rhino Python script editor.

_TODO: determine best way to use libraries_
### Project

What things you need to install the software and how to install them

```
Give examples
```

### Compiling

The goal of compilation is a directory SHL_TOOLBAR containing everything the enduser needs:
- ```SHL_Toolbar_Installer_Part_1.rhi```: Installs the commands and toolbar
- ```SHL_Toolbar_Installer_Part_2.ps1```: Moves the required modules to the user's scripts directory ###NOTE LOCATION OF THIS###

There are two ways to compile, manual compilations is described in case there are bugs in the process or the user is unclear on the automated method:
Automated Method:
_TO WORK ON THIS_
1. A Rhino Installer Package (.rhi) file is a package containing a Rhino Plugin .rhp file and a Rhino User Interface .rui file.
.rhp files are compiled using the RhinoScriptCompiler located in buildhelpers.
Use buildhelpers/build_shl_toolbar_installer.py to 
Compilation 
_TO WORK ON THIS_

_TODO: graphic and explanation of compilation process_

```
Give the example
```

And repeat

```
until finished
```

End with an example of getting some data out of the system or using it for a little demo

## Running the tests

Explain how to run the automated tests for this system

### Break down into end to end tests

Explain what these tests test and why

```
Give an example
```

### And coding style tests

Explain what these tests test and why

```
Give an example
```

## Releasing

The goal of releasing is a directory SHL_TOOLBAR containing everything the enduser needs:
- ```SHL_Toolbar_Installer_Part_1.rhi```: Installs the commands and toolbar
- ```SHL_Toolbar_Installer_Part_2.ps1```: Moves the required modules to the user's scripts directory ###NOTE LOCATION OF THIS###
- ```_INSTALLATION_.txt```: Installation instructions
- ```SHL_Toolbox_Guide.pdf```: Full documentation

## Built With

* [Dropwizard](http://www.dropwizard.io/1.0.2/docs/) - The web framework used
* [Maven](https://maven.apache.org/) - Dependency Management
* [ROME](https://rometools.github.io/rome/) - Used to generate RSS Feeds

## Contributing

Please read [CONTRIBUTING.md](https://gist.github.com/PurpleBooth/b24679402957c63ec426) for details on our code of conduct, and the process for submitting pull requests to us.

## Versioning

We use [SemVer](http://semver.org/) for versioning. For the versions available, see the [tags on this repository](https://github.com/your/project/tags). 

## Authors

* **Billie Thompson** - *Initial work* - [PurpleBooth](https://github.com/PurpleBooth)

See also the list of [contributors](https://github.com/your/project/contributors) who participated in this project.

## License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details

## Acknowledgments

* Hat tip to anyone whose code was used
* Inspiration
* etc
