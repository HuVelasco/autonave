import constants

class Apply:

    @staticmethod
    def to_area_group(sap_model, group_name, load_pattern, value):
        # ETABS: SetLoadUniformToFrame causes GUI error dialogs. Use SetLoadUniform only.
        sap_model.AreaObj.SetLoadUniform(group_name, load_pattern, value, 10, True, "Global", 1)

    @staticmethod
    def to_area_object(sap_model, object_name, load_pattern, value):
        sap_model.AreaObj.SetLoadUniform(object_name, load_pattern, value, 10, True, "Global", 0)
