#SHL Architects
#Sean Lamb 29-05-2019
#sel@shl.dk

#Example use of ws_lib package. Run in Rhino Python Interpreter.

import System.Drawing as sd
import rhinoscriptsyntax as rs

import shl-toolbox.lib.layers as wla
reload(wla)
import shl-toolbox.lib.rhino_util as wru
reload(wru)

wla.add_layer("t1",sd.Color.Aqua)

layerlist = "Layer 01"

rhobjs = wla.get_layer_objects(layerlist)

x = 5
guids = wru.docobj_to_guid(rhobjs)
y = 10
rs.MoveObjects(guids,[20,20,0])

wla.change_object_layers(guids,"t1")
