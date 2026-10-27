import os
import re
import sys
import comtypes.client
import numpy as np
import math
import array
import Model
import time
np.set_printoptions(threshold=sys.maxsize)
np.set_printoptions(linewidth=np.inf)
np.set_printoptions(suppress=True)

#Variables:
#Units
lb_in_F = 1
lb_ft_F = 2
kip_in_F = 3
kip_ft_F = 4
kN_mm_C = 5
kN_m_C = 6
kgf_mm_C = 7
kgf_m_C = 8
N_mm_C = 9
N_m_C = 10
Ton_mm_C = 11
Ton_m_C = 12
kN_cm_C = 13
kgf_cm_C = 14
N_cm_C = 15
Ton_cm_C = 16

#Define point object restraints
RestraintPinned = [True, True, True, False, False, False]
RestraintRigid = [True, True, True, True, True, True]

#Define frame releases
release_pinned = [False, False, False, False, True, True]
release_pinned_and_torsion = [False, False, False, True, True, True]
release_rigid = [False, False, False, False, False, False]




#Functions
def calculate_purlin_separation_and_number(length, firstPurlinDistance, lastPurlinDistance, maxSeparation):
    number_of_spaces = math.ceil((length - lastPurlinDistance - firstPurlinDistance) / maxSeparation)
    purlin_separation = (length - lastPurlinDistance - firstPurlinDistance) / (number_of_spaces)
    number_of_purlins = number_of_spaces + 1

    return purlin_separation, number_of_purlins

#---2023.01.21---Use numpy array operations instead of for loops:#
def calculate_tributary_lengths(arr):
    """Calculates tributary lengths for a given array of element positions"""
    start = (arr[1:] - arr[:-1]) / 2
    end = (arr[1:] - arr[:-1]) / 2
    tributary = np.concatenate(([arr[0]], arr[1:] + start, [arr[-1]]))
    tributary_start = np.concatenate(([arr[0]], arr[1:] - start))
    tributary_end = np.concatenate((arr[1:] + end, [arr[-1]]))
    return tributary, tributary_start, tributary_end

#---2023.01.21---Use list comprehension:#
def GetNamesFromElementsList(lst):
    """Returns only names from a list of elements"""
    names = [elem[0] for sublist in lst for elem in sublist[1:]]
    return names

def GetTributaryLengthsFromElementsList(lst): #tributary lengths must be always last of indexes
    """Returns only tributary lengths from a list of elements"""
    len1 = len(lst)
    len2 = len(lst[0])
    len3 = len(lst[0][1]) - 1
    tributary = []
    for i in range(len1):
        for j in range(1, len2):
            tributary.append(lst[i][j][len3])
    return tributary

def get_frame_points_and_coordinates(SapModel, frame):
    """Returns start and end points and coordinates of the points, given a frame name, str"""
    points_and_coordinates = []
    point1 = point2 =  ""
    x = y = z = 0.0
    ret =  SapModel.FrameObj.GetPoints(frame, point1, point2)
    point1 = ret[0]; point2 = ret[1]
    points_and_coordinates.append(ret[:2])
    ret = SapModel.PointObj.GetCoordCartesian(point1, x, y, z)
    points_and_coordinates.append(ret[:-1])
    ret = SapModel.PointObj.GetCoordCartesian(point2, x, y, z)
    points_and_coordinates.append(ret[:-1])
    return points_and_coordinates

def get_areas_points_and_coordinates(SapModel, area_list):
    """Returns area points and coordinates of the points, given a list of area names, str"""
    list_of_points = []
    list_of_coordinates = []
    list_of_coordinates_sorted = []

    for i in area_list:
        coordinates = [[], [], []] #x, y, z
        ret = SapModel.AreaObj.GetPoints(i, 0, [])
        number_of_points = ret[0]
        points = list(ret[1]) # ['48', '49', '11', '9']
        for j in points:
            x, y, z, ok = SapModel.PointObj.GetCoordCartesian(j, 0, 0, 0)
            coordinates[0].append(x)
            coordinates[1].append(y)
            coordinates[2].append(z)

        coordinates = np.asarray(coordinates)
        list_of_points.append(points)
        list_of_coordinates.append(coordinates)
        list_of_coordinates_sorted.append(np.sort(coordinates))
    
    return list_of_points, list_of_coordinates, list_of_coordinates_sorted


def get_z_from_x(x, a, alpha, h1): 
    """returns z coordinate of frame, given an x distance"""
    #Inputs angle
    x = np.array(x)
    h2 = math.tan(alpha) * a / 2
    z_top = np.where(x <= a/2, math.tan(alpha)*x, h2 - math.tan(alpha) * (x - a / 2)) + h1
    
    return z_top



######################################################################################



