"""help docstring"""
#workshop_lib
#Layer Functions

#SHL Architects
#Sean Lamb 2018-09-26
#TODO: define an __all__

import System.Drawing as sd
from scriptcontext import doc
import rhinoscriptsyntax as rs
import Rhino

def add_layer(name,color):
	"""add layer by name.
	params: str name, System.Drawing.Color
	returns: int layer index"""

	myLayer = name
	layerInd = doc.Layers.Find(myLayer,False)
	if layerInd == -1:
		layerInd= doc.Layers.Add(myLayer,color)
	return layerInd


def set_layer_color(layerInd,color):
	"""params: int layer index, System.Drawing.Color"""
	layer = doc.Layers[layerInd]
	layer.Color = color


def set_layer_plot_weight(layerInd,weight):
	"""params: int layer index, float plotweight. -1 for NoPrint"""
	layer = doc.Layers[layerInd]
	layer.PlotWeight = weight


def change_object_layers(guids,layName,copy=False):
	"""change layer of objects.
	params: [guids], str layName. bool copy
	return: new objects on layer (or original objects with reassigned layer if copy==False)"""

	if (not rs.IsLayer(layName)): add_layer(layName,sd.Color.White)

	if copy == True: guids = rs.CopyObjects(guids)

	[rs.ObjectLayer(id,layName) for id in guids]
	return guids


def get_layer_objects(*layers):
	"""Get all of the objects on the layer. If layer does not exist, will get an empty list back
	params: *str layers
	return: [docobjs]
	Dev Notes: - raises exception is no objects in layer. should this be changed?"""

	rhobjs = []
	for layerName in layers:
		rhobjs += doc.Objects.FindByLayer(layerName)
		if not rhobjs: raise Exception("No objects in this layer")
		#if not rhobjs: rc.Result.Cancel

	for obj in rhobjs: obj.Select(True)
	return rhobjs


def ind_to_name(layer_indices):
	"""convert a list of layer indices to layer names for use in rhinoscriptsyntax."""
	layer_names = [doc.Layers[index].Name for index in layer_indices]
	return layer_names


def get_lcut_layers():
	#Add layers
	l_index_guide = add_layer("XXX_LCUT_00-GUIDES",sd.Color.Gray)
	l_index_cut = add_layer("XXX_LCUT_01-CUT",sd.Color.Red)
	l_index_score = add_layer("XXX_LCUT_02-SCORE",sd.Color.Blue)
	l_index_lscore = add_layer("XXX_LCUT_03-LSCORE",sd.Color.Lime)
	l_index_raster = add_layer("XXX_LCUT_04-ENGRAVE",sd.Color.Magenta)

	#reset colours
	doc.Layers[l_index_guide].Color = sd.Color.Gray
	doc.Layers[l_index_cut].Color = sd.Color.Red
	doc.Layers[l_index_score].Color = sd.Color.Blue
	doc.Layers[l_index_lscore].Color = sd.Color.Lime
	doc.Layers[l_index_raster].Color = sd.Color.Magenta

	set_layer_plot_weight(l_index_guide,-1)
	set_layer_plot_weight(l_index_cut,0.0001)
	set_layer_plot_weight(l_index_score,0.0001)
	set_layer_plot_weight(l_index_lscore,0.0001)
	set_layer_plot_weight(l_index_raster,0.0001)

	return [l_index_guide,l_index_cut,l_index_score,l_index_lscore,l_index_raster]