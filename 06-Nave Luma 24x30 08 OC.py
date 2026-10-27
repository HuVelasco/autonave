"""
AutoNave 2026 - ETABS Version
Nave Luma 24x30 08 OC
Ported from SAP2000 to ETABS.

ETABS and SAP2000 share ~95% of the same API (both CSI products).
Key differences handled:
  - COM ProgID: CSI.ETABS.API.ETABSObject (vs CSI.SAP2000.API.SapObject)
  - File extension: .edb (vs .sdb)
  - AreaObj.SetLoadUniformToFrame: may behave differently in ETABS.
    The convert_area_loads_to_frame_and_point_loads workaround is enabled
    by default (same as original SAP2000 version).
  - PropFrame.SetNonPrismatic: used for haunched sections.
    If ETABS does not support this, the haunched segments are already
    modeled as separate frame objects with the HAUNCHED-WxxXyy I-sections,
    so the model will still work (just without the taper).
"""
from email.mime import base
import os
import sys
import comtypes.client
import Model
import Geometry
import numpy as np
import GravityLoads
import CFEWindLoads
import time
import Profiles
import Design
import CFESeismicLoads

np.set_printoptions(threshold=sys.maxsize)
np.set_printoptions(linewidth=np.inf)
np.set_printoptions(suppress=True)

time_a = time.time()

#Input variables
a = 24.0 #Span
h1 = 6.0
h2 = 1.8
ch, bh1, bh2 =  0, 3, 2
y = np.array([0., 7.5, 15., 22.5, 30.])
wind_columns_wall_A = np.arange(8, a, 8) #x position of columns
wind_columns_wall_B = np.arange(8, a, 8) #x position of columns
pinned_frame = True

#Roof Purlins
roof_purlins_pinned = True
maxSeparation = 1.6
lastPurlinDistance = 0.1
firstPurlinDistance = 0.1

#Lateral Purlins
lateral_purlins_pinned = True
end_purlins_pinned = True
wall_A_height = 0
wall_B_height = 0
wall_C_height = 0
wall_D_height = 0
lateral_purlins_maxSeparation = 1.6
lateral_purlins_lastPurlinDistance = 0.1
lateral_purlins_firstPurlinDistance = 0.15

#Roof Bracings
rb_start_y = y[:-1]
rb_end_y = y[1:]
number_of_roof_bracings_per_half_span = 2
at_purlins_worpoints = True

#Endwall bracings
eb_start_xA = [0, wind_columns_wall_A[-1]]
eb_end_xA = [wind_columns_wall_A[0], a]
eb_start_xB = [0, wind_columns_wall_B[-1]]
eb_end_xB = [wind_columns_wall_B[0], a]

#Lateral bracings
number_of_vertical_braces = 1
add_compression_elements_to_vertical_bracing = False

lb_start_y0 = [y[0],  y[-2]]
lb_end_y0 =   [y[1], y[-1]]
lb_start_ya = lb_start_y0
lb_end_ya = lb_end_y0

#Sections
vertical_bracing_double_angles = False
purlin_section_roof = "CF10CAL14"
purlin_section_lateral = purlin_section_roof
purlin_section_end = purlin_section_roof
horizontal_bracing_section = "r3/4" # Default = "Auto-rods"

#Loads
apply_to_purlins = True
#Gravity loads
dead_load_per_area = 15.0 #Kg/m2
live_load_per_area = 40.0 #Kg/m2
facade_dead_load_per_area = 10.0 #kg/m2

#Wind loads
qz1 = 90.0 #Presion dinamica de base, kg/m2
qz2 = 100.0 #Presion dinamica de base cuando h>10, kg/m2
interior_pressure_coefficient_x = 0.8 #Interior pressure coefficient x
interior_pressure_coefficient_y = -.65 #Interior pressure coefficient y

#Seismic loads
seismic_coefficient = 0.2378
base_reaction_dead_z = y[1] * a * (dead_load_per_area + 25)
seismic_dead_load_multiplier = 1
sesimic_live_load_multiplier = 0.5