class CreateGeometry:
    def __init__(self, SapModel, a, h1, h2, y, ch, bh1, bh2, units = 8):
        #Main frames
        self.SapModel = SapModel
        self.a = a
        self.h1 = h1
        self.h2 = h2
        self.y = y
        self.ch = ch
        self.bh1 = bh1
        self.bh2 = bh2

        self.numberOfFrames = np.size(y)
        self.alpha = math.atan(2 * h2 / a) 

        #End Wall Columns
        self.wind_columns_wall_A = np.array([a/4, a/4*2, a/4*3]) #x position of columns
        self.wind_columns_wall_B = np.array([a/4, a/4*2, a/4*3]) #x position of columns

        self.number_of_cols_wall_A = self.wind_columns_wall_A.shape[0] #Number of wind columns on wall A, y = 0
        self.number_of_cols_wall_B = self.wind_columns_wall_B.shape[0] #Number of wind columns on wall B, y = max(y)
        self.all_columns_coordinates_on_wall_A = np.append(np.append(0, self.wind_columns_wall_A), a)
        self.all_columns_coordinates_on_wall_B = np.append(np.append(0, self.wind_columns_wall_B), a)
        
        #Interior columns
        self.interior_columns = np.array([a/2])

        #Roof Purlins
        self.maxSeparation = 1.5
        self.lastPurlinDistance = 0.2
        self.firstPurlinDistance = 0.2

        #Lateral Purlins
        self.wall_A_height = 0.0
        self.wall_B_height = 0.0
        self.wall_C_height = 0.0
        self.wall_D_height = 0.0
        self.lateral_purlins_maxSeparation = 1.2
        self.lateral_purlins_lastPurlinDistance = 0.2
        self.lateral_purlins_firstPurlinDistance = 0.2

        #Gravity loads
        self.dead_load_per_area = 20.0 #Kg/m2
        self.live_load_per_area = 40.0 #Kg/m2
        self.facade_dead_load_per_area = 0.0 #kg/m2
        self.facade_live_load_per_area = 0.0 #kg/m2

        #Tributary lengths
        self.main_frame_tributaries = calculate_tributary_lengths(y)
        self.wind_columns_A_triburares = calculate_tributary_lengths(np.append(np.append(0, self.wind_columns_wall_A), a))
        self.wind_columns_B_triburares = calculate_tributary_lengths(np.append(np.append(0, self.wind_columns_wall_B), a))
        
        #Elements lists
        self.main_frames_list = [] #[y, [frame name, point1, point2, tributary length],]
        self.purlin_list = [] #[y start, [purlin name, point1, point2, tributary length], ]
        self.lateral_purlin_list_C = [] #[y start, [purlin name, point1, point2, tributary length], ]
        self.lateral_purlin_list_D = [] #[y start, [purlin name, point1, point2, tributary length], ]
        self.endwall_purlin_list_A = [] #[x start, [purlin name, point1, point2, tributary length], ]
        self.endwall_purlin_list_B = [] #[x start, [purlin name, point1, point2, tributary length], ]
        #Wind column lists include main frame columns of A and B Walls
        self.wind_columns_list_A = [] #[y position, [column name, point1, point2, tributary length], ]
        self.wind_columns_list_B = [] #[y position, [column name, point1, point2, tributary length], ]
        #Areas lists
        self.area_list_roof = [] #[Area_name]
        self.area_list_wall_A = [] #[Area_name]
        self.area_list_wall_B = [] #[Area_name]
        self.area_list_wall_C = [] #[Area_name]
        self.area_list_wall_D = [] #[Area_name]
        #Bracing lists
        self.roof_bracing_list = []
        self.end_bracing_list = []
        self.lateral_bracing_list = []
        #Monitoring points
        self.monitoring_points_apex = []
        self.monitoring_points_lateral = []


    
    def set_main_frames_geometry(self, a, h1, h2, y, ch, bh1, bh2 ):
        """Set the geometry for the main frames of the structure, including the dimensions of the frame and the position of the frames (y)"""
        self.a = a
        self.h1 = h1
        self.h2 = h2
        self.y = y
        self.ch = ch
        self.bh1 = bh1
        self.bh2 = bh2

        self.numberOfFrames = np.size(y)
        self.alpha = math.atan(2 * h2 / a)
        #Tributary lengths
        self.main_frame_tributaries = calculate_tributary_lengths(y)

    def set_continuous_frame_geometry(self, haunch_multiplier, apex_haunch_multiplier):
        """
Set the geometry for the continuous frames of the structure, including the haunch multiplier and the apex haunch multiplier
"""
        self.haunch_multiplier = haunch_multiplier
        self.apex_haunch_multiplier = apex_haunch_multiplier


    def set_endwall_columns(self, wind_cols_A, wind_cols_B):
        """Set the position of the endwall columns and the number of columns on each wall,
also calculates the tributary lengths for these columns"""
        self.wind_columns_wall_A = wind_cols_A #x position of columns
        self.wind_columns_wall_B = wind_cols_B #x position of columns

        self.number_of_cols_wall_A = wind_cols_A.shape[0] #Number of wind columns on wall A, y = 0
        self.number_of_cols_wall_B = wind_cols_B.shape[0] #Number of wind columns on wall B, y = max(y)
        self.all_columns_coordinates_on_wall_A = np.append(np.append(0, wind_cols_A), self.a)
        self.all_columns_coordinates_on_wall_B = np.append(np.append(0, wind_cols_B), self.a)
        #Tributary lengths
        self.wind_columns_A_triburares = calculate_tributary_lengths(np.append(np.append(0, wind_cols_A), self.a))
        self.wind_columns_B_triburares = calculate_tributary_lengths(np.append(np.append(0, wind_cols_B), self.a))

    def set_roof_purlins(self, maxSeparation, lastPurlinDistance, firstPurlinDistance):
        """
        Set the maximum separation between roof purlins, the distance from the last purlin to the end of the roof, 
        and the distance from the first purlin to the start of the roof. 
        """
        self.maxSeparation = maxSeparation
        self.lastPurlinDistance = lastPurlinDistance
        self.firstPurlinDistance = firstPurlinDistance 

    def set_lateral_purlins(self, maxSeparation, lastPurlinDistance, firstPurlinDistance,
                            wall_A_height = 0.0, wall_B_height = 0.0, wall_C_height = 0.0, wall_D_height = 0.0, ):
        """
        Set the maximum separation between lateral purlins, the distance from the last purlin to the end of the lateral, 
        and the distance from the first purlin to the start of the lateral. 
        Also set the heights of walls A, B, C, and D (default value is 0.0).
        """         
        self.wall_A_height = wall_A_height
        self.wall_B_height = wall_B_height
        self.wall_C_height = wall_C_height
        self.wall_D_height = wall_D_height
        self.lateral_purlins_maxSeparation = maxSeparation
        self.lateral_purlins_lastPurlinDistance = lastPurlinDistance
        self.lateral_purlins_firstPurlinDistance = firstPurlinDistance

    def set_loads_gravity(self, dead, live, lateral_dead = 0.0, lateral_live = 0.0):
        """
        Set the maximum separation between lateral purlins, the distance from the last purlin to the end of the lateral, 
        and the distance from the first purlin to the start of the lateral. 
        Also set the heights of walls A, B, C, and D (default value is 0.0).
        """        
        self.dead_load_per_area = dead #Kg/m2
        self.live_load_per_area = live #Kg/m2
        self.facade_dead_load_per_area = lateral_dead #kg/m2
        self.facade_live_load_per_area = lateral_live #kg/m2

    def get_base_reactions(self, load_patterns):
        """Returns base reactions array in the format:
        [LoadCase, StepType, StepNum, Fx, Fy, Fz, Mx, My, Mz]
        """
        SapModel = self.SapModel
        IsLocked = SapModel.GetModelIsLocked()
        print(IsLocked)
        if IsLocked == False:
            ret = SapModel.Analyze.RunAnalysis()
            print(ret)
        ret = SapModel.Results.Setup.DeselectAllCasesAndCombosForOutput()
        for i in load_patterns:
            ret = SapModel.Results.Setup.SetCaseSelectedForOutput(i)
        ret = SapModel.Results.BaseReact(0, [], [],[],[],[],[],[],[],[], 0, 0,0)
        reactions = np.transpose(np.array(ret[1:-4], dtype=object))
        print("xxxxx")
        print(reactions)
        return reactions
        
    def convert_area_loads_to_frame_and_point_loads(self, delete_areas = True, unify_loads = True):  
        """Function to add loads directlly to frames""" 
        label = '34'
        time_a = time.time()
        SapModel = self.SapModel
        #Run analysis
        ret = SapModel.SetModelIsLocked(False)
        ret = SapModel.Analyze.RunAnalysis()
        print("xxxxx1")
        print(ret)
        #Get Base Reactions
        reactions1 = self.get_base_reactions(Model.load_patterns)
        print(reactions1)
        #Get distributed loads from elements
        ar = SapModel.LineElm.GetLoadDistributed("All", 0, [], [], [], [], [], [], [], [], [], [], [], 2)
        ar = np.transpose(np.array(ar[1:-1], dtype=object))
        ROUNDING_DIGITS = 6
        ar[:, [5, 6, 7, 8, 9, 10]] = np.around(ar[:, [5, 6, 7, 8, 9, 10]].astype(np.double), ROUNDING_DIGITS)
        names = ar[:, 0]
        element_values = ar[:, [1, 2, 3, 4, 9, 10]]

        
        #[frame_name, type_of_object, RDI, RDJ, // Load_path, load_type, coord_system, Load_Direction, Load_value_1, Load_value_2  ]
 
        object_values = np.vectorize(lambda x: np.asarray(SapModel.LineElm.GetObj(x, "", 0, 0, 0), dtype=object))(names)
        object_values = np.vstack(object_values)[:,:-1]
        relative_length = object_values[:, 3] - object_values[:, 2]
        start_length = object_values[:, 2]
        absolutized_distances = ar[:,[5,6]] * relative_length.reshape(1, -1).T + start_length.reshape(1,-1).T
        object_values[:, [2, 3]] = absolutized_distances

        #Combine object and element values to create applicable loads
        applicable_loads = np.hstack((object_values, element_values))

        #Round values
        #applicable_loads[:, [2, 3, 8, 9]] = np.around(applicable_loads[:, [2, 3, 8, 9]].astype(np.double), ROUNDING_DIGITS)
        #Sort
        ind = np.lexsort((applicable_loads[:,9].astype(np.double), applicable_loads[:,8].astype(np.double), applicable_loads[:,7].astype(int), 
        applicable_loads[:,4].astype('<U25'), applicable_loads[:,0].astype('<U25')))
        applicable_loads = applicable_loads[ind]

        x = applicable_loads

        #Unify and reduce number of loads
        if unify_loads:
            #get sorted unique loads indices
            unique, ind, count = np.unique(applicable_loads[:,[0,4,5,6,7,8,9,2,3]].astype('<U25'), return_index=True, return_counts=True, axis=0)
            #reduce applicable loads and multiply by occurrence
            applicable_loads = applicable_loads[ind]
            applicable_loads[:,8] =  applicable_loads[:,8]  * count
            applicable_loads[:,9] =  applicable_loads[:,9]  * count
            #get unique loads indices 2
            ind1 = np.unique(applicable_loads[:,[0,4,5,6,7,8,9]].astype('<U25'), return_index=True, axis=0)[1]
            ind1 = np.sort(ind1)
            ind2 = np.append(ind1[1:]-1, applicable_loads.shape[0] - 1)

            #Save unique loads
            unique_loads = applicable_loads[ind1]
            unique_loads[:,[3, 9]] = applicable_loads[ind2][:,[3, 9]]
            x = unique_loads

        #Apply loads to frames
        ret = SapModel.SetModelIsLocked(False)
        ret = np.vectorize(SapModel.FrameObj.SetLoadDistributed, otypes = '?')(
        x[:,0], x[:,4], x[:,5], x[:,7], x[:,2], x[:,3], x[:,8], x[:,9], x[:,6], True, False)

        #Delete Areas
        if delete_areas:
            ret = SapModel.AreaObj.Delete("ALL", 1)

        ########################################
        ######### VERIFY #######################
        
        reactions2 = self.get_base_reactions(Model.load_patterns)
        reactions1[:, 2:] = np.round(reactions1[:, 2:].astype(np.double), ROUNDING_DIGITS)
        reactions2[:, 2:] = np.round(reactions2[:, 2:].astype(np.double), ROUNDING_DIGITS)
        ret = SapModel.SetModelIsLocked(False)
        print("Reactions 1: \n")
        print(reactions1)
        print("Reactions 2: \n")
        print(reactions2)
        print("Reactions diff: \n")
        results1 = reactions1[:, [3,4,5,6,7,8]].astype(np.double)
        results2 = reactions2[:, [3,4,5,6,7,8]].astype(np.double)
        difference = np.round(results1 - results2, 3)
        print(difference)
        print("Reactions ratio: \n")
        results1 = np.where(results1 == 0, 0.0001, results1) #No zeros
        results2 = np.where(results2 == 0, 0.0001, results2) #No zeros
        ratio = np.round(results1 / results2, 3)
        print(ratio)
        time_b = time.time()
        print("Total time = ", time_b - time_a)
        
        

        #TODO add function for the point loads

    def CreateHaunchedFrame(self, y, prefix, is_endframe = False, pinned_frame = True ):
        SapModel = self.SapModel
        a = self.a
        h1 = self.h1
        h2 = self.h2
        ch = self.ch
        bh1 = self.bh1
        bh2 = self.bh2

        if pinned_frame: Restraint = RestraintPinned
        else: Restraint = RestraintRigid

        frame_list = [[0,0,0,0] for i in range(11)]
        frame_list[0] = y    
        #Geometric properties
        x1 = math.cos(self.alpha) * bh1
        y1 = math.sin(self.alpha) * bh1
        x2 = math.cos(self.alpha) * bh2
        y2 = math.sin(self.alpha) * bh2
        
        #Create Frame
        [frame_list[1][0], ret] = SapModel.FrameObj.AddByCoord(0, y, 0, 0, y, h1 - ch, "", "Default", "", 'Global')
        [frame_list[2][0], ret] = SapModel.FrameObj.AddByCoord(x1, y, h1 + y1, a / 2 - x2, y, h1 + h2 - y2, "", "Default", "", 'Global')
        [frame_list[3][0], ret] = SapModel.FrameObj.AddByCoord(a - x1, y, y1 + h1, a / 2 + x2, y, h1 + h2 - y2, "", "Default", "", 'Global')
        [frame_list[4][0], ret] = SapModel.FrameObj.AddByCoord(a, y, 0, a, y, h1 - ch, "", "Default", "", 'Global')
        [frame_list[5][0], ret] = SapModel.FrameObj.AddByCoord(0, y, h1, 0, y, h1 - ch, "", "Default", "", 'Global')
        [frame_list[6][0], ret] = SapModel.FrameObj.AddByCoord(a, y, h1, a, y, h1 - ch, "", "Default", "", 'Global')
        [frame_list[7][0], ret] = SapModel.FrameObj.AddByCoord(0, y, h1, x1, y, h1 + y1, "", "Default", "", 'Global')
        [frame_list[8][0], ret] = SapModel.FrameObj.AddByCoord(a / 2, y, h1 + h2, a / 2 - x2, y, h1 + h2 - y2, "", "Default", "", 'Global')
        [frame_list[9][0], ret] = SapModel.FrameObj.AddByCoord(a / 2, y, h1 + h2, a / 2 + x2, y, h1 + h2 - y2, "", "Default", "", 'Global')
        [frame_list[10][0], ret] = SapModel.FrameObj.AddByCoord(a, y, h1, a - x1, y, y1 + h1, "", "Default", "", 'Global')

        #Add to groups
        main_frame_groups = ["Main_Columns", "Main_Beams", "Main_Beams", "Main_Columns", "Haunched_Columns", 
        "Haunched_Columns", "Haunched_Beams", "Haunched_Beams_Central", "Haunched_Beams_Central", "Haunched_Beams"]

        for i in range(len(main_frame_groups)):
            if is_endframe:
                SapModel.FrameObj.SetGroupAssign(frame_list[i + 1][0], main_frame_groups[i] + "_end")
            else:
                SapModel.FrameObj.SetGroupAssign(frame_list[i + 1][0], main_frame_groups[i])

        #Set insertion point to top center
        beams_list = [2, 3, 7, 8, 9, 10]
        for i in beams_list:
            ret = SapModel.FrameObj.SetInsertionPoint(frame_list[i][0], 8, False, True, [0,0,0], [0,0,0])

        #Add points to list
        trib = self.main_frame_tributaries[0][np.where(np.isclose(self.y , y))[0][0]]
        for i in range(1, 11):
            [frame_list[i][1], frame_list[i][2], ret] = SapModel.FrameObj.GetPoints(frame_list[i][0], "", "")
            frame_list[i][3] = trib
        #Add Restraints
        point1 = SapModel.FrameObj.GetPoints(frame_list[1][0], "", "")
        SapModel.PointObj.SetRestraint(point1[0], Restraint)
        point1 = SapModel.FrameObj.GetPoints(frame_list[4][0], "", "")
        SapModel.PointObj.SetRestraint(point1[0], Restraint)

        #Add monitoring points to list
        if self.bh2 > 0:
            self.monitoring_points_apex.append(SapModel.FrameObj.GetPoints(frame_list[8][0], "", "")[1])
        else:
            self.monitoring_points_apex.append(SapModel.FrameObj.GetPoints(frame_list[2][0], "", "")[1])

        if self.ch > 0:
            self.monitoring_points_lateral.append(SapModel.FrameObj.GetPoints(frame_list[5][0], "", "")[1])
            self.monitoring_points_lateral.append(SapModel.FrameObj.GetPoints(frame_list[6][0], "", "")[1])
        else:
            self.monitoring_points_lateral.append(SapModel.FrameObj.GetPoints(frame_list[1][0], "", "")[1])
            self.monitoring_points_lateral.append(SapModel.FrameObj.GetPoints(frame_list[4][0], "", "")[1])

        return frame_list

    def create_continuous_frame(self, y, interior_columns, is_endframe = False,
    pinned_main_columns = True, pinned_interior_columns = True, rotate_interior_columns = None):
        if rotate_interior_columns == None: rotate_interior_columns = not is_endframe

        #Local Variables
        main_columns_list = []
        interior_columns_list = []
        haunch_list = []
        beams_list = [] 

        all_columns_x_position = np.append(np.append(0, interior_columns), self.a)
        spans = all_columns_x_position[1:] - all_columns_x_position[:-1]
        z_positions = get_z_from_x(all_columns_x_position, self.a, self.alpha, self.h1)

        #Model External Columns
        ret1 = self.SapModel.FrameObj.AddByCoord(0, y, 0, 0, y, self.h1, "", "Default", "", 'Global')
        ret2 = self.SapModel.FrameObj.AddByCoord(self.a, y, 0, self.a, y, self.h1, "", "Default", "", 'Global')
        main_columns_list.extend([ret1[0], ret2[0]])

        if pinned_main_columns: Restraint = RestraintPinned
        else: Restraint = RestraintRigid

        #Add Restraints
        point1 = self.SapModel.FrameObj.GetPoints(ret1[0], "", "")
        self.SapModel.PointObj.SetRestraint(point1[0], Restraint)
        point1 = self.SapModel.FrameObj.GetPoints(ret2[0], "", "")
        self.SapModel.PointObj.SetRestraint(point1[0], Restraint)
        
        #Mdodel internal columns and frames
        #Internal restraints
        if pinned_interior_columns: Restraint = RestraintPinned
        else: Restraint = RestraintRigid

        for i in range(spans.shape[0]):
            #Columns positions
            x = all_columns_x_position[i]
            z = z_positions[i]
            x2 = all_columns_x_position[i + 1]
            z2 = z_positions[i + 1]

            #haunches positions
            haunch_length = spans[i] * self.haunch_multiplier
            apex_haunch_length = spans[i] * self.apex_haunch_multiplier
            x_left = x + haunch_length
            z_left = get_z_from_x(x_left, self.a, self.alpha, self.h1)
            x_rigth = x + spans[i] - haunch_length
            z_rigth = get_z_from_x(x_rigth, self.a, self.alpha, self.h1)

            #Columns
            if i > 0:
                ret1 = self.SapModel.FrameObj.AddByCoord(x, y, 0, x, y, z, "", "Default", "", 'Global')
                interior_columns_list.append(ret1[0])
                #Add Restraints
                point1 = self.SapModel.FrameObj.GetPoints(ret1[0], "", "")
                self.SapModel.PointObj.SetRestraint(point1[0], Restraint)
                if rotate_interior_columns: 
                    self.SapModel.FrameObj.SetLocalAxes(ret1[0], 90)


            #Beams and haunches
            ret2 = self.SapModel.FrameObj.AddByCoord(x, y, z, x_left, y, z_left, "", "Default", "", 'Global')
            ret3 = self.SapModel.FrameObj.AddByCoord(x2, y, z2, x_rigth, y, z_rigth, "", "Default", "", 'Global')

            haunch_list.extend([ret2[0], ret3[0]])

            if x < self.a/2 and self.a/2 < x2: #When at apex
                x_center_left = self.a/2 - apex_haunch_length
                x_center_right = self.a/2 + apex_haunch_length
                z_center_left = get_z_from_x(x_center_left, self.a, self.alpha, self.h1)
                z_center_right = get_z_from_x(x_center_right, self.a, self.alpha, self.h1)

                ret5 = self.SapModel.FrameObj.AddByCoord(x_left, y, z_left, x_center_left, y, z_center_left, "", "Default", "", 'Global')
                ret6 = self.SapModel.FrameObj.AddByCoord(self.a/2, y, self.h1 + self.h2, x_center_left, y, z_center_left, "", "Default", "", 'Global')
                ret7 = self.SapModel.FrameObj.AddByCoord(self.a/2, y, self.h1 + self.h2, x_center_right, y, z_center_right, "", "Default", "", 'Global')
                ret8 = self.SapModel.FrameObj.AddByCoord(x_center_right, y, z_center_right, x_rigth, y, z_rigth, "", "Default", "", 'Global')

                haunch_list.extend([ret6[0], ret7[0]])
                beams_list.extend([ret5[0], ret8[0]])
            else:
                ret4 = self.SapModel.FrameObj.AddByCoord(x_left, y, z_left, x_rigth, y, z_rigth, "", "Default", "", 'Global')
                beams_list.append(ret4[0])

        #Add to groups
        for i in main_columns_list:
            if is_endframe:
                self.SapModel.FrameObj.SetGroupAssign(i, "Main_Columns" + "_end")
            else:
                self.SapModel.FrameObj.SetGroupAssign(i, "Main_Columns")
        for i in interior_columns_list:
            if is_endframe:
                self.SapModel.FrameObj.SetGroupAssign(i, "Interior_Columns" + "_end")
            else:
                self.SapModel.FrameObj.SetGroupAssign(i, "Interior_Columns")
        for i in haunch_list:
            if is_endframe:
                self.SapModel.FrameObj.SetGroupAssign(i, "Haunched_Beams" + "_end")
            else:
                self.SapModel.FrameObj.SetGroupAssign(i, "Haunched_Beams")
        for i in beams_list:
            if is_endframe:
                self.SapModel.FrameObj.SetGroupAssign(i, "Main_Beams" + "_end")
            else:
                self.SapModel.FrameObj.SetGroupAssign(i, "Main_Beams")
        #Set insertion point to top center
        for i in beams_list:
            ret = self.SapModel.FrameObj.SetInsertionPoint(i, 8, False, True, [0,0,0], [0,0,0])
        for i in haunch_list:
            ret = self.SapModel.FrameObj.SetInsertionPoint(i, 8, False, True, [0,0,0], [0,0,0])


    def CreateRoofPurlins(self, startPoint_y, endPoint_y, prefix, pinned):
        SapModel = self.SapModel
        a = self.a
        h1 = self.h1
        h2 = self.h2
        alpha = self.alpha
        lastPurlinDistance = self.lastPurlinDistance
        firstPurlinDistance = self.firstPurlinDistance
        maxSeparation = self.maxSeparation
        #Calculate number of purlins per half-frame
        beamLength = ((a / 2) ** (2) + h2 ** (2)) ** (0.5)
        purlin_separation, number_of_purlins = calculate_purlin_separation_and_number(
        beamLength, firstPurlinDistance, lastPurlinDistance, maxSeparation)

        #Purlin list
        local_purlin_list = [[0,0,0,0] for i in range(1 + number_of_purlins * 2)]
        local_purlin_list[0] = startPoint_y

        for i in range(0, number_of_purlins):
            #Model Purlins
            ret1 = SapModel.FrameObj.AddByCoord(firstPurlinDistance * math.cos(alpha) + math.cos(alpha) * purlin_separation * i, startPoint_y, #Left purlins
                                                h1 + math.sin(alpha) * firstPurlinDistance + math.sin(alpha) * purlin_separation * i, firstPurlinDistance * math.cos(alpha) + math.cos(alpha) * purlin_separation * i,
                                                endPoint_y, h1 + math.sin(alpha) * firstPurlinDistance + math.sin(alpha) * purlin_separation * i, "", "Default", prefix + str(i))

            ret2 = SapModel.FrameObj.AddByCoord(a - firstPurlinDistance * math.cos(alpha) - math.cos(alpha) * purlin_separation * i, #Right purlins
                                                startPoint_y, h1 + math.sin(alpha) * firstPurlinDistance + math.sin(alpha) * purlin_separation * i, a - firstPurlinDistance * math.cos(alpha) - math.cos(alpha) * purlin_separation * i,
                                                endPoint_y, h1 + math.sin(alpha) * firstPurlinDistance + math.sin(alpha) * purlin_separation * i, "", "Default", prefix + str(i + number_of_purlins) )
            
            #Add to groups
            SapModel.FrameObj.SetGroupAssign(ret1[0], "Purlins_Roof")
            SapModel.FrameObj.SetGroupAssign(ret2[0], "Purlins_Roof")

            #Set local axes
            SapModel.FrameObj.SetLocalAxes(ret1[0], -alpha * 180 / math.pi)
            SapModel.FrameObj.SetLocalAxes(ret2[0], alpha * 180 / math.pi)
            #Save frames and points to list
            local_purlin_list[i + 1][0], local_purlin_list[i + 1 + number_of_purlins][0] = ret1[0], ret2[0]
            [local_purlin_list[i + 1][1], local_purlin_list[i + 1][2], ret] = SapModel.FrameObj.GetPoints(ret1[0], "", "")
            [local_purlin_list[i + 1 + number_of_purlins][1], local_purlin_list[i + 1 + number_of_purlins][2], ret] = SapModel.FrameObj.GetPoints(ret1[0], "", "")
            #Save tributary lengths
            if i == 0:
                local_purlin_list[i + 1][3] = firstPurlinDistance + purlin_separation/2
                local_purlin_list[i + 1 + number_of_purlins][3] = firstPurlinDistance + purlin_separation/2
            elif i == number_of_purlins:
                local_purlin_list[i + 1][3] = lastPurlinDistance + purlin_separation/2
                local_purlin_list[i + 1 + number_of_purlins][3] = lastPurlinDistance + purlin_separation/2
            else:
                local_purlin_list[i + 1][3] = purlin_separation
                local_purlin_list[i + 1 + number_of_purlins][3] = purlin_separation
        #Releases
        if pinned == True:
            self.SapModel.FrameObj.SetReleases("Purlins_Roof", release_pinned, release_pinned, [0] * 6, [0] * 6, 1)


        return local_purlin_list

    def CreateLateralWallPurlins(self, x, startPoint_y, endPoint_y, wall_height, prefix, pinned,
                                maxSeparation =  None,  
                                lastPurlinDistance = None, 
                                firstPurlinDistance = None):
        if maxSeparation == None: maxSeparation = self.lateral_purlins_maxSeparation
        if lastPurlinDistance == None: lastPurlinDistance = self.lateral_purlins_lastPurlinDistance
        if firstPurlinDistance == None: lastPurlinDistance = self.lateral_purlins_firstPurlinDistance
        SapModel = self.SapModel
        h1 = self.h1 
        maxSeparation = self.lateral_purlins_maxSeparation
        lastPurlinDistance = self.lateral_purlins_lastPurlinDistance
        firstPurlinDistance = self.lateral_purlins_firstPurlinDistance
        #Calculate number of purlins
        length = h1 - wall_height
        purlin_separation, number_of_purlins = calculate_purlin_separation_and_number(
            length, firstPurlinDistance, lastPurlinDistance, maxSeparation)

        #Purlin list
        local_purlin_list = [[0,0,0,0] for i in range(1 + number_of_purlins)]
        local_purlin_list[0] = startPoint_y

        for i in range(0, number_of_purlins):
            #Model Purlins
            ret1 = SapModel.FrameObj.AddByCoord(x, startPoint_y, wall_height + firstPurlinDistance + purlin_separation * i,#Left purlins
                                                x, endPoint_y, firstPurlinDistance + wall_height + purlin_separation * i, "", "Default", prefix + str(i))
            #Add to groups
            SapModel.FrameObj.SetGroupAssign(ret1[0], "Purlins_Lateral")

            #Releases
            if pinned == True:
                self.SapModel.FrameObj.SetReleases("Purlins_Lateral", release_pinned, release_pinned, [0] * 6, [0] * 6, 1)

            #Set local axes
            SapModel.FrameObj.SetLocalAxes(ret1[0], 90)

            #Save frames and points to list
            local_purlin_list[i + 1][0] = ret1[0]
            [local_purlin_list[i + 1][1], local_purlin_list[i + 1][2], ret] = SapModel.FrameObj.GetPoints(ret1[0], "", "")
            #Save tributary lengths
            if i == 0:
                local_purlin_list[i + 1][3] = firstPurlinDistance + purlin_separation/2
            elif i == number_of_purlins:
                local_purlin_list[i + 1][3] = lastPurlinDistance + purlin_separation/2
            else:
                local_purlin_list[i + 1][3] = purlin_separation

        return local_purlin_list

    def CreateEndWallPurlins(self, y, startPoint_x, endPoint_x, wall_height, prefix, pinned,
                             maxSeparation = None, lastPurlinDistance = None, firstPurlinDistance = None):
        if maxSeparation == None: maxSeparation = self.lateral_purlins_maxSeparation
        if lastPurlinDistance == None: lastPurlinDistance = self.lateral_purlins_lastPurlinDistance
        if firstPurlinDistance == None: firstPurlinDistance = self.lateral_purlins_firstPurlinDistance
                                
        SapModel = self.SapModel
        a = self.a
        h1 = self.h1
        h2 = self.h2
        alpha = self.alpha
        maxSeparation = self.lateral_purlins_maxSeparation
        lastPurlinDistance = self.lateral_purlins_lastPurlinDistance
        firstPurlinDistance = self.lateral_purlins_firstPurlinDistance
        #Calculate number of purlins
        length1 = h1 - wall_height #from top of wall (if any) to h1
        number_of_spaces1 = math.ceil((length1 - lastPurlinDistance - firstPurlinDistance) / maxSeparation)
        purlin_separation1 = (length1 - lastPurlinDistance - firstPurlinDistance) / (number_of_spaces1)
        number_of_purlins1 = number_of_spaces1 + 1
        z1 = np.arange(firstPurlinDistance + wall_height, length1, purlin_separation1)

        last_purlin_height1 = z1[-1]

        length2 = h2 #from top of wall (if any) to h1
        number_of_spaces2 = math.ceil((length2) / maxSeparation)
        purlin_separation2 = (length2) / (number_of_spaces2)
        number_of_purlins2 = number_of_spaces2 + 1
        z2 = np.arange(last_purlin_height1, h1 + length2, purlin_separation2)[1:]

        z = np.append(z1, z2)

        number_of_purlins = number_of_purlins1 + number_of_purlins2 - 1
        
        #Set an x array, wish contains the posible x start and x end for any purlin modeled above h1
        xi = np.where(z > last_purlin_height1 , (z - h1) / math.tan(alpha), startPoint_x)
        xj = np.where(z > last_purlin_height1 , a - (z - h1) / math.tan(alpha), endPoint_x)
        #limit values of x
        xi = np.clip(xi,  a_max= endPoint_x, a_min = startPoint_x)
        xj = np.clip(xj, a_max = endPoint_x, a_min = startPoint_x)  

        #Purlin list
        local_purlin_list = [[0,0,0,0] for i in range(1 + number_of_purlins)]
        local_purlin_list[0] = startPoint_x

        for i in range(z.shape[0]):
            #if xi[i] <= endPoint_x and xj[i] >= startPoint_x:
            #Model  bottom Purlins
            ret1 = SapModel.FrameObj.AddByCoord(xi[i], y, z[i], xj[i], y, z[i], "", "Default", prefix + str(round(z[i],2)))
            
            #Add to groups
            SapModel.FrameObj.SetGroupAssign(ret1[0], "Purlins_end")

            #Releases
            if pinned == True:
                self.SapModel.FrameObj.SetReleases("Purlins_end", release_pinned, release_pinned, [0] * 6, [0] * 6, 1)
            
            #Set local axes
            SapModel.FrameObj.SetLocalAxes(ret1[0], 90)

            #Save frames and points to list
            local_purlin_list[i + 1][0] = ret1[0]
            [local_purlin_list[i + 1][1], local_purlin_list[i + 1][2], ret] = SapModel.FrameObj.GetPoints(ret1[0], "", "")
            #Save tributary lengths
            if i == 0:
                local_purlin_list[i + 1][3] = firstPurlinDistance + purlin_separation1/2
            elif i == number_of_purlins:
                local_purlin_list[i + 1][3] = lastPurlinDistance + purlin_separation2/2
            elif i == number_of_purlins1:
                local_purlin_list[i + 1][3] = purlin_separation1/2 + purlin_separation2/2
            elif i < number_of_purlins1:
                local_purlin_list[i + 1][3] = purlin_separation1    
            else:
                local_purlin_list[i + 1][3] = purlin_separation2
            
        return local_purlin_list



    def create_roof_bracing_x(self, start_y, end_y, number_of_braces = 1, at_purlins_work_points = True, pinned = True, prefix = "cvh"):
        """start_y and end_y are lists, number is the number of x´s by half span (a/2)
            start_y = [8, 24]
            end_y = [16, 32]
            """

        assert len(start_y) == len(end_y), "start_y and end_y are not the same size"

        length = ((self.a / 2) ** (2) + self.h2 ** (2)) ** (0.5)
        purlin_separation, number_of_purlins = calculate_purlin_separation_and_number(length, self.firstPurlinDistance, self.lastPurlinDistance, self.maxSeparation)
        spaces_per_brace = round((number_of_purlins - 0) / number_of_braces)

        first_distance = self.firstPurlinDistance
        last_distance = self.lastPurlinDistance

        start_x =  [(first_distance + spaces_per_brace * purlin_separation * i) * math.cos(self.alpha) for i in range(number_of_braces)]
        end_x = start_x[1:]
        end_x.append((length - last_distance) * math.cos(self.alpha))

        if not at_purlins_work_points:
            start_x[0] = 0
            end_x[-1] = self.a/2

        start_z = [get_z_from_x(i, self.a, self.alpha, self.h1) for i in start_x]
        end_z = [get_z_from_x(i, self.a, self.alpha, self.h1) for i in end_x]       
                
        for i in range(len(start_y)):
            for j in range(len(start_x)):
                #Side1
                ret1 = self.SapModel.FrameObj.AddByCoord(start_x[j], start_y[i], start_z[j], end_x[j], end_y[i], end_z[j], "", "None", "")
                ret2 = self.SapModel.FrameObj.AddByCoord(end_x[j], start_y[i], end_z[j], start_x[j], end_y[i], start_z[j], "", "None", "")
                #Side2
                ret3 = self.SapModel.FrameObj.AddByCoord(self.a - start_x[j], start_y[i], start_z[j], self.a - end_x[j], end_y[i], end_z[j], "", "None", "")
                ret4 = self.SapModel.FrameObj.AddByCoord(self.a - end_x[j], start_y[i], end_z[j], self.a - start_x[j], end_y[i], start_z[j], "", "None", "")
                #Add to group and set compression limit
                for k in [ret1[0], ret2[0], ret3[0], ret4[0]]:
                    ret = self.SapModel.FrameObj.SetGroupAssign(k, "Bracing_Horizontal")
                    ret = self.SapModel.FrameObj.SetTCLimits(k, True, -0.001, False, 0)

                #Releases
                if pinned == True:
                    ret = self.SapModel.FrameObj.SetReleases("Bracing_Horizontal", release_pinned, release_pinned, [0] * 6, [0] * 6, 1)

                #Add to list
                self.roof_bracing_list.extend([ret1[0], ret2[0], ret3[0], ret4[0]])

        #Releases
        if pinned == True:
            self.SapModel.FrameObj.SetReleases("Purlins_Roof", release_pinned, release_pinned, [0] * 6, [0] * 6, 1)
        #Set transmition of load as No (SAP2000 only, ETABS does not have SetLoadTransfer)
        try:
            self.SapModel.FrameObj.SetLoadTransfer("Bracing_Horizontal", False, 1)
        except AttributeError:
            pass
        #Set Weigth modifier to 0
        ret = self.SapModel.FrameObj.SetModifiers("Bracing_Horizontal", [1, 1, 1 ,1 ,1 ,1 ,1 ,0], 1)
                

                

    def create_end_bracing_x(self, y, start_x, end_x,  number_of_braces = 1, add_compression_elements = False, z_bottom_offset = 0,  pinned = True, prefix = "cvv"):
        """start_x and end_x are lists, number is the number of x´s by height
            z_bottom_offset is the bottom position of the brace from the ground
            add_compression_elements, adds tube sections and makes x bracing tension-only
            start_x = [0, 18.75]
            end_x = [6.25, 25]
            """
            #02.20.2022 - implemented number of vertical braces
            #02.20.2022 - implemented add compression elements
        assert len(start_x) == len(end_x), "start_x and end_x are not the same size"

        start_z = [get_z_from_x(i, self.a, self.alpha, self.h1) for i in start_x]
        end_z = [get_z_from_x(i, self.a, self.alpha, self.h1) for i in end_x]


        z0 = z_bottom_offset
        z1 = np.arange(z0, self.h1 + self.h1/number_of_braces, self.h1/number_of_braces)
        z1 = z1[z1 <= self.h1]
        z2 = np.copy(z1)


        for i in range(len(start_x)):
            z1[-1] = start_z[i]
            z2[-1] = end_z[i]
            for j in range(len(z1) - 1):
                #Model end bracings
                ret1 = self.SapModel.FrameObj.AddByCoord(start_x[i], y, z1[j], end_x[i], y, z2[j + 1], "", "None", "")
                ret2 = self.SapModel.FrameObj.AddByCoord(end_x[i], y, z2[j], start_x[i], y, z1[j + 1], "", "None", "")
            
                #Add to group
                self.SapModel.FrameObj.SetGroupAssign(ret1[0], "Bracing_Vertical")
                self.SapModel.FrameObj.SetGroupAssign(ret2[0], "Bracing_Vertical")

                if add_compression_elements == True:
                    if j > 0: #create compression elements in mid positions only, not first and last z's
                        ret3 = self.SapModel.FrameObj.AddByCoord(start_x[i], y, z1[j], end_x[i], y, z2[j], "", "None", "")
                        self.SapModel.FrameObj.SetGroupAssign(ret3[0], "Bracing_Vertical")
                        self.SapModel.FrameObj.SetGroupAssign(ret3[0], "Bracing_Vertical_compression")
                        ret = self.SapModel.FrameObj.SetTCLimits(ret1[0], True, -0.001, False, 0)
                        ret = self.SapModel.FrameObj.SetTCLimits(ret2[0], True, -0.001, False, 0) 

                #Releases
                if pinned == True:
                    ret = self.SapModel.FrameObj.SetReleases("Bracing_Vertical", release_pinned, release_pinned, [0] * 6, [0] * 6, 1)
                #Set transmition of load as No (SAP2000 only)
                try:
                    self.SapModel.FrameObj.SetLoadTransfer("Bracing_Vertical", False, 1)
                except AttributeError:
                    pass

                #Add to list
                self.end_bracing_list.extend([ret1[0], ret2[0]])

    def create_lateral_bracing_x(self, x, start_y, end_y, number_of_braces = 1, add_compression_elements = False, z_bottom_offset = 0, pinned = True, prefix = "cvv"):
        """start_y and end_y are lists, number is the number of x´s by height
            z_bottom_offset is the bottom position of the brace from the ground
            add_compression_elements, adds tube sections and makes x bracing tension-only 
            start_x = [0, 18.75]
            end_x = [6.25, 25]
            """
            #02.20.2022 - implemented number of vertical braces
            #02.20.2022 - implemented add compression elements
        assert len(start_y) == len(end_y), "start_x and end_x are not the same size"

        z0 = z_bottom_offset
        z = np.arange(z0, self.h1 + self.h1/number_of_braces, self.h1/number_of_braces)
        z = z[z <= self.h1]  


        for i in range(len(start_y)):
            for j in range(len(z) - 1):
                #Model end bracings
                ret1 = self.SapModel.FrameObj.AddByCoord(x, start_y[i], z[j], x, end_y[i], z[j + 1], "", "None", "")
                ret2 = self.SapModel.FrameObj.AddByCoord(x, end_y[i], z[j], x, start_y[i], z[j + 1], "", "None", "")
            
                #Add to group
                self.SapModel.FrameObj.SetGroupAssign(ret1[0], "Bracing_Vertical")
                self.SapModel.FrameObj.SetGroupAssign(ret2[0], "Bracing_Vertical")

                if add_compression_elements == True:
                    ret3 = self.SapModel.FrameObj.AddByCoord(x, start_y[i], z[j + 1], x, end_y[i], z[j + 1], "", "None", "")
                    self.SapModel.FrameObj.SetGroupAssign(ret3[0], "Bracing_Vertical")
                    self.SapModel.FrameObj.SetGroupAssign(ret3[0], "Bracing_Vertical_compression")
                    ret = self.SapModel.FrameObj.SetTCLimits(ret1[0], True, -0.001, False, 0)
                    ret = self.SapModel.FrameObj.SetTCLimits(ret2[0], True, -0.001, False, 0)      

                

                #Releases
                if pinned == True:
                    ret = self.SapModel.FrameObj.SetReleases("Bracing_Vertical", release_pinned, release_pinned, [0] * 6, [0] * 6, 1)
                #Set transmition of load as No (SAP2000 only)
                try:
                    self.SapModel.FrameObj.SetLoadTransfer("Bracing_Vertical", False, 1)
                except AttributeError:
                    pass

                #Add to list
                self.lateral_bracing_list.extend([ret1[0], ret2[0]])


    def CreateRoofAreas(self, startPoint_y, endPoint_y, prefix, apply_to_purlins = True, revert_local_3 = False):
        """Create roof area and add areas names to list"""
        SapModel = self.SapModel
        a = self.a
        h1 = self.h1
        h2 = self.h2

        if revert_local_3:
            tmp = [startPoint_y, endPoint_y]
            startPoint_y = tmp[1]
            endPoint_y = tmp[0]

        x1 = [0, a/2, a/2, 0]
        y = [endPoint_y, endPoint_y, startPoint_y, startPoint_y]
        z1 = [h1, h1 + h2, h1 + h2, h1]
        x2 = [a/2, a, a, a/2]
        z2 = [h1 +h2, h1, h1, h1 + h2]

        ret1 = SapModel.AreaObj.AddByCoord(4, x1, y, z1, "", "LoadPanel")
        ret2 = SapModel.AreaObj.AddByCoord(4, x2, y, z2, "", "LoadPanel")
        #Add to group
        SapModel.AreaObj.SetGroupAssign(ret1[3], "Areas_Roof_Gravity")
        SapModel.AreaObj.SetGroupAssign(ret2[3], "Areas_Roof_Gravity")


        if apply_to_purlins == True:
            SapModel.AreaObj.SetLocalAxes(ret1[3], 90)
            SapModel.AreaObj.SetLocalAxes(ret2[3], 90)


        self.area_list_roof.append(ret1[3])
        self.area_list_roof.append(ret2[3])

        return ret1[3], ret2[3]

    def AddWindColumns(self, endwall, Restraint = RestraintPinned):
        """Create end wind columns area and add them to list,
            then add the main columns that are part of the endwall.
            Main frames list must be populated before
            endwall = "A" or "B" """               
        SapModel = self.SapModel
        a = self.a
        h1 = self.h1
        h2 = self.h2
        alpha = self.alpha
        if endwall == "A":
            y = self.y[0]
            wind_column_positions = self.wind_columns_wall_A
            prefix = "wca"
        elif endwall == "B":
            y = self.y[-1]
            wind_column_positions = self.wind_columns_wall_B
            prefix = "wcb"
        else: print("Error, endwall name must be 'A' or 'B' ")

        x = wind_column_positions
        z_top = np.where(x <= a/2, math.tan(alpha)*x, h2 - math.tan(alpha) * (x - a / 2)) + h1
        #List
        local_list = [[0,0,0,0] for i in range(1 + x.shape[0])]
        local_list[0] = y
        s = 0
        for i in range(x.shape[0]):
            s+=1
            ret = SapModel.FrameObj.AddByCoord(x[i], y, 0, x[i], y, z_top[i], "", "Default", "", 'Global')
            #Add to groups
            SapModel.FrameObj.SetGroupAssign(ret[0], "Wind_Columns")
            #Add Restraints
            point1 = SapModel.FrameObj.GetPoints(ret[0], "", "")
            SapModel.PointObj.SetRestraint(point1[0], Restraint)
            #Local axis
            SapModel.FrameObj.SetLocalAxes(ret[0], 90)

            #Save columns to list
            local_list[i + 1][0] = ret[0]
            local_list[i + 1][1:3] = get_frame_points_and_coordinates(SapModel, ret[0])[0][:]
        
        if endwall == "A":
            self.wind_columns_list_A.append(y)
            self.wind_columns_list_A.append(local_list)
            #TODO self.wind_columns_list_A.append(self.main_frames_list[0][1])
            #TODO self.wind_columns_list_A.append(self.main_frames_list[0][5])
            #TODO self.wind_columns_list_A.append(self.main_frames_list[0][4])
            #TODO self.wind_columns_list_A.append(self.main_frames_list[0][6])
        elif endwall == "B":
            self.wind_columns_list_B.append(y)
            self.wind_columns_list_B.append(local_list)
            #TODO self.wind_columns_list_B.append(self.main_frames_list[self.y.shape[0] - 1][1])
            #TODO self.wind_columns_list_B.append(self.main_frames_list[self.y.shape[0] - 1][5])
            #TODO self.wind_columns_list_B.append(self.main_frames_list[self.y.shape[0] - 1][4])
            #TODO self.wind_columns_list_B.append(self.main_frames_list[self.y.shape[0] - 1][6])


        return local_list

    #################################################################
    #Apply gravity loads
    def applyGravityLoads(self, list_of_elements, load_pattern, force_per_area): #Load Pattern must be defined
        names = GetNamesFromElementsList(list_of_elements)
        lengths = GetTributaryLengthsFromElementsList(list_of_elements)
        for i in range (0, len(names)):
            force_per_length = force_per_area * lengths[i]
            ret = SapModel.FrameObj.SetLoadDistributed(names[i], load_pattern, 1, 10, 0, 1, force_per_length, force_per_length) #TODO 10 = Gravity direction or 11 = Projected Gravity direction?


    def select_main_columns_top_points(self):
        """Select points at the top of main columns: (0, y_i, h1) and (a, y_i, h1).
        Rewritten to avoid SelectObj.CoordinateRange which is SAP2000-only."""
        matching_points = []
        ret = self.SapModel.PointObj.GetNameList(0, [])
        all_points = list(ret[1])
        for pt in all_points:
            coord = self.SapModel.PointObj.GetCoordCartesian(pt, 0, 0, 0)
            px, py, pz = coord[0], coord[1], coord[2]
            if np.isclose(pz, self.h1, atol=0.01):
                if np.isclose(px, 0.0, atol=0.01) or np.isclose(px, self.a, atol=0.01):
                    if any(np.isclose(py, yi, atol=0.01) for yi in self.y):
                        matching_points.append(pt)
        return np.array(matching_points)
#################################################################
#Model



