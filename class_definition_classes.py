from xml_helpers import element_text, get_path_elements


class WxObjectClass(object):
    def __init__(self, wxg_name, base_name, wx_class_name, constructor_name, constructor_params_form=None, properties_for_constructor=None,
                 constructor_needs_parent=True):
        """
        Contains the definition of a WX object class.
        :param wxg_name: The class name as it will appear in the wxg object tag's class attribute. Not really used ATM?
        None is not normally allowed, it is a placeholder indicating the value may vary for different instances of the tag
        :type wxg_name: str or None
        :param base_name: The value of the wxg object tag's base attribute.
        :type base_name: str
        :param wx_class_name: The wxGo class to use for this class; should include the package prefix if one is required.
        None is not normally allowed, it is a placeholder indicating the value may vary for different instances of the tag.
        :type wx_class_name: str or None
        :param constructor_name: The wxGo function to use to construct an object instance; should include the package prefix if
        one is required. None is not normally allowed, it is a placeholder indicating the value may vary for different instances of the tag
        :type constructor_name: str or None
        :param constructor_params_form: what should go between the parens in the constructor call; this is a
         golang format string (https://golang.org/pkg/fmt/) that will be Sprintf'd with values from
         properties_for_constructor if any
        :type constructor_params_form: str
        :param properties_for_constructor: What properties to get from the wxg xml and use as constructor parameters; this
        is a list of entries in the form of (name, conversion function[, default value]).  Normally we treat name as the name
        of a tag inside the object tag, but if it starts with "@" we look for an attribute on the object tag by that name, and the
        conversion function takes the text in the tag or attribute and converts it to a form to use in with the constructor format
        string; often this is a golang string representation to put in a plain %s.
        For the special name values "DOM_OBJECT" (or "DOM_CHILD_OBJECT") we pass the conversion function the whole DOM object for the
        object tag (or the tags of the objects it contains), instead of text, which allows putting together a property value
        from the XML in an arbitrarily complex way.
        :type properties_for_constructor: None or list[(str, function) or (str, function, str)]
        """
        self._cur_obj = None
        self._wxg_name = wxg_name
        self.base_name = base_name
        self._wx_class_name = wx_class_name
        self._constructor_name = constructor_name
        self.constructor_needs_parent = constructor_needs_parent
        self.properties = {}
        if properties_for_constructor is None:
            properties_for_constructor = []
        if not isinstance(properties_for_constructor, list) and not isinstance(properties_for_constructor, tuple):
            raise TypeError("properties_for_constructor must be list, tuple, or None")
        self.constructor_params_form = constructor_params_form
        self.properties_for_constructor = properties_for_constructor

    @property
    def wxg_name(self):
        assert self._wxg_name is not None
        return self._wxg_name

    @property
    def wx_class_name(self):
        assert self._wx_class_name is not None
        return self._wx_class_name

    @property
    def constructor_name(self):
        assert self._constructor_name is not None
        return self._constructor_name

    def add_property(self, tag_name, go_property_name, value_func=None, go_property_set_prefix="Set"):
        assert tag_name not in self.properties
        self.properties[tag_name] = (go_property_set_prefix + go_property_name, value_func)

    def setup_for_dom_obj(self, obj):
        """:type obj: xml.dom.minidom.Element"""
        assert self._cur_obj is None
        self._cur_obj = obj

    def teardown_for_dom_obj(self, obj):
        """:type obj: xml.dom.minidom.Element"""
        assert self._cur_obj == obj
        self._cur_obj = None


class WxContainer(WxObjectClass):
    """
    Contains information about a WX container class
    """
    def __init__(self, wxg_name, base_name, wx_class_name, constructor_name, constructor_params_form, properties_for_constructor,
                 subobject_wxg_name, subobject_constructor_params_form=None, subobject_properties_for_constructor=None,
                 add_method_name="Add", use_as_parent_object_for_enclosed_objects=False, expect_one_child=True,
                 **kwargs):
        super(WxContainer, self).__init__(wxg_name, base_name, wx_class_name, constructor_name, constructor_params_form, properties_for_constructor,
                                          **kwargs)
        self.subobject_wxg_name = subobject_wxg_name
        self.subobject_fields = {}
        self.subobject_constructor_params_form = subobject_constructor_params_form
        self.subobject_properties_for_constructor = subobject_properties_for_constructor
        self.add_method_name = add_method_name
        self.use_as_parent_object_for_enclosed_objects = use_as_parent_object_for_enclosed_objects
        self.expect_one_child = expect_one_child

    def add_subobject_field(self, tag_name, property_name, value_func=None):
        assert tag_name not in self.subobject_fields
        self.subobject_fields[tag_name] = (property_name, value_func)


class WxCustomWidget(WxObjectClass):
    def __init__(self):
        super(WxCustomWidget, self).__init__(None, "CustomWidget", None, None)

    def setup_for_dom_obj(self, obj):
        """:type obj: xml.dom.minidom.Element"""
        super(WxCustomWidget, self).setup_for_dom_obj(obj)

        # init the class-name-based properties
        file_class_name = obj.getAttribute("class")
        self.init_class_name_for_custom_class(file_class_name)

        # init the constructor param list based properties
        argument_placeholders = []
        for argument_obj in get_path_elements(obj, "arguments/argument"):
            argument_placeholders.append(element_text(argument_obj))

        takes_parent_param = False
        if len(argument_placeholders) >= 1 and argument_placeholders[0] == "$parent":
            takes_parent_param = True
            argument_placeholders = argument_placeholders[1:]
            assert "$parent" not in argument_placeholders

        constructor_params_form_parts = list(argument_placeholders)
        constructor_properties = []

        for i, param in enumerate(argument_placeholders):
            if param == "$id":
                constructor_params_form_parts[i] = "wx.ID_ANY"

        self.init_constructor_params_for_custom_class(", ".join(constructor_params_form_parts), constructor_properties, takes_parent_param)

    def init_class_name_for_custom_class(self, file_class_name):
        # let's assume that the custom class will always exist inside the same package
        # and that the caller can always wrap it if necessary
        self._wxg_name = file_class_name
        self._wx_class_name = file_class_name
        self._constructor_name = "New%s" % file_class_name

    def init_constructor_params_for_custom_class(self, constructor_params_form, properties_for_constructor,
                                                 constructor_needs_parent):
        self.constructor_params_form = constructor_params_form
        self.properties_for_constructor = properties_for_constructor
        self.constructor_needs_parent = constructor_needs_parent
