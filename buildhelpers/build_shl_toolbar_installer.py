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
	build_directory = "O:\\SHL\\ModelshopCopenhagen\\05_scripting\\FabToolbox\\compiler_projects\\build\\"
	author = "SHL Architects - Sean Lamb (Developer)"
	email = "sel@shl.dk"
	phone = "+45 78 74 48 12"
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
	
	version_num = 0.2
	rhc_filename = "SHL_Toolbar.rhc"
#	commands_path = 'O:\\SHL\ModelshopCopenhagen\\05_scripting\\FabToolbox\\compiler_projects\\command_staging\\'
	commands_path = 'C:\\Users\\lambs\\AppData\\Roaming\\McNeel\\Rhinoceros\\6.0\\scripts\\ws_tools_repo\\shl-toolbox\\'
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
			"shlCutTerrain"
			]
	
	xml_command_list = make_xml_command_list(command_list,commands_path)
	plugin = make_plugin_info(version_num)
	
	commands = xm.XElement(xm.XName.Get("Commands"),xml_command_list)
	menu = xm.XElement("Menu")
	
	xdoc = xm.XDocument(xm.XDeclaration("1.0","utf-16","no"),xm.XElement(
				xm.XName.Get("RhinoScriptCompilerProject"),plugin,commands,menu))
	
	
	path_to_exe = "O:\\SHL\\ModelshopCopenhagen\\05_scripting\\FabToolbox\\compiler_projects\\RhinoScriptCompiler.exe"
	path_to_file = "O:\\SHL\\ModelshopCopenhagen\\05_scripting\\FabToolbox\\compiler_projects\\" + rhc_filename
	
	#debug... shouldn't have to be using ToString here, but as a temporary fix this works.
	#xdoc.Save("test1.rhc",xm.SaveOptions.DisableFormatting)
	str_doc = xdoc.ToString()
	file = open(path_to_file,'w')
	file.write('<?xml version="1.0" encoding="utf-16"?>\n')
	file.write(str_doc)
	file.close()
	print str_doc
	
	#make rhp file
#	subprocess.call([path_to_exe,path_to_file])
	
	
	#get paths to relevant files
	rhp_path = os.path.normpath("O:\\SHL\ModelshopCopenhagen\\05_scripting\\FabToolbox\\compiler_projects\\build\\SHL_Toolbar.rhp")
	rui_path = os.path.normpath("O:\\SHL\ModelshopCopenhagen\\05_scripting\\FabToolbox\\compiler_projects\\build\\SHL_Toolbar.rui")
	rhi_build_path = os.path.normpath("O:\\SHL\\ModelshopCopenhagen\\05_scripting\\FabToolbox\\compiler_projects\\build")
	
	try: 
		os.remove(os.path.normpath("O:\\SHL\ModelshopCopenhagen\\05_scripting\\FabToolbox\\compiler_projects\\build\\SHL_Toolbar.rhi"))
		print "removed"
	except:
		pass
	
	archive_from_files("SHL_Toolbar",rhi_build_path,[rhp_path,rui_path],'rhi')
#	print rhp_path
#	print rui_path
#	print rhi_build_path