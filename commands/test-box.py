import rhinoscriptsyntax as rs
import Rhino
import System.Drawing as sd
from scriptcontext import doc

def test():
	
	go = Rhino.Input.Custom.GetObject()
	go.GeometryFilter = Rhino.DocObjects.ObjectType.Brep
	
	opt_outer = Rhino.Input.Custom.OptionDouble(5,0.2,1000)
	
	go.SetCommandPrompt("Select breps to be boxed or press Enter for manual dimensioning (Suggested: 3 mm ply)")
	go.AddOptionDouble("Thickness", opt_outer)
	
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

	MANUAL = False
	while True:
		res = go.GetMultiple(1,0)

		#If new option entered, redraw a possible result
		if res == Rhino.Input.GetResult.Option:
			go.EnablePreSelect(False, True)
			continue
		elif res == Rhino.Input.GetResult.Nothing:
			MANUAL = True
		#If not correct
		elif res != Rhino.Input.GetResult.Object:
			return Rhino.Commands.Result.Cancel
			
		if go.ObjectsWerePreselected:
			bHavePreselectedObjects = True
			go.EnablePreSelect(False, True)
			continue
		
		break
	
	#set globals according to input
	global T_OBOX
	T_OBOX = opt_outer.CurrentValue	
	print "testing..."



if __name__ == "__main__":
	test()