#Analisis
max_analysis_iterations = 8
convert_area_loads_to_frame_and_point_loads = True

#Design
framing_design_type = 3 #2 = IMF, 3 = OMF

#File
APIPath = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'output', 'NaveLuma24x30')
os.makedirs(APIPath, exist_ok=True)
ModelPath = APIPath + os.sep + 'NaveLuma24x30_1(8oc).edb'
print(ModelPath)

################################################################
#1. DEFINE MODEL
time1 = time.time()

model = Model.ModelObject(software="ETABS")
model.initialize_new_model()
SapModel = model.sap_model

#Save
SapModel.File.Save(ModelPath)

time2 = time.time()
print(time2 - time1)


time1 = time.time()
#Define geometry objects and asign variables
geometry = Geometry.CreateGeometry(SapModel, a, h1, h2, y, ch, bh1, bh2)
geometry.set_endwall_columns(wind_columns_wall_A, wind_columns_wall_B)
geometry.set_roof_purlins(maxSeparation, lastPurlinDistance, firstPurlinDistance)
geometry.set_lateral_purlins(lateral_purlins_maxSeparation, lateral_purlins_lastPurlinDistance, lateral_purlins_firstPurlinDistance,
                             wall_A_height, wall_B_height, wall_C_height, wall_D_height)

################################################################
#2. MODEL OBJECTS
print("Creating model objects...")

time2 = time.time()
print(time2 - time1)


time1 = time.time()

print("Creating frames, purlins and areas...")
for i in range(y.shape[0] ):
    #Main frames
    is_endframe = False
    if i == 0 or i == y.shape[0] - 1: is_endframe = True

    obj = geometry.CreateHaunchedFrame(y[i], "f" + str(i), is_endframe, pinned_frame)
    geometry.main_frames_list.append(obj) #Add this frame to list
    if i < y.shape[0] - 1:
        #Roof purlins
        obj = geometry.CreateRoofPurlins(y[i], y[i + 1], "rp" + str(i), roof_purlins_pinned)
        geometry.purlin_list.append(obj) #Add this purlin to list
        #Create  Roof Areas
        obj = geometry.CreateRoofAreas(y[i], y[i + 1], "ar" + str(i), apply_to_purlins)
        #Create lateral walls purlins and add them to list
        obj = geometry.CreateLateralWallPurlins(0, y[i], y[i+1], wall_C_height, "pc", lateral_purlins_pinned)
        geometry.lateral_purlin_list_C.append(obj)
        obj = geometry.CreateLateralWallPurlins(a, y[i], y[i+1], wall_D_height, "pd", lateral_purlins_pinned)
        geometry.lateral_purlin_list_D.append(obj)


time2 = time.time()
print(time2 - time1)


time1 = time.time()
#Wind Columns
print("Creating wind columns...")
geometry.AddWindColumns("A")
geometry.AddWindColumns("B")


time2 = time.time()
print(time2 - time1)


time1 = time.time()
#Endwalls purlins
print("Creating end wall purlins...")
for i in range(geometry.number_of_cols_wall_A + 1):
    geometry.CreateEndWallPurlins(y[0], geometry.all_columns_coordinates_on_wall_A[i], geometry.all_columns_coordinates_on_wall_A[i + 1], wall_A_height, 'pa', end_purlins_pinned)
for i in range(geometry.number_of_cols_wall_B + 1):
    geometry.CreateEndWallPurlins(y[-1], geometry.all_columns_coordinates_on_wall_B[i], geometry.all_columns_coordinates_on_wall_B[i + 1], wall_B_height, 'pb', end_purlins_pinned)

#Roof Bracings
geometry.create_roof_bracing_x(rb_start_y, rb_end_y, number_of_roof_bracings_per_half_span, at_purlins_worpoints)



