import comtypes.client
import numpy as np
import math
import Geometry
import time

def get_z_from_x(x, a, alpha, h1): 
    """returns z coordinate of frame, given an x distance"""
    #Inputs angle
    x = np.array(x)
    h2 = math.tan(alpha) * a / 2
    z_top = np.where(x <= a/2, math.tan(alpha)*x, h2 - math.tan(alpha) * (x - a / 2)) + h1
    
    return z_top

def get_z_from_x(x, a, h1, h2): 
    """returns z coordinate of frame, given an x distance"""
    #Inputs distances
    x = np.array(x)
    alpha = math.atan(2 * h2 / a)
    z_top = np.where(x <= a/2, math.tan(alpha)*x, h2 - math.tan(alpha) * (x - a / 2)) + h1
    
    return z_top

def calculate_tributary_lengths(arr):
    """Calculates tributary lengths for a given array of element positions"""
    elements = arr.shape[0]
    tributary_start = np.zeros(elements)
    tributary_end = np.zeros(elements)
    tributary = np.zeros(elements)
    
    for i in range(1, elements - 1):
        start = (arr[i] - arr[i - 1]) / 2
        end = (arr[i+1] - arr[i]) / 2
        tributary_start[i] = arr[i] - start
        tributary_end[i] = arr[i] + end
        tributary[i] = start + end

    tributary_start[-1] = tributary_end[-2]
    tributary[-1] = end
    tributary[0] =  tributary_end[0] = tributary_start[1]
    tributary_end[-1] = arr[-1]
    
    return tributary, tributary_start, tributary_end

def get_frame_points_and_coordinates(frame):
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

def averaged_lateral_cpes(h_average, wall_length, x_positions):
    cpes, cpe_start_points, cpe_end_points = CpeCoefficient.lateral_and_end_walls_lateral(h_average, wall_length)
    trib, trib_start, trib_end = calculate_tributary_lengths(x_positions)

    average_cpes = np.zeros(trib_start.shape[0])

    for i in range(trib_start.shape[0]):
        test_start = trib_start[i]
        test_trib = trib[i]
        test_end = trib_end[i]

        mask = (cpe_end_points > test_start) & (cpe_start_points < test_end)
        tributary_cpes = cpes[mask]
        tributary_cpes_start = cpe_start_points[mask]
        tributary_cpes_end = cpe_end_points[mask]
        #Lengths:
        t1 = tributary_cpes_end - test_start
        t2 = tributary_cpes_end - tributary_cpes_start
        t3 = test_end - tributary_cpes_start
        t4 = np.array([test_trib] * t1.shape[0])
        #Minimum lengths:
        tributary_lengs = np.minimum(np.minimum(np.minimum(t1, t2), t3), t4)
        #Average cpe:
        average_cpes[i] = np.sum(tributary_lengs * tributary_cpes) / test_trib

    return average_cpes, trib


