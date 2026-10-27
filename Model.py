import os
import sys
import comtypes.client
import constants
import numpy as np

load_patterns = ['DEAD', 'LIVE', 'WIND_X1+', 'WIND_Y1+', 'WIND_X1-', 'WIND_Y1-', 'WIND_X2+', 'WIND_Y2+',
                'WIND_X2-', 'WIND_Y2-', 'Q_STAT_X+', 'Q_STAT_Y+', 'Q_STAT_X-', 'Q_STAT_Y-']

ltypes = ['LTYPE_DEAD', 'LTYPE_LIVE', 'LTYPE_WIND', 'LTYPE_WIND', 'LTYPE_WIND', 'LTYPE_WIND',
 'LTYPE_WIND', 'LTYPE_WIND', 'LTYPE_WIND', 'LTYPE_WIND', 'LTYPE_QUAKE', 'LTYPE_QUAKE', 'LTYPE_QUAKE', 'LTYPE_QUAKE']

class ModelObject:
    def __init__(self, units = 8, software = "ETABS"):
        """
        Initialize connection to ETABS (default) or SAP2000.
        software: "ETABS" or "SAP2000"
        """
        self.software = software

        if software == "ETABS":
            active_prog_id = "CSI.ETABS.API.ETABSObject"
            helper_prog_id = "ETABSv1.Helper"
            helper_interface_module = "ETABSv1"
            create_prog_id = "CSI.ETABS.API.ETABSObject"
            file_extension = ".edb"
        else:
            active_prog_id = "CSI.SAP2000.API.SapObject"
            helper_prog_id = "SAP2000v1.Helper"
            helper_interface_module = "SAP2000v1"
            create_prog_id = "CSI.SAP2000.API.SapObject"
            file_extension = ".sdb"

        self.file_extension = file_extension

        if software == "ETABS":
            try:
                #try to attach to a running ETABS instance (proven pattern)
                print("Trying to attach to a running ETABS instance")
                helper = comtypes.client.CreateObject('ETABSv1.Helper')
                AppObject = helper.GetObject("CSI.ETABS.API.ETABSObject")
                print(AppObject)
                SapModel = AppObject.SapModel
            except Exception:
                #if no running instance, create new instance
                print("No ETABS instance running, Opening ETABS")
                helper = comtypes.client.CreateObject('ETABSv1.Helper')
                AppObject = helper.CreateObject("CSI.ETABS.API.ETABSObject")
                AppObject.ApplicationStart()
                SapModel = AppObject.SapModel
        else:
            try:
                #try to attach to a running SAP2000 instance
                print("Trying to attach to a running SAP2000 instance")
                AppObject = comtypes.client.GetActiveObject(active_prog_id)
                print(AppObject)
                SapModel = AppObject.SapModel
            except OSError:
                #if no running instance, create new instance
                print("No SAP2000 instance running, Opening SAP2000")
                helper = comtypes.client.CreateObject(helper_prog_id)
                helper = helper.QueryInterface(getattr(comtypes.gen, helper_interface_module).cHelper)
                AppObject = helper.CreateObjectProgID(create_prog_id)
                AppObject.ApplicationStart()
                SapModel = AppObject.SapModel

        self.sap_object = AppObject
        self.sap_model = SapModel


    def initialize_new_model(self, units = 8):
        """Initialize a new model with kgf_m_C units as default"""
        #initialize model
        self.sap_model.InitializeNewModel(units)
        #New blank model
        self.sap_model.File.NewBlank()
        #Create groups
        self.create_groups()
        #Add load patterns
        self.add_load_patterns()
        #Add combos
        self.add_linear_combinations()
        #Create thin slab section for ETABS area load panels
        if self.software == "ETABS":
            self._create_load_panel_section()

    def save(self, filename=""):
        """
        If a file name is specified, it should have the correct extension
        (.edb for ETABS, .sdb for SAP2000). If no file name is specified
        the file is saved using its current name.
        """
        with self.sap_model.File:
            return_value = self.sap_model.File.Save(filename)
            assert return_value == 0        # Ensure that everything went as expected

    def refreshview(self, window = 0, zoom = False):
        '''
        This functions updates the display so it is much faster
        than refreshwindow())
        '''
        return_value = self.sap_model.View.RefreshView(window, zoom)

    def lock_model(self):
        self.sap_model.SetModelIsLocked(False)

    def _create_load_panel_section(self):
        """Create a thin slab section for ETABS load panels.
        ETABS needs areas to have a section for SetLoadUniform to work.
        Stiffness modifiers are set to near-zero so the panel doesn't
        attract load or add stiffness to the model."""
        sm = self.sap_model
        # Create a thin slab: SetSlab(Name, SlabType=0, ShellType=1(thin), MatProp, Thickness)
        # Use ETABS default material "4000Psi" (always exists in new blank model)
        sm.PropArea.SetSlab("LoadPanel", 0, 1, "4000Psi", 0.001)
        # Set stiffness modifiers to near-zero [f11, f22, f12, m11, m22, m12, v13, v23, mass, weight]
        sm.PropArea.SetModifiers("LoadPanel", [0.001]*10)

    def create_groups(self):
        """Create groups"""
        groups = ["Main_Columns", "Haunched_Columns", "Main_Beams", "Haunched_Beams", "Haunched_Beams_Central",
        "Main_Columns_end", "Haunched_Columns_end", "Main_Beams_end", "Haunched_Beams_end", "Haunched_Beams_Central_end",
        "Interior_Columns", "Wind_Columns", "Purlins_Roof", "Purlins_Lateral", "Purlins_end", "Bracing_Vertical",
        "Bracing_Vertical_compression", "Bracing_Horizontal", "Areas_Roof_Gravity", "Areas_Roof_Wind", "Areas_Lateral",
        "Areas_End"]


        for i in groups:
            self.sap_model.GroupDef.SetGroup(i)

    def add_load_patterns(self):
        #Add Load patterns x1+, x2+, x1-, x2-, x1+, x2+, x1-, x2-,
        for i in range(len(load_patterns)):
            self_multiplyer = 0
            if ltypes[i] == 'LTYPE_DEAD':
                self_multiplyer = 1
            self.sap_model.LoadPatterns.Add(load_patterns[i], constants.LOAD_PATTERN_TYPES[ltypes[i]], self_multiplyer, True)

    def add_linear_combinations(self):
        #Load combinations
        #[Name, Short_name, Loads, Values]
        #SD = steel deflection
        #SS = steel strength
        combos = np.array([
        ["D", "SD-01", ['DEAD'], [1.0]],
        ["D + L", "SD-02", ['DEAD', 'LIVE'], [1.0, 1.0]],
        ["1.4D", "SS-01.1", ['DEAD'], [1.4]],
        ["1.2D + 1.6L", "SS-01.2", ['DEAD', 'LIVE'], [1.2, 1.6]],
        ["1.2D + 0.5L + WX1+", "SS-02.1", ['DEAD', 'LIVE', 'WIND_X1+'], [1.2, 0.5, 1]],
        ["1.2D + 0.5L + WX2+", "SS-02.2", ['DEAD', 'LIVE', 'WIND_X2+'], [1.2, 0.5, 1]],
        ["1.2D + 0.5L + WX1-", "SS-02.3", ['DEAD', 'LIVE', 'WIND_X1-'], [1.2, 0.5, 1]],
        ["1.2D + 0.5L + WX2-", "SS-02.4", ['DEAD', 'LIVE', 'WIND_X2-'], [1.2, 0.5, 1]],
        ["1.2D + 0.5L + WY1+", "SS-02.5", ['DEAD', 'LIVE', 'WIND_Y1+'], [1.2, 0.5, 1]],
        ["1.2D + 0.5L + WY2+", "SS-02.6", ['DEAD', 'LIVE', 'WIND_Y2+'], [1.2, 0.5, 1]],
        ["1.2D + 0.5L + WY1-", "SS-02.7", ['DEAD', 'LIVE', 'WIND_Y1-'], [1.2, 0.5, 1]],
        ["1.2D + 0.5L + WY2-", "SS-02.8", ['DEAD', 'LIVE', 'WIND_Y2-'], [1.2, 0.5, 1]],


        ["0.9D + WX1+", "SS-03.1", ['DEAD', 'WIND_X1+'], [0.9, 1]],
        ["0.9D + WX2+", "SS-03.2", ['DEAD', 'WIND_X2+'], [0.9, 1]],
        ["0.9D + WX1-", "SS-03.3", ['DEAD', 'WIND_X1-'], [0.9, 1]],
        ["0.9D + WX2-", "SS-03.4", ['DEAD', 'WIND_X2-'], [0.9, 1]],
        ["0.9D + WY1+", "SS-03.5", ['DEAD', 'WIND_Y1+'], [0.9, 1]],
        ["0.9D + WY2+", "SS-03.6", ['DEAD', 'WIND_Y2+'], [0.9, 1]],
        ["0.9D + WY1-", "SS-03.7", ['DEAD', 'WIND_Y1-'], [0.9, 1]],
        ["0.9D + WY2-", "SS-03.8", ['DEAD', 'WIND_Y2-'], [0.9, 1]],


        ["1.2D + 0.5L + QX+ + 0.3QY+", "SS-04.01", ['DEAD', 'LIVE', 'Q_STAT_X+', 'Q_STAT_Y+'], [1.2, 0.5, 1, 0.3]],
        ["1.2D + 0.5L + QX+ - 0.3QY+", "SS-04.02", ['DEAD', 'LIVE', 'Q_STAT_X+', 'Q_STAT_Y+'], [1.2, 0.5, 1, -0.3]],
        ["1.2D + 0.5L - QX+ + 0.3QY+", "SS-04.03", ['DEAD', 'LIVE', 'Q_STAT_X+', 'Q_STAT_Y+'], [1.2, 0.5, -1, 0.3]],
        ["1.2D + 0.5L - QX+ - 0.3QY+", "SS-04.04", ['DEAD', 'LIVE', 'Q_STAT_X+', 'Q_STAT_Y+'], [1.2, 0.5, -1, -0.3]],

        ["1.2D + 0.5L + 0.3QX+ + QY+", "SS-04.05", ['DEAD', 'LIVE', 'Q_STAT_X+', 'Q_STAT_Y+'], [1.2, 0.5, 0.3, 1]],
        ["1.2D + 0.5L + 0.3QX+ - QY+", "SS-04.06", ['DEAD', 'LIVE', 'Q_STAT_X+', 'Q_STAT_Y+'], [1.2, 0.5, 0.3, -1]],
        ["1.2D + 0.5L - 0.3QX+ + QY+", "SS-04.07", ['DEAD', 'LIVE', 'Q_STAT_X+', 'Q_STAT_Y+'], [1.2, 0.5, -0.3, 1]],
        ["1.2D + 0.5L - 0.3QX+ - QY+", "SS-04.08", ['DEAD', 'LIVE', 'Q_STAT_X+', 'Q_STAT_Y+'], [1.2, 0.5, -0.3, -1]],

        ["1.2D + 0.5L + QX- + 0.3QY+", "SS-04.09", ['DEAD', 'LIVE', 'Q_STAT_X-', 'Q_STAT_Y+'], [1.2, 0.5, 1, 0.3]],
        ["1.2D + 0.5L + QX- - 0.3QY+", "SS-04.10", ['DEAD', 'LIVE', 'Q_STAT_X-', 'Q_STAT_Y+'], [1.2, 0.5, 1, -0.3]],
        ["1.2D + 0.5L - QX- + 0.3QY+", "SS-04.11", ['DEAD', 'LIVE', 'Q_STAT_X-', 'Q_STAT_Y+'], [1.2, 0.5, -1, 0.3]],
        ["1.2D + 0.5L - QX- - 0.3QY+", "SS-04.12", ['DEAD', 'LIVE', 'Q_STAT_X-', 'Q_STAT_Y+'], [1.2, 0.5, -1, -0.3]],

        ["1.2D + 0.5L + 0.3QX- + QY+", "SS-04.13", ['DEAD', 'LIVE', 'Q_STAT_X-', 'Q_STAT_Y+'], [1.2, 0.5, 0.3, 1]],
        ["1.2D + 0.5L + 0.3QX- - QY+", "SS-04.14", ['DEAD', 'LIVE', 'Q_STAT_X-', 'Q_STAT_Y+'], [1.2, 0.5, 0.3, -1]],
        ["1.2D + 0.5L - 0.3QX- + QY+", "SS-04.15", ['DEAD', 'LIVE', 'Q_STAT_X-', 'Q_STAT_Y+'], [1.2, 0.5, -0.3, 1]],
        ["1.2D + 0.5L - 0.3QX- - QY+", "SS-04.16", ['DEAD', 'LIVE', 'Q_STAT_X-', 'Q_STAT_Y+'], [1.2, 0.5, -0.3, -1]],

        ["1.2D + 0.5L + QX+ + 0.3QY-", "SS-04.17", ['DEAD', 'LIVE', 'Q_STAT_X+', 'Q_STAT_Y-'], [1.2, 0.5, 1, 0.3]],
        ["1.2D + 0.5L + QX+ - 0.3QY-", "SS-04.18", ['DEAD', 'LIVE', 'Q_STAT_X+', 'Q_STAT_Y-'], [1.2, 0.5, 1, -0.3]],
        ["1.2D + 0.5L - QX+ + 0.3QY-", "SS-04.19", ['DEAD', 'LIVE', 'Q_STAT_X+', 'Q_STAT_Y-'], [1.2, 0.5, -1, 0.3]],
        ["1.2D + 0.5L - QX+ - 0.3QY-", "SS-04.20", ['DEAD', 'LIVE', 'Q_STAT_X+', 'Q_STAT_Y-'], [1.2, 0.5, -1, -0.3]],

        ["1.2D + 0.5L + 0.3QX+ + QY-", "SS-04.21", ['DEAD', 'LIVE', 'Q_STAT_X+', 'Q_STAT_Y-'], [1.2, 0.5, 0.3, 1]],
        ["1.2D + 0.5L + 0.3QX+ - QY-", "SS-04.22", ['DEAD', 'LIVE', 'Q_STAT_X+', 'Q_STAT_Y-'], [1.2, 0.5, 0.3, -1]],
        ["1.2D + 0.5L - 0.3QX+ + QY-", "SS-04.23", ['DEAD', 'LIVE', 'Q_STAT_X+', 'Q_STAT_Y-'], [1.2, 0.5, -0.3, 1]],
        ["1.2D + 0.5L - 0.3QX+ - QY-", "SS-04.24", ['DEAD', 'LIVE', 'Q_STAT_X+', 'Q_STAT_Y-'], [1.2, 0.5, -0.3, -1]],

        ["1.2D + 0.5L + QX- + 0.3QY-", "SS-04.25", ['DEAD', 'LIVE', 'Q_STAT_X-', 'Q_STAT_Y-'], [1.2, 0.5, 1, 0.3]],
        ["1.2D + 0.5L + QX- - 0.3QY-", "SS-04.26", ['DEAD', 'LIVE', 'Q_STAT_X-', 'Q_STAT_Y-'], [1.2, 0.5, 1, -0.3]],
        ["1.2D + 0.5L - QX- + 0.3QY-", "SS-04.27", ['DEAD', 'LIVE', 'Q_STAT_X-', 'Q_STAT_Y-'], [1.2, 0.5, -1, 0.3]],
        ["1.2D + 0.5L - QX- - 0.3QY-", "SS-04.28", ['DEAD', 'LIVE', 'Q_STAT_X-', 'Q_STAT_Y-'], [1.2, 0.5, -1, -0.3]],

        ["1.2D + 0.5L + 0.3QX- + QY-", "SS-04.29", ['DEAD', 'LIVE', 'Q_STAT_X-', 'Q_STAT_Y-'], [1.2, 0.5, 0.3, 1]],
        ["1.2D + 0.5L + 0.3QX- - QY-", "SS-04.30", ['DEAD', 'LIVE', 'Q_STAT_X-', 'Q_STAT_Y-'], [1.2, 0.5, 0.3, -1]],
        ["1.2D + 0.5L - 0.3QX- + QY-", "SS-04.31", ['DEAD', 'LIVE', 'Q_STAT_X-', 'Q_STAT_Y-'], [1.2, 0.5, -0.3, 1]],
        ["1.2D + 0.5L - 0.3QX- - QY-", "SS-04.32", ['DEAD', 'LIVE', 'Q_STAT_X-', 'Q_STAT_Y-'], [1.2, 0.5, -0.3, -1]],


        ["0.8D + QX+ + 0.3QY+", "SS-05.01", ['DEAD', 'Q_STAT_X+', 'Q_STAT_Y+'], [0.8, 1, 0.3]],
        ["0.8D + QX+ - 0.3QY+", "SS-05.02", ['DEAD', 'Q_STAT_X+', 'Q_STAT_Y+'], [0.8, 1, -0.3]],
        ["0.8D - QX+ + 0.3QY+", "SS-05.03", ['DEAD', 'Q_STAT_X+', 'Q_STAT_Y+'], [0.8, -1, 0.3]],
        ["0.8D - QX+ - 0.3QY+", "SS-05.04", ['DEAD', 'Q_STAT_X+', 'Q_STAT_Y+'], [0.8, -1, -0.3]],

        ["0.8D + 0.3QX+ + QY+", "SS-05.05", ['DEAD', 'Q_STAT_X+', 'Q_STAT_Y+'], [0.8, 0.3, 1]],
        ["0.8D + 0.3QX+ - QY+", "SS-05.06", ['DEAD', 'Q_STAT_X+', 'Q_STAT_Y+'], [0.8, 0.3, -1]],
        ["0.8D - 0.3QX+ + QY+", "SS-05.07", ['DEAD', 'Q_STAT_X+', 'Q_STAT_Y+'], [0.8, -0.3, 1]],
        ["0.8D - 0.3QX+ - QY+", "SS-05.08", ['DEAD', 'Q_STAT_X+', 'Q_STAT_Y+'], [0.8, -0.3, -1]],

        ["0.8D + QX- + 0.3QY+", "SS-05.09", ['DEAD', 'Q_STAT_X-', 'Q_STAT_Y+'], [0.8, 1, 0.3]],
        ["0.8D + QX- - 0.3QY+", "SS-05.10", ['DEAD', 'Q_STAT_X-', 'Q_STAT_Y+'], [0.8, 1, -0.3]],
        ["0.8D - QX- + 0.3QY+", "SS-05.11", ['DEAD', 'Q_STAT_X-', 'Q_STAT_Y+'], [0.8, -1, 0.3]],
        ["0.8D - QX- - 0.3QY+", "SS-05.12", ['DEAD', 'Q_STAT_X-', 'Q_STAT_Y+'], [0.8, -1, -0.3]],

        ["0.8D + 0.3QX- + QY+", "SS-05.13", ['DEAD', 'Q_STAT_X-', 'Q_STAT_Y+'], [0.8, 0.3, 1]],
        ["0.8D + 0.3QX- - QY+", "SS-05.14", ['DEAD', 'Q_STAT_X-', 'Q_STAT_Y+'], [0.8, 0.3, -1]],
        ["0.8D - 0.3QX- + QY+", "SS-05.15", ['DEAD', 'Q_STAT_X-', 'Q_STAT_Y+'], [0.8, -0.3, 1]],
        ["0.8D - 0.3QX- - QY+", "SS-05.16", ['DEAD', 'Q_STAT_X-', 'Q_STAT_Y+'], [0.8, -0.3, -1]],

        ["0.8D + QX+ + 0.3QY-", "SS-05.17", ['DEAD', 'Q_STAT_X+', 'Q_STAT_Y-'], [0.8, 1, 0.3]],
        ["0.8D + QX+ - 0.3QY-", "SS-05.18", ['DEAD', 'Q_STAT_X+', 'Q_STAT_Y-'], [0.8, 1, -0.3]],
        ["0.8D - QX+ + 0.3QY-", "SS-05.19", ['DEAD', 'Q_STAT_X+', 'Q_STAT_Y-'], [0.8, -1, 0.3]],
        ["0.8D - QX+ - 0.3QY-", "SS-05.20", ['DEAD', 'Q_STAT_X+', 'Q_STAT_Y-'], [0.8, -1, -0.3]],

        ["0.8D + 0.3QX+ + QY-", "SS-05.21", ['DEAD', 'Q_STAT_X+', 'Q_STAT_Y-'], [0.8, 0.3, 1]],
        ["0.8D + 0.3QX+ - QY-", "SS-05.22", ['DEAD', 'Q_STAT_X+', 'Q_STAT_Y-'], [0.8, 0.3, -1]],
        ["0.8D - 0.3QX+ + QY-", "SS-05.23", ['DEAD', 'Q_STAT_X+', 'Q_STAT_Y-'], [0.8, -0.3, 1]],
        ["0.8D - 0.3QX+ - QY-", "SS-05.24", ['DEAD', 'Q_STAT_X+', 'Q_STAT_Y-'], [0.8, -0.3, -1]],

        ["0.8D + QX- + 0.3QY-", "SS-05.25", ['DEAD', 'Q_STAT_X-', 'Q_STAT_Y-'], [0.8, 1, 0.3]],
        ["0.8D + QX- - 0.3QY-", "SS-05.26", ['DEAD', 'Q_STAT_X-', 'Q_STAT_Y-'], [0.8, 1, -0.3]],
        ["0.8D - QX- + 0.3QY-", "SS-05.27", ['DEAD', 'Q_STAT_X-', 'Q_STAT_Y-'], [0.8, -1, 0.3]],
        ["0.8D - QX- - 0.3QY-", "SS-05.28", ['DEAD', 'Q_STAT_X-', 'Q_STAT_Y-'], [0.8, -1, -0.3]],

        ["0.8D + 0.3QX- + QY-", "SS-05.29", ['DEAD', 'Q_STAT_X-', 'Q_STAT_Y-'], [0.8, 0.3, 1]],
        ["0.8D + 0.3QX- - QY-", "SS-05.30", ['DEAD', 'Q_STAT_X-', 'Q_STAT_Y-'], [0.8, 0.3, -1]],
        ["0.8D - 0.3QX- + QY-", "SS-05.31", ['DEAD', 'Q_STAT_X-', 'Q_STAT_Y-'], [0.8, -0.3, 1]],
        ["0.8D - 0.3QX- - QY-", "SS-05.32", ['DEAD', 'Q_STAT_X-', 'Q_STAT_Y-'], [0.8, -0.3, -1]],

        ], dtype=object)

        #DEFINE COMBOS
        #define combo names
        self.combo_names = combos[:, 1]
        self.design_combo_names = combos[:, 1][2:]
        self.deflection_combo_names = combos[:, 1][:2]

        #Linear combos
        vfunc = np.vectorize(self.sap_model.RespCombo.Add)(self.combo_names, 0)
        ###################NonLinear combos
        ####################vfunc = np.vectorize(self.sap_model.LoadCases.StaticNonlinear.SetCase)("NL-" + self.combo_names)
        #add cases to combos
        for i in combos:
            name = i[1]
            self.sap_model.LoadCases.StaticNonlinear.SetLoads("NL-" + name, len(i[2]), ["Load"] * len(i[2]), i[2], i[3])
            for j in range(len(i[2])):
                self.sap_model.RespCombo.SetCaseList(name, 0, i[2][j], i[3][j])