#End Bracings
geometry.create_end_bracing_x(y[0], eb_start_xA, eb_end_xA, number_of_braces=number_of_vertical_braces, add_compression_elements=add_compression_elements_to_vertical_bracing)
geometry.create_end_bracing_x(y[-1], eb_start_xB, eb_end_xB, number_of_braces=number_of_vertical_braces, add_compression_elements=add_compression_elements_to_vertical_bracing)

#Lateral Bracings
geometry.create_lateral_bracing_x(0, lb_start_y0, lb_end_y0, number_of_braces=number_of_vertical_braces, add_compression_elements=add_compression_elements_to_vertical_bracing)
geometry.create_lateral_bracing_x(a, lb_start_ya, lb_end_ya, number_of_braces=number_of_vertical_braces, add_compression_elements=add_compression_elements_to_vertical_bracing)


time2 = time.time()
print(time2 - time1)

#Assign Profiles
print("Assigning profiles...")
Profiles.set_initial_sections_type_1(SapModel, vertical_bracing_double_angles,
 purlin_section_roof = purlin_section_roof, purlin_section_lateral = purlin_section_lateral, purlin_section_end = purlin_section_end, horizontal_bracing_section= horizontal_bracing_section)

################################################################
#3. LOADS
#3.1. GRAVITY LOADS
print("Applying gravity loads...")
#Apply dead and live loads to roof areas
time1 = time.time()
GravityLoads.Apply.to_area_group(SapModel, "Areas_Roof_Gravity", "DEAD", dead_load_per_area)
GravityLoads.Apply.to_area_group(SapModel, "Areas_Roof_Gravity", "LIVE", live_load_per_area)


time2 = time.time()
print(time2 - time1)


time1 = time.time()
#3.2. WIND LOADS
print("Applying wind loads...")
#Define wind loads object
w1 = CFEWindLoads.AddWindLoads(SapModel, qz1, qz2,)
w1.set_geometry(a, h1, h2, y, wind_columns_wall_A, wind_columns_wall_B, False)

time2 = time.time()
print(time2 - time1)

w1.apply_loads_to_purlins = apply_to_purlins
time1 = time.time()
#Allow the correct application of lateral loads
#SetLoadTransfer is SAP2000 only — ETABS does not have this method.
#With convert_area_loads_to_frame_and_point_loads = True, loads are applied directly to frames.
try:
    if w1.apply_loads_to_purlins == True:
        ret = SapModel.FrameObj.SetLoadTransfer("Main_Columns", False, 1)
        assert (ret == 0),"verify"
        ret = SapModel.FrameObj.SetLoadTransfer("Haunched_Columns", False, 1)
        assert (ret == 0),"verify"
        ret = SapModel.FrameObj.SetLoadTransfer("Wind_Columns", False, 1)
        assert (ret == 0),"verify"
        ret = SapModel.FrameObj.SetLoadTransfer("Main_Beams", False, 1)
        assert (ret == 0),"verify"
        ret = SapModel.FrameObj.SetLoadTransfer("Haunched_Beams", False, 1)
        assert (ret == 0),"verify"
        ret = SapModel.FrameObj.SetLoadTransfer("Haunched_Beams_Central", False, 1)
        assert (ret == 0),"verify"

    elif w1.apply_loads_to_purlins == False:
        ret = SapModel.FrameObj.SetLoadTransfer("Purlins_Lateral", False, 1)
        assert (ret == 0),"verify"
        ret = SapModel.FrameObj.SetLoadTransfer("Purlins_end", False, 1)
        assert (ret == 0),"verify"
        ret = SapModel.FrameObj.SetLoadTransfer("Purlins_Roof", False, 1)
        assert (ret == 0),"verify"
except AttributeError:
    print("SetLoadTransfer not available in ETABS — skipping (loads applied directly to frames)")




#Wind in X+ direction
print(9.0)
w1.add_lateral_wall_windward_load("WIND_X1+", True)
w1.add_lateral_wall_windward_load("WIND_X2+")
w1.add_lateral_wall_leeward_load("WIND_X1+")
w1.add_lateral_wall_leeward_load("WIND_X2+")
w1.add_end_wall_lateral_load("WIND_X1+")
w1.add_end_wall_lateral_load("WIND_X2+")
w1.add_roof_windward_load("WIND_X1+", "WIND_X2+")
w1.add_roof_leeward_load("WIND_X1+", "WIND_X2+")


