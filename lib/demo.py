import System.Drawing as sd
import rhinoscriptsyntax as rs

import ws_lib.layers as wla
reload(wla)
import ws_lib.rhino_util as wru
reload(wru)

wla.add_layer("t1",sd.Color.Aqua)

layerlist = "Layer 01"

rhobjs = wla.get_layer_objects(layerlist)

x = 5
guids = wru.docobj_to_guid(rhobjs)
y = 10
rs.MoveObjects(guids,[20,20,0])

wla.change_object_layers(guids,"t1")