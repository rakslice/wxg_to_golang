
class WxObjectClass(object):
    def __init__(self, wxg_name, base_name, wx_class_name, constructor_name, constructor_params_form=None, properties_for_constructor=None,
                 constructor_needs_parent=True):
        """
        Contains information about a WX object class
        :type wxg_name: str
        :type constructor_params_form: str
        :type properties_for_constructor: None or list[(str, function)] or list[(str, function, str)]
        """
        self.wxg_name = wxg_name
        self.base_name = base_name
        self.wx_class_name = wx_class_name
        self.constructor_name = constructor_name
        self.constructor_needs_parent = constructor_needs_parent
        self.properties = {}
        if properties_for_constructor is None:
            properties_for_constructor = []
        if not isinstance(properties_for_constructor, list) and not isinstance(properties_for_constructor, tuple):
            raise TypeError("properties_for_constructor must be list, tuple, or None")
        self.constructor_params_form = constructor_params_form
        self.properties_for_constructor = properties_for_constructor

    def add_property(self, tag_name, go_property_name, value_func=None):
        assert tag_name not in self.properties
        self.properties[tag_name] = (go_property_name, value_func)


class WxContainer(WxObjectClass):
    """
    Contains information about a WX container class
    """
    def __init__(self, wxg_name, base_name, wx_class_name, constructor_name, constructor_params_form, properties_for_constructor,
                 subobject_wxg_name, subobject_constructor_params_form=None, subobject_properties_for_constructor=None,
                 **kwargs):
        super(WxContainer, self).__init__(wxg_name, base_name, wx_class_name, constructor_name, constructor_params_form, properties_for_constructor,
                                          **kwargs)
        self.subobject_wxg_name = subobject_wxg_name
        self.subobject_fields = {}
        self.subobject_constructor_params_form = subobject_constructor_params_form
        self.subobject_properties_for_constructor = subobject_properties_for_constructor

    def add_subobject_field(self, tag_name, property_name, value_func=None):
        assert tag_name not in self.subobject_fields
        self.subobject_fields[tag_name] = (property_name, value_func)
