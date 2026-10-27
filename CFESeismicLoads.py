import comtypes.client
import numpy as np
import math
import Geometry
import time

"""""
#trys to attach to a running instance
print("Trying to attach to a running instance")
SapObject = comtypes.client.GetActiveObject("CSI.SAP2000.API.SapObject")
print(SapObject)
#create SapModel object
SapModel = SapObject.SapModel
print(SapModel)
#initialize model

ret = SapModel.SelectObj.CoordinateRange(-10000, 100000, -10000, 100000, 11, 11, False, "Global", False, True, False, False, False, False )

ret1 =  np.array(SapModel.SelectObj.GetSelected()[2])
print(ret1)
"""


def apply_load_to_points_array(SapModel, total_load_x, total_load_y, points_array):
    SapModel.SetModelIsLocked(False)
    load_x = total_load_x / points_array.shape[0]
    load_y = total_load_y / points_array.shape[0]

    for i in points_array:
        ret = SapModel.PointObj.SetLoadForce(i, 'Q_STAT_X+', [load_x,0,0,0,0,0], True)
        SapModel.PointObj.SetLoadForce(i, 'Q_STAT_Y+', [0,load_y,0,0,0,0], True)

#apply_load_to_points_array(SapModel, 1000, 1000, ret1)

#print (ret)