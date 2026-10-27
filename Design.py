
import os
import sys
import comtypes.client
import Model
import Geometry
import numpy as np
import math
import Profiles
import time


#SapObject = comtypes.client.GetActiveObject("CSI.SAP2000.API.SapObject")
#SapModel = SapObject.SapModel

def run_analysis_and_design(SapModel):
    #Unluck model
    SapModel.SetModelIsLocked(False)

    print("Analyzing")
    ret = SapModel.Analyze.RunAnalysis()
    print(ret)

    print("Start design")
    ret = SapModel.DesignSteel.StartDesign()
    print(ret)

    print("Verify design vs analysis sections")
    ret = SapModel.DesignSteel.VerifySections(0, [])
    print(ret)

    return ret



def get_heavier_section_in_group(SapModel, group_name):
    elements = SapModel.GroupDef.GetAssignments(group_name, 0, [], [])
    sections = []
    areas = []

    print('elements:')
    print(elements)

    for i in elements[2]:
        #section = SapModel.FrameObj.GetSection(i, "", "")
        section = SapModel.DesignSteel.GetDesignSection(i, "")
        print('section = ', section)
        area = SapModel.PropFrame.GetSectProps(section[0], 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)[1] #FIXME does not retrieve all the sections
        areas.append(area)
        sections.append(section[0])
    try:
        max_area_index = areas.index(max(areas))
        heavier_section = sections[max_area_index]
        return heavier_section
    except:
        print("Empty group")
        return None

def get_heavier_section_in_list(SapModel, elements_list):
    elements = elements_list
    sections = []
    areas = []

    for i in elements:
        area = SapModel.PropFrame.GetSectProps(i, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)[1]
        areas.append(area)
        sections.append(i)

    max_area_index = areas.index(max(areas))
    heavier_section = sections[max_area_index]

    return heavier_section


"""    
groups = ["Main_Columns", "Haunched_Columns", "Main_Beams", "Haunched_Beams", "Haunched_Beams_Central",
"Main_Columns_end", "Haunched_Columns_end", "Main_Beams_end", "Haunched_Beams_end", "Haunched_Beams_Central_end",
 "Wind_Columns", "Purlins_Roof", "Purlins_Lateral", "Purlins_end", "Bracing_Vertical", "Bracing_Horizontal",
 "Areas_Roof_Gravity", "Areas_Roof_Wind", "Areas_Lateral", "Areas_End"]
"""
 
def assign_optimized_sections_to_main_frames(SapModel): 
    #Unlock model
    SapModel.SetModelIsLocked(False)
    
    #Get heavier section from the main frames
    heavier_beams_list = []
    h1 = get_heavier_section_in_group(SapModel, "Main_Beams")    
    h2 = get_heavier_section_in_group(SapModel, "Haunched_Beams") 
    h3 = get_heavier_section_in_group(SapModel, "Haunched_Beams_Central")
    if h1 != None : heavier_beams_list.append(h1)
    if h2 != None : heavier_beams_list.append(h2.replace("HAUNCHED-", ""))
    if h3 != None : heavier_beams_list.append(h3.replace("HAUNCHED-", "")) 
    print("heavier beams list: ", heavier_beams_list)
    #Columns
    c1 = get_heavier_section_in_group(SapModel, "Main_Columns")
    c2 = get_heavier_section_in_group(SapModel, "Haunched_Columns")

    #Get heavier section
    heavier_beam = get_heavier_section_in_list(SapModel, heavier_beams_list)
    heavier_column = c1
    if c2 != None : # make haunched part of column the main propfile
        heavier_column = c2.replace("HAUNCHED-", "")

    print("heavier beam: ", heavier_beam)
    print("heavier column: ", heavier_column)

    #Assign optimized sections to main frames
    #Beams
    ret = SapModel.FrameObj.SetSection("Main_Beams", heavier_beam, 1)
    assert ret == 0, "Could not assign sections"
    ret = SapModel.FrameObj.SetSection("Haunched_Beams", "NP-" + heavier_beam, 1)
    assert ret == 0, "Could not assign sections"
    ret = SapModel.FrameObj.SetSection("Haunched_Beams_Central", "NP-" + heavier_beam, 1)
    assert ret == 0, "Could not assign sections"
    #Columns
    ret = SapModel.FrameObj.SetSection("Main_Columns", heavier_column, 1)
    assert ret == 0, "Could not assign sections"
    ret = SapModel.FrameObj.SetSection("Haunched_Columns", "NP-" + heavier_column, 1)
    assert ret == 0, "Could not assign sections"