class CpeCoefficient:
#Cpe coefficient tables based on gamma angle and d/b relation
#Tables are limited to gamma < 10 degrees
#TODO: ADD VALUES WHEN GAMMA > 10 DEGREES

    @staticmethod
    def insert_frame_positions_into_cpes(frame_positions, start_points, end_points, cpes1, cpes2, wall_length, flip_points = False):
        """combine cpe positions and frame positions, in order. calculates cpes values in order too.
        Only works for ascendent ordered points"""
   

        cp1 = cpes1
        cp2 = cpes2
        sp = start_points


        for i in range(frame_positions.shape[0]):
            if not frame_positions[i] in sp:
                idx = sp.searchsorted(frame_positions[i])
                idx2 = np.where(frame_positions[i] >= start_points)[0][-1]
                sp = np.insert(sp, idx,  frame_positions[i])
                cp1 = np.insert(cp1, idx,  cpes1[idx2])
                cp2 = np.insert(cp2, idx,  cpes2[idx2])
                    

        ep = np.append(sp[1:], max(frame_positions[-1], end_points[-1]))

        if flip_points:
            sp = wall_length - sp
            ep = wall_length - ep

        return cp1, cp2, sp, ep

    #Table 4.3.1
    @staticmethod
    def lateral_walls_leeward(d_b, angle = NotImplemented): #d_b = d/b
        """d_b = d/b"""
        if d_b <= 1: cpe = -0.5
        elif d_b <= 2: cpe = np.interp(d_b, [1, 2], [-.5,-0.3])
        elif d_b <= 4: cpe = np.interp(d_b, [2, 4], [-.3,-0.2])
        else: cpe = -0.2 #When d/b > 4
        return cpe
        
    @staticmethod
    def end_walls_leeward(d_b, angle = NotImplemented): #d_b = d/b 
        """d_b = d/b"""
        if d_b <= 1: cpe = -0.5
        elif d_b <= 2: cpe = np.interp(d_b, [1, 2], [-.5,-0.3])
        elif d_b <= 4: cpe = np.interp(d_b, [2, 4], [-.3,-0.2])
        else: cpe = -0.2 #When d/b > 4
        return cpe   

    @staticmethod
    def lateral_walls_lateral(h_average, wall_length, flip_points = False, angle = NotImplemented):
        cpe = np.array([-0.65, -0.5, -0.3, -0.2]) 
        start_points = np.array([0, h_average, 2 * h_average, 3 * h_average])
        start_points = start_points[start_points <  wall_length]
        end_points = np.append(start_points[1:], wall_length)
        cpe = cpe[0:len(start_points)]
        if flip_points:
            start_points = wall_length - start_points
            end_points = wall_length - end_points
        return cpe, start_points, end_points

    @staticmethod
    def end_walls_lateral(h_average, wall_length, flip_points = False, angle = NotImplemented):
        cpe = np.array([-0.65, -0.5, -0.3, -0.2]) 
        start_points = np.array([0, h_average, 2 * h_average, 3 * h_average])

        if 3 * h_average > wall_length / 2:
            #Find where to insert the middle point, and insert it
            index = np.where(start_points > wall_length / 2)[0][0]
            start_points = np.insert(start_points, index, wall_length / 2)
            cpe = np.insert(cpe, index, cpe[index - 1])
        else:
            start_points = np.hstack((start_points, wall_length / 2))
            cpe = np.hstack((cpe, cpe[-1]))

        start_points = start_points[start_points <  wall_length]
        end_points = np.append(start_points[1:], wall_length)
        cpe = cpe[0:len(start_points)]
        if flip_points:
            start_points = wall_length - start_points
            end_points = wall_length - end_points

        return cpe, start_points, end_points

    @staticmethod
    def __roof_cpes(h_average, endwall_length, angle = NotImplemented, transversal_roof = False):
        h_d = h_average/endwall_length
        #Start points
        start_points = np.array([0, 0.5 * h_average, h_average, 2 * h_average, 3 * h_average])
        #For h/d <= 0.5, case a:
        cpe_case_1a = np.array([-0.9, -0.9, -0.5, -0.3, -0.2]) 
        cpe_case_2a = np.array([-0.4, -0.4, 0.0, 0.1, 0.2])
        #For h/d >= 1.0, case b:
        cpe_case_1b = np.array([-1.3, -0.7, -0.7, -0.7, -0.7]) 
        cpe_case_2b = np.array([-0.6, -0.3, -0.3, -0.3, -0.3])

        if h_d <= 0.5:
            cpe1 = cpe_case_1a
            cpe2 = cpe_case_2a
        elif h_d >= 1.0:
            cpe1 = cpe_case_1b
            cpe2 = cpe_case_2b
        else:
            #Interpolate between h/d == 0.5 and h/d == 1.0
            cpe1 = np.zeros(5)
            cpe2 = np.zeros(5)
            for i in range(5):
                cpe1[i] = np.interp(h_d, [0.5, 1], [cpe_case_1a[i], cpe_case_1b[i]]) 
                cpe2[i] = np.interp(h_d, [0.5, 1], [cpe_case_2a[i], cpe_case_2b[i]])

        if transversal_roof == False:
            #insert wall / 2 point
            if 3 * h_average > endwall_length / 2:
                #Find where to insert the middle point, and insert it
                index = np.where(start_points > endwall_length / 2)[0][0]
                start_points = np.insert(start_points, index, endwall_length / 2)
                cpe1 = np.insert(cpe1, index, cpe1[index - 1])
                cpe2 = np.insert(cpe2, index, cpe2[index - 1])
            else:
                start_points = np.hstack((start_points, endwall_length / 2))
                cpe1 = np.hstack((cpe1, cpe1[-1]))
                cpe2 = np.hstack((cpe2, cpe2[-1])) 

        return cpe1, cpe2, start_points


    @staticmethod
    def roof_windward(h_average, endwall_length, flip_start_points = False, angle = NotImplemented):
        #Define cpes
        cpe1, cpe2, start_points = CpeCoefficient.__roof_cpes(h_average, endwall_length, angle)
        #Define start and end points and limit the arrays to the endwall length / 2
        start_points = start_points[start_points <  endwall_length / 2]
        end_points = np.append(start_points[1:], endwall_length / 2)
        cpe1 = cpe1[0:len(start_points)]
        cpe2 = cpe2[0:len(start_points)]
        if flip_start_points:
            start_points = endwall_length - start_points
            end_points = endwall_length - end_points

        return cpe1, cpe2, start_points, end_points

    @staticmethod
    def roof_leeward(h_average, endwall_length, flip_points = False, angle = NotImplemented):
        #Define cpes
        cpe1, cpe2, start_points = CpeCoefficient.__roof_cpes(h_average, endwall_length, angle)
        #Define start and end points and limit the arrays between endwall leength / 2 and  endwall length
        start_points = np.hstack((start_points, endwall_length)) 
  
        index = np.where(np.logical_and(start_points >= endwall_length/2, start_points <  endwall_length))[0]
        start_points = start_points[index]
        cpe1 = cpe1[index]
        cpe2 = cpe2[index]
        end_points = np.append(start_points[1:], endwall_length)

        if flip_points:
            start_points = endwall_length - start_points
            end_points = endwall_length - end_points

        return cpe1, cpe2, start_points, end_points

    @staticmethod
    def roof_lateral(h_average, lateral_wall_length, flip_points = False, angle = NotImplemented):
        #Define cpes
        cpe1, cpe2, start_points = CpeCoefficient.__roof_cpes(h_average, lateral_wall_length, 0, True)
        
        #Define start and end points and limit the arrays to the lateral wall length
        start_points = start_points[start_points <  lateral_wall_length]
        end_points = np.append(start_points[1:], lateral_wall_length)
        cpe1 = cpe1[0:len(start_points)]
        cpe2 = cpe2[0:len(start_points)]

        if flip_points:
            start_points = lateral_wall_length - start_points
            end_points = lateral_wall_length - end_points


        return cpe1, cpe2, start_points, end_points

