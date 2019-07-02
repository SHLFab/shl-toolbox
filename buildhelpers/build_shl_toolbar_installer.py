import clr
clr.AddReference('System.Xml.Linq')
import System.Xml.Linq as xm
import subprocess
import os
import zipfile

#todo: build xml properly (why is is coming out strangely when using XDocument.Save?)

#generate xml for command list
def make_xml_command_list(command_list,dir):
	"""generate xml for command list"""
	command_elements = []
	for command_name in command_list:
		path = dir + command_name + '.py'
		command = xm.XElement(xm.XName.Get("Command"),
								xm.XElement(xm.XName.Get("Name"),command_name),
								xm.XElement(xm.XName.Get("Path"),path),
								xm.XElement(xm.XName.Get("Type"),"Normal")
								)
		command_elements.append(command)
	return command_elements


def make_plugin_info(version_num):
	"""generate xml for plugin info"""
	name = "SHL Toolbar"
	build_directory = REPO_PATH + "build\\"
	author = "SHL Architects - Sean Lamb (Developer)"
	email = "aam@shl.dk"
	phone = " "
	address = "Njalsgade 17A/Pakhus 2/2300 Copenhagen S/Denmark"
	country = "Denmark"
	website = "www.shl.dk"
	update_url = ""
	copyright = "Loading SHL Fabrication Toolbox v" + str(version_num)
	rc_directory = "C:\\Program Files\\Rhino 6\\System\\RhinoCommon.dll"
	
	plugin = xm.XElement(xm.XName.Get("Plugin"),
							xm.XElement(xm.XName.Get("PluginName"),name),
							xm.XElement(xm.XName.Get("PluginFolder"),build_directory),
							xm.XElement(xm.XName.Get("AuthorName"),author),
							xm.XElement(xm.XName.Get("AuthorEmail"),email),
							xm.XElement(xm.XName.Get("AuthorPhone"),phone),
							xm.XElement(xm.XName.Get("AuthorAddress"),address),
							xm.XElement(xm.XName.Get("AuthorCountry"),country),
							xm.XElement(xm.XName.Get("AuthorWebsite"),website),
							xm.XElement("UpdateURL"),
							xm.XElement(xm.XName.Get("CopyrightMessage"),copyright),
							xm.XElement(xm.XName.Get("RhinoCommonOverride"),rc_directory)
							)
	return plugin


def archive_from_files(name,home_dir,files,extension='zip'):
	filename = name + "." + extension
	path = os.path.join(home_dir,filename)
	with zipfile.ZipFile(path,mode='a',compression=zipfile.ZIP_DEFLATED) as myzip:
		for x in files:
			myzip.write(x,arcname=os.path.basename(x))

#make rhp file
def make_rhi(rhp_path,rui_path,directory_out):
	"""make rhi file from rhp and rui"""
	pass

if __name__=="__main__":
	
	#set to local repo location
	global REPO_PATH
	REPO_PATH = 'C:\\Users\\lambs\\AppData\\Roaming\\McNeel\\Rhinoceros\\6.0\\scripts\\shl-toolbox\\'
	
	version_num = 0.3
	rhc_filename = "SHL_Toolbar.rhc"
	commands_path = REPO_PATH + 'command_staging\\' #path to the directory with the commands
	#List all command names by their filenames here. The command name will be the same as the filename.
	command_list = [
			"shlBridge",
			"shlSliceVolumes",
			"shlTag",
			"shlLaserSheet",
			"shlLayer",
			"shlPlotVolumes",
			"shlUnrollWithThickness",
			"shlMakeBox",
			"shlCollapseBox",
			"shlSketchLayers",
			"shlSmartOutline",
			"shlCutTerrain",
			"shlMakeSlidingLidBox",
			"shlCutPlan"
			]
	
	xml_command_list = make_xml_command_list(command_list,commands_path)
	plugin = make_plugin_info(version_num)
	
	commands = xm.XElement(xm.XName.Get("Commands"),xml_command_list)
	menu = xm.XElement("Menu")
	
	xdoc = xm.XDocument(xm.XDeclaration("1.0","utf-16","no"),xm.XElement(
				xm.XName.Get("RhinoScriptCompilerProject"),plugin,commands,menu))
	
	#location of rhinoscriptcompiler.
	path_to_exe = REPO_PATH + 'buildhelpers\\RhinoScriptCompiler.exe' 
	
	#Place where the Rhinoscript Compiler Project file SHL_Toolbar.rhc is located.
	#This is an XML file built by the batchscript automatically and read by the RhinoScriptCompiler
	path_to_file = REPO_PATH + 'build\\' + rhc_filename 
	
	#Write the xml to a .rhc file.
	#Dev note: using .ToString() here is poor form, .Save is preferred... but not working for some reason...
	#xdoc.Save("test1.rhc",xm.SaveOptions.DisableFormatting)
	str_doc = xdoc.ToString()
	file = open(path_to_file,'w')
	file.write('<?xml version="1.0" encoding="utf-16"?>\n')
	file.write(str_doc)
	file.close()
	print str_doc

	#Make the rhp file by running RhinoScriptCompiler.exe with SHL_Toolbar.rhc as an argument.
	subprocess.call([path_to_exe,path_to_file])


	#Get paths to the location of the rhp, rui, and the build directory where the .rhi file will be placed.
	rhp_path = os.path.normpath(REPO_PATH + 'build\\SHL_Toolbar.rhp')
	rui_path = os.path.normpath(REPO_PATH + 'build\\SHL_Toolbar.rui')
	rhi_build_path = os.path.normpath(REPO_PATH + 'build\\')
	
	#Remove any existing .rhi in the build directory.
	try:
		os.remove(os.path.normpath(REPO_PATH + 'build\\SHL_Toolbar.rhi'))
		print "removed existing rhi"
	except:
		pass
	
	#zip together the rhi and rui files and give the archive the .rhi extension.
	#.rhi files are just zipped files with the extension .zip renamed to .rhi
	archive_from_files("SHL_Toolbar",rhi_build_path,[rhp_path,rui_path],'rhi')
#	print rhp_path
#	print rui_path
#	print rhi_build_path
