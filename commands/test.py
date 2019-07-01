import rhinoscriptsyntax as rs
import Rhino
import scriptcontext as sc

def test():
	
	opt_KeepLayer = Rhino.Input.Custom.OptionToggle("KeepLayer","No","Yes")
	
	go = Rhino.Input.Custom.GetObject()
	go.GeometryFilter = Rhino.DocObjects.ObjectType.Brep

	go.SetCommandPrompt("Select Breps")
	go.AddOptionToggle("KeepLayer",opt_KeepLayer)
	
	go.GroupSelect = True
	go.SubObjectSelect = False
	go.AcceptEnterWhenDone(True)
	go.AcceptNothing(True)
	go.EnableClearObjectsOnEntry(False)
	go.GroupSelect = True
	go.SubObjectSelect = False
	go.DeselectAllBeforePostSelect = False
	
	res = None
	bHavePreselectedObjects = True
	while True:
		res = go.GetMultiple(1,0)
		if res == Rhino.Input.GetResult.Option:
			go.EnablePreSelect(False, True)
			continue
		#If not correct
		elif res != Rhino.Input.GetResult.Object:
			rs.Redraw()
			print "No Breps Selected!"
			return Rhino.Commands.Result.Cancel
		if go.ObjectsWerePreselected:
			rs.Redraw()
			bHavePreselectedObjects = True
			go.EnablePreSelect(False, True)
			continue
		break
	
	print "testing..."
	return None


def RunCommand( is_interactive ):

	test()
	return None

RunCommand(True)