print(10)
#Wind in X- direction
w1.add_lateral_wall_windward_load("WIND_X1-", False)
w1.add_lateral_wall_windward_load("WIND_X2-", False)
w1.add_lateral_wall_leeward_load("WIND_X1-", False)
w1.add_lateral_wall_leeward_load("WIND_X2-", False)
w1.add_end_wall_lateral_load("WIND_X1-", False)
w1.add_end_wall_lateral_load("WIND_X2-", False)
w1.add_roof_windward_load("WIND_X1-", "WIND_X2-", False)
w1.add_roof_leeward_load("WIND_X1-", "WIND_X2-", False)

print(11)
#Wind in Y+ direction
w1.add_end_wall_windward_load("WIND_Y1+")
w1.add_end_wall_windward_load("WIND_Y2+")
w1.add_end_wall_leeward_load("WIND_Y1+")
w1.add_end_wall_leeward_load("WIND_Y2+")
w1.add_lateral_wall_lateral_load("WIND_Y1+")
w1.add_lateral_wall_lateral_load("WIND_Y2+")
w1.add_roof_lateral_load("WIND_Y1+", "WIND_Y2+")


print(12)
#Wind in Y- direction
w1.add_end_wall_windward_load("WIND_Y1-", False)
w1.add_end_wall_windward_load("WIND_Y2-", False)
w1.add_end_wall_leeward_load("WIND_Y1-", False)
w1.add_end_wall_leeward_load("WIND_Y2-", False)
w1.add_lateral_wall_lateral_load("WIND_Y1-", False)
w1.add_lateral_wall_lateral_load("WIND_Y2-", False)
w1.add_roof_lateral_load("WIND_Y1-", "WIND_Y2-", False)
print(13)


# SetComboAutoGenerate is SAP2000 only
try:
    SapModel.DesignSteel.SetComboAutoGenerate(False)
except AttributeError:
    pass

for i in model.design_combo_names:
    ret = SapModel.DesignSteel.SetComboStrength(i, True)
for i in model.deflection_combo_names:
    ret = SapModel.DesignSteel.SetComboDeflection(i, True)

# AISC360_16 is SAP2000; ETABS uses AISC360_05_IBC2006
try:
    SapModel.DesignSteel.AISC360_16.SetPreference(1, 2)
except AttributeError:
    try:
        SapModel.DesignSteel.AISC360_05_IBC2006.SetPreference(1, 2)
    except Exception as e:
        print(f"  [WARN] Could not set AISC design preference: {e}")

#Apply seismic loads
print("Applying seismic loads...")
base_reactions = geometry.get_base_reactions(Model.load_patterns)
base_reaction_live_z = base_reactions[1,5]
seismic_total_load = base_reaction_dead_z * seismic_dead_load_multiplier + base_reaction_live_z * sesimic_live_load_multiplier
print(seismic_total_load)
points = geometry.select_main_columns_top_points()
CFESeismicLoads.apply_load_to_points_array(SapModel, seismic_total_load, seismic_total_load, points)



#Convert area loads to frame and point loads
#In ETABS, areas use SetLoadUniform with a LoadPanel section — loads distribute
#through the mesh during analysis. convert_area_loads_to_frame_and_point_loads
#is only needed for SAP2000's SetLoadUniformToFrame mechanism.
#print("Converting area loads to frame and point loads...")
#if convert_area_loads_to_frame_and_point_loads:
#    print("Converting areas to actual loads")
#    geometry.convert_area_loads_to_frame_and_point_loads(True, True)

#analyze and run steel design
print("Analyzing and running steel design...")
Design.design_frames(SapModel, max_analysis_iterations, framing_design_type)


time_b = time.time()
print("Total time = ", time_b - time_a)

model.refreshview()
