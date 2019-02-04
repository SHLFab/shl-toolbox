"""
SHL Architects 16-10-2018
v1.1 Sean Lamb (Developer)
sel@shl.dk
v1.1: option list selection bug fix
-removed interactive
"""

import System.Drawing as sd
from scriptcontext import doc
import rhinoscriptsyntax as rs
import Rhino

# __commandname__ = "shlLayer"

def add_layer(name,color):
	myLayer = name
	layerInd = doc.Layers.Find(myLayer,False)
	if layerInd == -1:
		layerInd= doc.Layers.Add(myLayer,color)
	return layerInd


def set_layer_color(layerInd,color):
	layer = doc.Layers[layerInd]
	layer.Color = color


def set_layer_plot_weight(layerInd,weight):
	layer = doc.Layers[layerInd]
	layer.PlotWeight = weight


def change_object_layers(guids,layName,copy):
	if (not rs.IsLayer(layName)): add_layer(layName,sd.Color.White)
	
	if copy == True: guids = rs.CopyObjects(guids)
	
	[rs.ObjectLayer(id,layName) for id in guids]
	[rs.ObjectPrintWidthSource(id,0) for id in guids]
	[rs.ObjectPrintColorSource(id,0) for id in guids]
	[rs.ObjectColorSource(id,0) for id in guids]
	
	return guids


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

	return 0


def rc_layer_change():
	go = Rhino.Input.Custom.GetObject()
	go.GeometryFilter = Rhino.DocObjects.ObjectType.Curve

	opt_copy = Rhino.Input.Custom.OptionToggle(False,"No","Yes")

	#Index is used for layer change.
	list_vals = ["Guides","Cut","Score","LightScore","Engrave"]
	list_index = 1
	opt_list = go.AddOptionList("DestinationLayer",list_vals,list_index)
	go.SetCommandPrompt("Select curves to move to layer or press Enter to add lasercut layers to document")
	go.AddOptionToggle("CopyCurves", opt_copy)
	#go.AddOptionDouble("InnerThickness", opt_inner)

	go.GroupSelect = True
	go.SubObjectSelect = False
	go.AcceptEnterWhenDone(True)
	go.AcceptNothing(True)
	go.EnableClearObjectsOnEntry(False)
	go.EnableUnselectObjectsOnExit(False)
	go.GroupSelect = True
	go.SubObjectSelect = False
	go.DeselectAllBeforePostSelect = False

	res = None
	bHavePreselectedObjects = False

	while True:
		res = go.GetMultiple(1,0)
		
		#If new option entered, redraw a possible result
		if res == Rhino.Input.GetResult.Option:
			# print res
			go.EnablePreSelect(False, True)
			if go.OptionIndex() == opt_list:
				list_index = go.Option().CurrentListOptionIndex
			continue
		
		elif res == Rhino.Input.GetResult.Nothing:
			MANUAL = True
			get_lcut_layers()
			return None
		
		#If not correct
		elif res != Rhino.Input.GetResult.Object:
			return Rhino.Commands.Result.Cancel
		
		if go.ObjectsWerePreselected:
			bHavePreselectedObjects = True
			go.EnablePreSelect(False, True)
			continue
		
		break
	
	#option results
	DESTINATION_LAYER = list_vals[list_index]
	COPY_ORIGINALS = opt_copy.CurrentValue
	
	get_lcut_layers()
	
	#selected curve objects
	c_ids_list = []
	for i in xrange(go.ObjectCount):
		c_obj = go.Object(i).Object()
		c_ids_list.append(c_obj.Id)

	switcher = {
		0:"XXX_LCUT_00-GUIDES",
		1:"XXX_LCUT_01-CUT",
		2:"XXX_LCUT_02-SCORE",
		3:"XXX_LCUT_03-LSCORE",
		4:"XXX_LCUT_04-ENGRAVE",
		}

	changed_crvs = change_object_layers(c_ids_list,switcher[list_index],COPY_ORIGINALS)
	rs.UnselectAllObjects()
	rs.SelectObjects(changed_crvs)


def RunCommand( is_interactive ):
	rc_layer_change()
	return 0

RunCommand(True)