def assign_optimized_sections_to_end_frames(SapModel): 
    #Unlock model
    SapModel.SetModelIsLocked(False)
    
    #Get heavier section from the main frames
    heavier_beams_list = []
    h1 = get_heavier_section_in_group(SapModel, "Main_Beams_end")
    h2 = get_heavier_section_in_group(SapModel, "Haunched_Beams_end")
    h3 = get_heavier_section_in_group(SapModel, "Haunched_Beams_Central_end")
    if h1 != None : heavier_beams_list.append(h1)
    if h2 != None : heavier_beams_list.append(h2.replace("HAUNCHED-", ""))
    if h3 != None : heavier_beams_list.append(h3.replace("HAUNCHED-", ""))
    print("heavier beams list: ", heavier_beams_list)

    #Columns
    c1 = get_heavier_section_in_group(SapModel, "Main_Columns_end")
    c2 = get_heavier_section_in_group(SapModel, "Haunched_Columns_end")

    #Get heavier section
    heavier_beam = get_heavier_section_in_list(SapModel, heavier_beams_list)
    heavier_column = c1
    if c2 != None : # make haunched part of column the main propfile
        heavier_column = c2.replace("HAUNCHED-", "")
    
    print("heavier beam: ", heavier_beam)
    print("heavier column: ", heavier_column)

        #Assign optimized sections to main frames
    #Beams
    ret = SapModel.FrameObj.SetSection("Main_Beams_end", heavier_beam, 1)
    assert ret == 0, "Could not assign sections"
    ret = SapModel.FrameObj.SetSection("Haunched_Beams_end", "NP-" + heavier_beam, 1)
    assert ret == 0, "Could not assign sections"
    ret = SapModel.FrameObj.SetSection("Haunched_Beams_Central_end", "NP-" + heavier_beam, 1)
    assert ret == 0, "Could not assign sections"
    #Columns
    ret = SapModel.FrameObj.SetSection("Main_Columns_end", heavier_column, 1)
    assert ret == 0, "Could not assign sections"
    ret = SapModel.FrameObj.SetSection("Haunched_Columns_end", "NP-" + heavier_column, 1)
    assert ret == 0, "Could not assign sections"


    

########------------------------------------------------------------------------------



def design_frames(SapModel, max_iterations = 10, framing_design_type = 3):
    """1 = Framing type
            0 = Program Default
            1 = SMF
            2 = IMF
            3 = OMF
            4 = SCB
            5 = OCBF
            6 = OCBFI
            7 = EBF
"""
    time_a = time.time()

    #Set code 
    SapModel.DesignSteel.SetCode("AISC 360-16")
    #and OMF frame
    try:
        SapModel.DesignSteel.AISC360_16.SetPreference(1, framing_design_type)
    except AttributeError:
        try:
            SapModel.DesignSteel.AISC360_05_IBC2006.SetPreference(1, framing_design_type)
        except Exception:
            print("  [WARN] Could not set AISC framing design preference")

    #Start design
    number_of_design_vs_analysis = run_analysis_and_design(SapModel)[0]
    
    i = 0
    while number_of_design_vs_analysis > 0 and i < max_iterations:
        print("Iteration No. ", i)
        number_of_design_vs_analysis = run_analysis_and_design(SapModel)[0]
        i += 1


    print("Assigning optimized sections to Main Frames")
    assign_optimized_sections_to_main_frames(SapModel)
    print("Assigning optimized sections to End Frames")
    assign_optimized_sections_to_end_frames(SapModel)


    run_analysis_and_design(SapModel)

    print(SapModel.DesignSteel.VerifyPassed(0, 0, 0, []))
    #TODO make auto select section null to all other sections

    time_b = time.time()
    print("Total time = ", time_b - time_a)