class AddWindLoads:

    def __init__(self, SapModel, qz1, qz2, cpi_x = 0.0, cpi_y = 0.0):
        self.qz1 = qz1 #Presion dinamica de base, kg/m2
        self.qz2 = qz2 #Presion dinamica de base cuando h>10, kg/m2
        self.SapModel = SapModel
        self.cpi_x = cpi_x #Coeficiente de presion interior en direccion X
        self.cpi_y = cpi_y #Coeficiente de presion interior en direccion Y
        self.a = 25.0#test_autoNave.a #Span
        self.h1 = 12.0#test_autoNave.h1  
        self.h2 = 2.0#test_autoNave.h2
        self.y = 40.0#np.max(test_autoNave.y)
        self.y_frames_positions = np.array([0., 8., 16., 24., 32., 40.])
        self.wind_columns_wall_A = np.array([self.a/4, 2*self.a/4, 3*self.a/4])
        self.wind_columns_wall_B = np.arange(self.a / 5, self.a, self.a / 5)
        self.h_average = self.h2/2 + self.h1
        self.alpha = math.atan(2 * self.h2 / self.a)
        self.apply_loads_to_purlins = False #if False, loads are applied to frames
        #Areas lists
        self.area_list_roof = [] #[Area_name]
        self.area_list_lateral_walls = [] #[Area_name]
        self.area_list_end_walls = [] #[Area_name]
        #All areas lists
        ret = SapModel.AreaObj.GetNameList(0, [])
        self.area_list_global = list(ret[1]) #Start the list with the existing areas
        cordinates = Geometry.get_areas_points_and_coordinates(self.SapModel, list(ret[1]))
        self.area_coordinates_global = cordinates[1]
        self.area_coordinates_sorted = cordinates[2]
        
        self.areas_names = []
        self.areas_locations = []
        self.areas_points = []

    def set_geometry(self, a, h1, h2, y, wind_columns_wall_A, wind_columns_wall_B,
    apply_loads_to_purlins = False):
        self.a = a #Span
        self.h1 = h1
        self.h2 = h2
        self.y_frames_positions = y 
        self.y = self.y_frames_positions[-1]
        self.wind_columns_wall_A = wind_columns_wall_A
        self.wind_columns_wall_B = wind_columns_wall_B
        self.alpha = math.atan(2 * h2 / a)
        self.apply_loads_to_purlins = apply_loads_to_purlins #if False, loads are applied to frames
        self.h_average = self.h2/2 + self.h1
        self.alpha = math.atan(2 * self.h2 / self.a)

    def add_area_to_list(self, area, area_list):
        """Adds area name to specified Area list and to global area list"""
        area_list.append(area)
        self.area_list_global.append(area)
        coordinates = Geometry.get_areas_points_and_coordinates(self.SapModel, [area])
        self.area_coordinates_global.append(coordinates[1][0])
        self.area_coordinates_sorted.append(coordinates[2][0])


    def get_existing_areas(self):
        """Returns a list of areas present in the model"""
        ret = self.SapModel.AreaObj.GetNameList(0, [])
        area_names = list(ret[1])
        return area_names

    def get_name_of_similar_existing_area(self, x, y, z, existing_areas = None, sorted_area_coordinates = None):
        """If an area with the same coordinates exists, return its name
        x, y, z = lists of coordinates of an area.
        existing_area = list of areas present in model"""

        time1 = time.time()

        if existing_areas == None:
            existing_areas = self.area_list_global
        if sorted_area_coordinates == None:
            area_coordinates = self.area_coordinates_sorted

        #Get points and coordinates
        #area_points, area_coordinates = Geometry.get_areas_points_and_coordinates(self.SapModel, existing_areas)
        #determine if x, y, z are present in the list of coordinates
        """
        #(), MIGHT WORK faster WITH np.where?
        for i in range(len(area_coordinates)):
            if (sorted(area_coordinates[i][0]) == x_sorted
            and sorted(area_coordinates[i][1]) == y_sorted
            and sorted(area_coordinates[i][2]) == z_sorted):
                index = i

        similar_area = existing_areas[index]
        """

        current_coordinates = np.array([x, y, z])
        current_coordinates = np.unique(current_coordinates, axis = 1)
        current_coordinates = np.sort(current_coordinates)
        
        
        """
        a = area_coordinates
        b = current_coordinates
        print("Existing areas = ", existing_areas)
        print("area coordnates =",area_coordinates)
        print("b =",b)
        c = np.array([np.isin(a[: , 0], b[0]), np.isin(a[: , 1], b[1]), np.isin(a[: , 2], b[2])])
        print("c =",c)
        c = np.all(c, axis = (2,0))
        #print("c all =",c)

        index = np.where(c == True)[0][0]
        """
        """
        #mask = np.isin(area_coordinates, current_coordinates, True)
        mask = np.isclose(np.sort(area_coordinates), np.sort(current_coordinates))
        index = np.where(np.all(mask, (1, 2)))[0][0]
        """
        #index = 0

        index = None
        for i in range(len(area_coordinates)):
            if current_coordinates.shape == area_coordinates[i].shape:
                mask = np.all(np.isclose(current_coordinates, area_coordinates[i]))
                if mask:
                    index = i
                    break

        # Fallback: if exact match failed, try looser tolerance
        if index is None:
            for i in range(len(area_coordinates)):
                if current_coordinates.shape == area_coordinates[i].shape:
                    mask = np.all(np.isclose(current_coordinates, area_coordinates[i], atol=1e-3))
                    if mask:
                        index = i
                        break

        # Last resort: match by checking all existing model areas directly
        if index is None:
            all_model_areas = self.get_existing_areas()
            for area_name in all_model_areas:
                try:
                    ret = self.SapModel.AreaObj.GetPoints(area_name, 0, [])
                    npts = ret[0]
                    pts = list(ret[1])
                    ax, ay, az = [], [], []
                    for pt in pts:
                        coord = self.SapModel.PointObj.GetCoordCartesian(pt, 0, 0, 0)
                        ax.append(coord[0]); ay.append(coord[1]); az.append(coord[2])
                    area_coords = np.array([ax, ay, az])
                    area_coords = np.unique(area_coords, axis=1)
                    area_coords = np.sort(area_coords)
                    if current_coordinates.shape == area_coords.shape:
                        if np.all(np.isclose(current_coordinates, area_coords, atol=1e-2)):
                            similar_area = area_name
                            time2 = time.time()
                            return similar_area
                except:
                    continue
            print(f"  [WARN] No matching area found for coordinates x={x}, y={y}, z={z}")
            similar_area = existing_areas[0]  # fallback to first area
            time2 = time.time()
            return similar_area

        similar_area = existing_areas[index]
       # print("similar area = ", similar_area)
        time2 = time.time()

        return similar_area



    def add_lateral_wall_panel(self, x_coord, y_start, y_end, z_start, z_end, revert_local_3 = False):
        x = [x_coord] * 4
        
        if revert_local_3:
            y_tmp = [y_start, y_end]
            y_start = y_tmp[1]
            y_end = y_tmp[0]

        y = [y_start, y_start, y_end, y_end]
        z = [z_start, z_end, z_end, z_start]        

        ret = self.SapModel.AreaObj.AddByCoord(4, x, y, z, "", "LoadPanel")
        area_name = ret[3]

        if ret[4] != 0:
            area_name = self.get_name_of_similar_existing_area(x, y, z)
            #TODO assert local axes is correct

        else:            
            if self.apply_loads_to_purlins == True:
                self.SapModel.AreaObj.SetLocalAxes(area_name, 90)
            #add areas to list if similar area does not exists
            self.add_area_to_list(area_name, self.area_list_end_walls)



        
        """
        #add areas to list if similar area does not exists, else, get similar area name
        area_location = [ret[0], ret[1], ret[2]]
        area_name = ret[3]
        if area_location in self.areas_locations:
            ret = self.areas_names[self.areas_locations.index(area_location)]
        else:
            self.areas_locations.append(area_location)
            self.areas_names.append(area_name)
            ret = ret[3]
        """

        return area_name

    def add_end_wall_panel(self, y_coord, x_start, x_end, z_start, z_end, revert_local_3 = False):
        number_of_points = 4

        if revert_local_3:
            x_tmp = [x_start, x_end]
            x_start = x_tmp[1]
            x_end = x_tmp[0]

        #is z > h1?, define z end
        if z_end > self.h1:
            z_end1 = get_z_from_x(x_start, self.a, self.h1, self.h2)
            z_end2 = get_z_from_x(x_end, self.a, self.h1, self.h2)
        else:       
            z_end1 = z_end #[z_start, z_start, z_end, self.h1 + self.h2, z_end]
            z_end2 = z_end
        #is panel in the middle and z_end > h1? , modify number of points in x and z
        if x_start < self.a / 2  and x_end > self.a / 2 and z_end > self.h1 or x_end < self.a / 2  and x_start > self.a / 2  and z_end > self.h1:
            number_of_points = 5
            x = [x_start, x_end, x_end, self.a / 2, x_start]
            z = [z_start, z_start, z_end2, self.h1 + self.h2, z_end1]
        else:
            x = [x_start, x_end, x_end, x_start]
            z = [z_start, z_start, z_end2, z_end1]
            
        y = [y_coord] * number_of_points
        ret = self.SapModel.AreaObj.AddByCoord(number_of_points, x, y, z, "", "LoadPanel")
        area_name = ret[3]

        if ret[4] != 0:
            area_name = self.get_name_of_similar_existing_area(x, y, z)
            #TODO assert local axes is correct

        else:            
            if self.apply_loads_to_purlins == True:
                self.SapModel.AreaObj.SetLocalAxes(area_name, 90)
            #add areas to list if similar area does not exists, else, get similar area name
            self.add_area_to_list(area_name, self.area_list_end_walls)

        return area_name

    def add_roof_panel(self, x_start, x_end, y_start, y_end, revert_local_3 = False):

        if revert_local_3:
            x_tmp = [x_start, x_end]
            x_start = x_tmp[1]
            x_end = x_tmp[0]

        x = [x_start, x_end, x_end, x_start]
        y = [y_start, y_start, y_end, y_end]
        z = get_z_from_x(x, self.a, self.h1, self.h2).tolist()

        ret = self.SapModel.AreaObj.AddByCoord(4, x, y, z, "", "LoadPanel")
        area_name = ret[3]

        if ret[4] != 0:
            area_name = self.get_name_of_similar_existing_area(x, y, z)
            #TODO assert local axes is correct

        else:            
            if self.apply_loads_to_purlins == True:
                self.SapModel.AreaObj.SetLocalAxes(area_name, 90)
            #add areas to list
            self.add_area_to_list(area_name, self.area_list_roof)


            
        """
        #add areas to list if similar area does not exists, else, get similar area name
        area_location = [ret[0], ret[1], ret[2]]
        area_name = ret[3]            

        if area_location in self.areas_locations:
            ret = self.areas_names[self.areas_locations.index(area_location)]
        else:
            self.areas_locations.append(area_location)
            self.areas_names.append(area_name)
            ret = ret[3]
        """

        return area_name

    #############################
    #Apply loads

    def add_lateral_wall_windward_load(self, load_pattern, positive_direction_load_pattern = True):
        x = 0
        cpe = 0.8
        ka = 1 #(TODO)
        kl = 1 #(TODO)
        cpi = self.cpi_x
        revert3 = True

        if positive_direction_load_pattern == False: 
            x = self.a
            revert3 = False

        #Add panel with z <= 10 m
        load_value = (cpe * ka * kl - cpi) * self.qz1        
        ret = self.add_lateral_wall_panel(x, 0, self.y, 0, min(self.h1, 10), revert3)
        self.SapModel.AreaObj.SetLoadUniform(ret, load_pattern, load_value, 3, False, "Local", 0)
        #Add panel with z > 10 m
        if self.h1 > 10:
            load_value = (cpe * ka * kl - cpi) * self.qz2        
            ret = self.add_lateral_wall_panel(x, 0, self.y, min(self.h1, 10), self.h1, revert3)
            self.SapModel.AreaObj.SetLoadUniform(ret, load_pattern, load_value, 3, False, "Local", 0)

        return load_value
        
    def add_lateral_wall_leeward_load(self, load_pattern, positive_direction_load_pattern = True):
        x = self.a
        ka = 1 #(TODO)
        kl = 1 #(TODO)
        cpi = self.cpi_x
        revert3 = False

        if positive_direction_load_pattern == False: 
            x = 0
            revert3 = True            
        d = self.a
        b = self.y
        cpe = CpeCoefficient.lateral_walls_leeward(d / b, self.alpha)
        
        #Add panel with z <= 10 m
        load_value = (cpe * ka * kl - cpi) * self.qz1        
        ret = self.add_lateral_wall_panel(x, 0, self.y, 0, min(self.h1, 10), revert3)
        self.SapModel.AreaObj.SetLoadUniform(ret, load_pattern, load_value, 3, False, "Local", 0)
        #Add panel with z > 10 m
        if self.h1 > 10:
            load_value = (cpe * ka * kl - cpi) * self.qz2        
            ret = self.add_lateral_wall_panel(x, 0, self.y, min(self.h1, 10), self.h1, revert3)
            self.SapModel.AreaObj.SetLoadUniform(ret, load_pattern, load_value, 3, False, "Local", 0)

        return load_value

    def add_lateral_wall_lateral_load(self, load_pattern, positive_direction_load_pattern = True):
    
        flip_points = not positive_direction_load_pattern
        revert3 = positive_direction_load_pattern
        cpe, start_points, end_points = CpeCoefficient.lateral_walls_lateral(self.h_average, self.y)
        cpe, cpe, start_points, end_points = CpeCoefficient.insert_frame_positions_into_cpes(self.y_frames_positions, start_points, end_points, cpe, cpe, self.y, flip_points)
        ka = 1 #(TODO)
        kl = 1 #(TODO)
        cpi = self.cpi_y

        load_value = (cpe * ka * kl - cpi) * self.qz1
        if self.h_average > 10:
            load_value = (cpe * ka * kl - cpi) * self.qz2
        for i in range (cpe.shape[0]):
            #Add panels
            if start_points[i] != end_points[i]:
                ret1 = self.add_lateral_wall_panel(0, start_points[i], end_points[i], 0, self.h1, revert3)
                ret2 = self.add_lateral_wall_panel(self.a, start_points[i], end_points[i], 0, self.h1, not revert3)
                self.SapModel.AreaObj.SetLoadUniform(ret1, load_pattern, load_value[i], 3, False, "Local", 0)
                self.SapModel.AreaObj.SetLoadUniform(ret2, load_pattern, load_value[i], 3, False, "Local", 0)
        
        
        return load_value


    def add_end_wall_windward_load(self, load_pattern, positive_direction_load_pattern = True):
        y = 0
        cpe = 0.8
        ka = 1 #(TODO)
        kl = 1 #(TODO)
        cpi = self.cpi_y

        revert3 = True

        if positive_direction_load_pattern == False: 
            y = self.y
            revert3 = False

        #Add panel with z <= 10 m
        load_value = (cpe * ka * kl - cpi) * self.qz1
        ret = self.add_end_wall_panel(y, 0, self.a, 0, self.h1, revert3)
        ret1 = self.SapModel.AreaObj.SetLoadUniform(ret, load_pattern, load_value, 3, False, "Local", 0)

        ret = self.add_end_wall_panel(y, 0, self.a / 2, self.h1, min(self.h1 + self.h2, 10), revert3)        
        ret1 = self.SapModel.AreaObj.SetLoadUniform(ret, load_pattern, load_value, 3, False, "Local", 0)

        ret = self.add_end_wall_panel(y, self.a / 2, self.a, self.h1, min(self.h1 + self.h2, 10), revert3)        
        ret1 = self.SapModel.AreaObj.SetLoadUniform(ret, load_pattern, load_value, 3, False, "Local", 0)


        #Add panel with z > 10 m
        if self.h1 > 10:
            load_value = (cpe * ka * kl - cpi) * self.qz2
            ret = self.add_end_wall_panel(y, 0, self.a, min(self.h1, 10), self.h1, revert3)         
            self.SapModel.AreaObj.SetLoadUniform(ret, load_pattern, load_value, 3, False, "Local", 0)
            ret = self.add_end_wall_panel(y, 0, self.a / 2, self.h1, self.h1 + self.h2, revert3)         
            self.SapModel.AreaObj.SetLoadUniform(ret, load_pattern, load_value, 3, False, "Local", 0)
            ret = self.add_end_wall_panel(y, self.a / 2, self.a, self.h1, self.h1 + self.h2, revert3)         
            self.SapModel.AreaObj.SetLoadUniform(ret, load_pattern, load_value, 3, False, "Local", 0)

        return load_value

    def add_end_wall_leeward_load(self, load_pattern, positive_direction_load_pattern = True):
        y = self.y
        ka = 1 #(TODO)
        kl = 1 #(TODO)
        cpi = self.cpi_y

        revert3 = False

        if positive_direction_load_pattern == False: 
            y = 0
            revert3 = True
        d = self.y
        b = self.a
        cpe = CpeCoefficient.end_walls_leeward(d / b)


        load_value = (cpe * ka * kl - cpi) * self.qz1
        if self.h_average > 10:
            load_value = (cpe * ka * kl - cpi) * self.qz2

        ret = self.add_end_wall_panel(y, 0, self.a, 0, self.h1, revert3)        
        ret1 = self.SapModel.AreaObj.SetLoadUniform(ret, load_pattern, load_value, 3, False, "Local", 0)

        ret = self.add_end_wall_panel(y, 0, self.a / 2, self.h1, self.h1 + self.h2, revert3)        
        ret1 = self.SapModel.AreaObj.SetLoadUniform(ret, load_pattern, load_value, 3, False, "Local", 0)

        ret = self.add_end_wall_panel(y, self.a / 2, self.a, self.h1, self.h1 + self.h2, revert3)        
        ret1 = self.SapModel.AreaObj.SetLoadUniform(ret, load_pattern, load_value, 3, False, "Local", 0)


        """
        #Add panel with z > 10 m
        if self.h1 > 10:
            ret = self.add_end_wall_panel(y, 0, self.a / 2, min(self.h1, 10), self.h1 + self.h2, revert3)         
            self.SapModel.AreaObj.SetLoadUniform(ret, load_pattern, load_value, 3, False, "Local", 0)
            ret = self.add_end_wall_panel(y, self.a / 2, self.a, min(self.h1, 10), self.h1 + self.h2, revert3)         
            self.SapModel.AreaObj.SetLoadUniform(ret, load_pattern, load_value, 3, False, "Local", 0)
        """
        return load_value

    def add_end_wall_lateral_load(self, load_pattern, positive_direction_load_pattern = True):
        #Does not work for panels on the slanted zone (h > h1) because, SAP2000 does not 
        #distribute loads correctlly. 
        #CORRECTED!, AVOID LOAD TRANSFER TO PURLINS IF APPLY LOADS TO PURLINS IS FALSE
        #AND AVOD LOAD TRANSFER TO COLUMNS IF APPLY LOADS TO PURLINS IS TRUE
        flip_points = not positive_direction_load_pattern
        revert3 = positive_direction_load_pattern
        cpe, start_points, end_points = CpeCoefficient.end_walls_lateral(self.h_average, self.a)
        ka = 1 #(TODO)
        kl = 1 #(TODO)
        cpi = self.cpi_x

        cpeA, cpeA, start_points_A, end_points_A = CpeCoefficient.insert_frame_positions_into_cpes(self.wind_columns_wall_A, start_points, end_points, cpe, cpe, self.a, flip_points)
        cpeB, cpeB, start_points_B, end_points_B = CpeCoefficient.insert_frame_positions_into_cpes(self.wind_columns_wall_B, start_points, end_points, cpe, cpe, self.a, flip_points)
        
        
        load_value_A = (cpeA * ka * kl - cpi) * self.qz1 #Save load value A
        if self.h_average > 10:
            load_value_A = (cpeA * ka * kl - cpi) * self.qz2 #Save load value A

        load_value = load_value_A #To use in the formulas

        for i in range (cpeA.shape[0]):
            if start_points_A[0] != end_points_A[0]:
                ret1 = self.add_end_wall_panel(self.y_frames_positions[0], start_points_A[i], end_points_A[i], 0, self.h1, revert3)
                self.SapModel.AreaObj.SetLoadUniform(ret1, load_pattern, load_value[i], 3, False, "Local", 0)
                ret1 = self.add_end_wall_panel(self.y_frames_positions[0], start_points_A[i], end_points_A[i], self.h1, self.h1 + self.h2, revert3)
                self.SapModel.AreaObj.SetLoadUniform(ret1, load_pattern, load_value[i], 3, False, "Local", 0)

        load_value_B = (cpeB * ka * kl - cpi) * self.qz1 #Save load value B
        if self.h_average > 10:
            load_value_B = (cpeB * ka * kl - cpi) * self.qz2 #Save load value B

        load_value = load_value_B #To use in the formulas

        for i in range (cpeB.shape[0]):
            if start_points_B[0] != end_points_B[0]:
                ret1 = self.add_end_wall_panel(self.y_frames_positions[-1], start_points_B[i], end_points_B[i], 0, self.h1, not revert3)
                self.SapModel.AreaObj.SetLoadUniform(ret1, load_pattern, load_value[i], 3, False, "Local", 0)
                ret1 = self.add_end_wall_panel(self.y_frames_positions[-1], start_points_B[i], end_points_B[i], self.h1, self.h1 + self.h2, not revert3)
                self.SapModel.AreaObj.SetLoadUniform(ret1, load_pattern, load_value[i], 3, False, "Local", 0)

        return load_value_A, load_value_B
        

    def add_roof_windward_load(self, load_pattern1, load_pattern2, positive_direction_load_pattern = True):
        """load_pattern1 = load pattern for case 1, load_pattern2 = load pattern for case 2"""
        flip_points = not positive_direction_load_pattern
        revert3 = positive_direction_load_pattern
        cpe1, cpe2, start_points, end_points = CpeCoefficient.roof_windward(self.h_average, self.a, flip_points)
        ka = 1 #(TODO)
        kl = 1 #(TODO)
        cpi = self.cpi_x

        #case 1 values, cpe1
        load_value1 = (cpe1 * ka * kl - cpi) * self.qz1
        #case 2 values, cpe2
        load_value2 = (cpe2 * ka * kl - cpi) * self.qz1
        if self.h_average > 10:
            load_value1 = (cpe1 * ka * kl - cpi) * self.qz2
            load_value2 = (cpe2 * ka * kl - cpi) * self.qz2

        #Add panels
        for i in range(cpe1.shape[0]):
            if start_points[i] != end_points[i]:
                #Model Panel    
                ret = self.add_roof_panel(start_points[i], end_points[i], 0, self.y, revert3)
                #Apply Load, Case 1
                self.SapModel.AreaObj.SetLoadUniform(ret, load_pattern1, load_value1[i], 3, False, "Local", 0)
                #Apply Load, Case 2
                self.SapModel.AreaObj.SetLoadUniform(ret, load_pattern2, load_value2[i], 3, False, "Local", 0)

        return load_value1, load_value2

    def add_roof_leeward_load(self, load_pattern1, load_pattern2, positive_direction_load_pattern = True):
        """load_pattern1 = load pattern for case 1, load_pattern2 = load pattern for case 2"""
        flip_start_points = not positive_direction_load_pattern
        revert3 = positive_direction_load_pattern
        cpe1, cpe2, start_points, end_points = CpeCoefficient.roof_leeward(self.h_average, self.a, flip_start_points)
        ka = 1 #(TODO)
        kl = 1 #(TODO)
        cpi = self.cpi_x

        #case 1 values, cpe1
        load_value1 = (cpe1 * ka * kl - cpi) * self.qz1
        #case 2 values, cpe2
        load_value2 = (cpe2 * ka * kl - cpi) * self.qz1
        if self.h_average > 10:
            load_value1 = (cpe1 * ka * kl - cpi) * self.qz2
            load_value2 = (cpe2 * ka * kl - cpi) * self.qz2

        #Add panels
        for i in range(cpe1.shape[0]):
            if start_points[i] != end_points[i]:
                #Model Panel
                ret = self.add_roof_panel(start_points[i], end_points[i], 0, self.y, revert3)
                #Apply Load, Case 1
                self.SapModel.AreaObj.SetLoadUniform(ret, load_pattern1, load_value1[i], 3, False, "Local", 0)
                #Apply Load, Case 2
                self.SapModel.AreaObj.SetLoadUniform(ret, load_pattern2, load_value2[i], 3, False, "Local", 0)

        return load_value1, load_value2

    def add_roof_lateral_load(self, load_pattern1, load_pattern2, positive_direction_load_pattern = True):
        """load_pattern1 = load pattern for case 1, load_pattern2 = load pattern for case 2"""

        flip_points = not positive_direction_load_pattern
        revert3 = positive_direction_load_pattern
        cpe1, cpe2, start_points, end_points = CpeCoefficient.roof_lateral(self.h_average, self.y)
        ka = 1 #(TODO)
        kl = 1 #(TODO)
        cpi = self.cpi_y

        cpe1, cpe2, start_points, end_points = CpeCoefficient.insert_frame_positions_into_cpes(self.y_frames_positions, start_points, end_points, cpe1, cpe2, self.y, flip_points)

        #case 1 values, cpe1
        load_value1 = (cpe1 * ka * kl - cpi) * self.qz1
        #case 2 values, cpe2
        load_value2 = (cpe2 * ka * kl - cpi) * self.qz1
        if self.h_average > 10:
            load_value1 = (cpe1 * ka * kl - cpi) * self.qz2
            load_value2 = (cpe2 * ka * kl - cpi) * self.qz2

        #Add panels
        for i in range(cpe1.shape[0]):
            if start_points[i] != end_points[i]:
                #Model Panel
                ret1 = self.add_roof_panel(0, self.a/2, start_points[i], end_points[i], revert3)
                ret2 = self.add_roof_panel(self.a/2, self.a, start_points[i], end_points[i], revert3)
                #Apply Load, Case 1
                ret3 = self.SapModel.AreaObj.SetLoadUniform(ret1, load_pattern1, load_value1[i], 3, False, "Local", 0)
                ret4 = self.SapModel.AreaObj.SetLoadUniform(ret2, load_pattern1, load_value1[i], 3, False, "Local", 0)
                #Apply Load, Case 2
                ret5 = self.SapModel.AreaObj.SetLoadUniform(ret1, load_pattern2, load_value2[i], 3, False, "Local", 0)
                ret6 = self.SapModel.AreaObj.SetLoadUniform(ret2, load_pattern2, load_value2[i], 3, False, "Local", 0)


        return load_value1, load_value2

"""
#MODEL
print("Starting sapobject from CFEWindLoads")
SapObject = comtypes.client.GetActiveObject("CSI.SAP2000.API.SapObject")
SapModel = SapObject.SapModel

print("Start to apply loads")
w1 = AddWindLoads(SapModel, 100, 200)
w1.h1 = 5
w1.h_average = w1.h2/2 + w1.h1


w1.add_roof_lateral_load("WIND_Y1+", "WIND_Y2+")





SapModel.View.RefreshView()
"""


