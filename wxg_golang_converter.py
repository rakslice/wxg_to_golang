import functools
import xml.dom.minidom
import sys
import datetime
import operator

from class_definition_classes import WxContainer, WxObjectClass, WxCustomWidget
from codegen import golang_str_repr, GenStruct, GenFile, golang_int
from xml_helpers import child_elements, child_element_text, element_text, get_path_elements


def const_convert(s):
    """Convert a wxg const value to the golang expression for the relevant constant"""
    if s.startswith("wx") and s[2:].isupper():
        return "wx.%s" % s[2:]
    else:
        assert False, "can't convert const %r" % s


def compose(*functions):
    # https://mathieularose.com/function-composition-in-python/
    return functools.reduce(lambda f, g: lambda x: f(g(x)), functions, lambda x: x)


def create_dict_from_list(l, key_property_name):
    """
    :type l: list[x]
    :type key_property_name: str
    :rtype: Dict[str, x]
    """
    out = {}
    for entry in l:
        key = getattr(entry, key_property_name)
        out[key] = entry
    return out


def make_size_expr(size_str):
    values = [int(x.strip()) for x in size_str.split(",")]
    size_expr = "wx.NewSize(%d, %d)" % tuple(values)
    return size_expr


def golang_bool_repr(x):
    if x:
        return "true"
    else:
        return "false"


class LookupTagText(object):
    """ A value converter that looks up values in a lookup table somewhere in the DOM """
    def __init__(self, subobject_property_name, tag_path, attr_name, converter):
        self.subobject_property_name = subobject_property_name
        self.tag_path = tag_path
        self.attr_name = attr_name
        self.converter = converter

    def __call__(self, dom_obj):
        """:type dom_obj: xml.dom.minidom.Element"""
        if self.subobject_property_name.startswith("@"):
            match_value = dom_obj.getAttribute(self.subobject_property_name[1:])
        else:
            match_value = child_element_text(dom_obj, self.subobject_property_name)

        for child_element in get_path_elements(dom_obj, self.tag_path):
            assert isinstance(child_element, xml.dom.minidom.Element)
            if child_element.getAttribute(self.attr_name) == match_value:
                return self.converter(element_text(child_element))

        return None


BOX_SIZER = WxContainer("wxBoxSizer", "EditBoxSizer", "wx.BoxSizer", "wx.NewBoxSizer",
                        "%s", [("orient", const_convert)],
                        "sizeritem",
                        "%s, %s, %s", [("option", int), ("flag", const_convert, "0"), ("border", int)],
                        constructor_needs_parent=False
                        )

PANEL = WxContainer("wxPanel", "EditPanel", "wx.Panel", "wx.NewPanel",
                    "wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, %s", [("style", const_convert)], None,
                    add_method_name="SetSizer",
                    use_as_parent_object_for_enclosed_objects=True,
                    )

NOTEBOOK = WxContainer("wxNotebook", "EditNotebook", "wx.Notebook", "wx.NewNotebook",
                       "wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, %s, %s", [("style", golang_int, 0), ("@name", golang_str_repr)],
                       subobject_wxg_name=None,
                       expect_one_child=False, add_method_name="AddPage",
                       subobject_constructor_params_form="%s",
                       subobject_properties_for_constructor=[("DOM_CHILD_OBJECT", LookupTagText("@name", "../tabs/tab", "window", golang_str_repr))],
                       use_as_parent_object_for_enclosed_objects=True,
                       )

CUSTOMWIDGET = WxCustomWidget()

LABEL = WxObjectClass("wxStaticText", "EditStaticText", "wx.StaticText", "wx.NewStaticText",
                      "wx.ID_ANY, %s", [("label", golang_str_repr, '""')])
LIST_BOX = WxObjectClass("wxListBox", "EditListBox", "wx.ListBox", "wx.NewListBox",
                         "wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, []string {}"
                         )
LIST_BOX.add_property("tooltip", "ToolTip", golang_str_repr)

STATIC_BITMAP = WxObjectClass(wxg_name="wxStaticBitmap", base_name="EditStaticBitmap", wx_class_name="wx.StaticBitmap",
                              constructor_name="wx.NewStaticBitmap", constructor_params_form="wx.ID_ANY, wx.NullBitmap")

BUTTON = WxObjectClass(wxg_name="wxButton", base_name="EditButton", wx_class_name="wx.Button",
                       constructor_name="wx.NewButton",
                       constructor_params_form="wx.ID_ANY, %s, wx.DefaultPosition, wx.DefaultSize, 0, wx.DefaultValidator, %s",
                       properties_for_constructor=[("label", golang_str_repr), ("label", golang_str_repr)],
                       )

BUTTON.add_property("disabled", "Enable", compose(golang_bool_repr, operator.not_, int), go_property_set_prefix="")

"""_init__(self, Window parent, int id=-1, String label=EmptyString,
            Point pos=DefaultPosition, Size size=DefaultSize,
            long style=0, Validator validator=DefaultValidator,
            String name=ButtonNameStr) -> Button
"""

STATIC_BITMAP.add_property("size", "MinSize", make_size_expr)
IGNORE_OBJECTS = []  # STATIC_BITMAP.base_name

OBJECTS = [
    PANEL,
    BOX_SIZER,
    LABEL,
    LIST_BOX,
    STATIC_BITMAP,
    BUTTON,
    NOTEBOOK,
    CUSTOMWIDGET
]
""":type: list of WxObject"""


def convert(input_filename, output_filename, package_name, wxgo_package_name):

    generation_comments = ["Generated by wxg_to_golang at %s" % datetime.datetime.now(),
                           "from %s" % input_filename,
                           ]

    with open(output_filename, "w") as output_handle:
        dom = xml.dom.minidom.parse(input_filename)

        out = GenFile(generation_comments, wxgo_package_name)

        # form_class_map = {"EditFrame": "wx.Frame"}

        appnodes = list(child_elements(dom, "application"))
        assert len(appnodes) == 1
        application = appnodes[0]

        wx_object_classes_map = create_dict_from_list(OBJECTS, "base_name")

        for form in child_elements(application, "object"):
            form_base = form.getAttribute("base")
            if form_base == "EditFrame":
                form_classname = "wx.Frame"
                form_constructor = "wx.NewFrame"
                form_struct_field_name = form_classname.rsplit(".", 1)[-1]
                st = GenStruct(form.getAttribute("class"), form_classname, form_constructor, form_struct_field_name, child_element_text(form, "title"))
                out.structs.append(st)

                size = child_element_text(form, "size", None)
                if size is not None:
                    size_expr = make_size_expr(size)
                    st.add_property_line(None, "SetSize", size_expr)

                bgcolor = child_element_text(form, "background", None)
                if bgcolor is not None:
                    color_obj_expr = colour_obj_for_web_colour(bgcolor)
                    st.add_property_line(None, "SetBackgroundColour", color_obj_expr)

                item_pops = [(obj, form_struct_field_name, None) for obj in child_elements(form, "object")]

                need_sizer = True

                while len(item_pops) > 0:
                    obj, parent_field_name, parent_object_name = item_pops.pop(0)

                    object_base = obj.getAttribute("base")
                    if object_base in IGNORE_OBJECTS:
                        pass
                    elif object_base in wx_object_classes_map:
                        member_class_obj = wx_object_classes_map[object_base]
                        assert isinstance(member_class_obj, WxObjectClass)

                        member_class_obj.setup_for_dom_obj(obj)

                        member_name = obj.getAttribute("name")
                        if need_sizer:
                            st.sizer_field_name = member_name
                            need_sizer = False

                        st.members.append((member_name, member_class_obj.wx_class_name))

                        built_additional_params = build_additional_params(member_class_obj.constructor_params_form,
                                                                          member_class_obj.properties_for_constructor, obj, None)
                        st.add_init_line(member_name, member_class_obj.constructor_name, built_additional_params,
                                         member_class_obj.constructor_needs_parent, parent_object_name=parent_object_name)

                        for tag_name, (go_property_name, value_func) in member_class_obj.properties.iteritems():
                            value = child_element_text(obj, tag_name, None)
                            if value is not None:
                                if value_func is not None:
                                    value = value_func(value)
                                st.add_property_line(member_name, go_property_name, value)

                        # add any event handlers

                        for event_tag in child_elements(obj, "events"):
                            for handler_tag in child_elements(event_tag, "handler"):
                                event = handler_tag.getAttribute("event")
                                callback = element_text(handler_tag)
                                st.add_binding(callback, event, member_name)

                        # handle containers (enqueuing any contained objects)

                        if isinstance(member_class_obj, WxContainer):
                            if member_class_obj.use_as_parent_object_for_enclosed_objects:
                                # use this object as a member object name for
                                parent_object_name = member_name

                            if member_class_obj.subobject_wxg_name is None:
                                # this container has a single enclosed object directly inside
                                subobjects = [obj]
                            else:
                                # this container has an object wrapper around each enclosed object
                                subobjects = child_elements(obj, "object")

                            for subobject in subobjects:
                                subobject_class = subobject.getAttribute("class")
                                if member_class_obj.subobject_wxg_name is not None:
                                    assert subobject_class == member_class_obj.subobject_wxg_name

                                sizer_item_children = list(child_elements(subobject, "object"))
                                if member_class_obj.expect_one_child:
                                    assert len(sizer_item_children) == 1, "expected %r object to have exactly one child" % subobject_class
                                for item_child in sizer_item_children:

                                    ic_base = item_child.getAttribute("base")

                                    if ic_base == "EditSpacer":
                                        is_horiz = obj.getAttribute("orient") == "wxHORIZONTAL"

                                        if is_horiz:
                                            height = int(child_element_text(item_child, "height"))
                                            spacer_size = height
                                        else:
                                            width = int(child_element_text(item_child, "width"))
                                            spacer_size = width

                                        # additional_params = build_additional_params(member_class_obj.subobject_constructor_params_form,
                                        #                                             member_class_obj.subobject_properties_for_constructor,
                                        #                                             subobject)

                                        proportion = int(child_element_text(subobject, "option", 0))

                                        if proportion == 0:
                                            st.add_layout_line(member_name, "%d" % spacer_size, None, False,
                                                               method="AddSpacer")
                                        else:
                                            st.add_layout_line(member_name, "%d" % proportion, None, False,
                                                               method="AddStretchSpacer")
                                        continue

                                    elif ic_base in IGNORE_OBJECTS:
                                        continue

                                    item_child_name = item_child.getAttribute("name")
                                    item_pops.append((item_child, member_name, parent_object_name))

                                    additional_params = build_additional_params(member_class_obj.subobject_constructor_params_form,
                                                                                member_class_obj.subobject_properties_for_constructor,
                                                                                subobject, item_child)
                                    # if parent_field_name == form_struct_field_name:
                                    #     continue

                                    st.add_layout_line(member_name, item_child_name, additional_params, method=member_class_obj.add_method_name)

                        member_class_obj.teardown_for_dom_obj(obj)

                    else:
                        assert False, "Unknown base %s; did you remember to add its definition to the OBJECTS list?" % object_base

        out.code_gen(output_handle, package_name)


def colour_obj_for_web_colour(color_str):
    assert color_str.startswith("#") and len(color_str) == 7
    color_str = color_str[1:]
    rgb = [int(color_str[i:i + 2], 16) for i in (0, 2, 4)]
    color_obj_expr = "wx.NewColour(%s)" % ", ".join(["byte(%d)" % x for x in rgb])
    return color_obj_expr


def build_additional_params(constructor_params_form, properties_for_constructor, dom_obj, item_child):
    if constructor_params_form is None:
        built_additional_params = None
    else:
        constructor_param_values = []
        for properties_entry in properties_for_constructor:
            if len(properties_entry) == 2:
                property_name, convert_func = properties_entry
                default_value = ""
            elif len(properties_entry) == 3:
                property_name, convert_func, default_value = properties_entry
            else:
                assert False, "invalid properties_for_constructor entry %r" % properties_entry
            if property_name == "DOM_OBJECT":
                pre_conversion_value = dom_obj
            elif property_name == "DOM_CHILD_OBJECT":
                pre_conversion_value = item_child
            elif property_name.startswith("@"):
                pre_conversion_value = dom_obj.getAttribute(property_name[1:])
            else:
                pre_conversion_value = child_element_text(dom_obj, property_name, None)
            if pre_conversion_value is None:
                converted_value = default_value
            else:
                try:
                    converted_value = convert_func(pre_conversion_value)
                except:
                    print "During conversion of %s class=%s %s value %r:" % (dom_obj.nodeName, dom_obj.getAttribute("class"), property_name, pre_conversion_value)
                    raise
            if converted_value is None or converted_value == "":
                msg = "During conversion of %s class=%s property '%s' value %r, got converted value %r" % (dom_obj.nodeName,
                                                                                                           dom_obj.getAttribute("class"),
                                                                                                           property_name,
                                                                                                           pre_conversion_value,
                                                                                                           converted_value)
                assert False, msg
            constructor_param_values.append(converted_value)
        if len(constructor_param_values) == 1:
            constructor_param_values = constructor_param_values[0]
        else:
            constructor_param_values = tuple(constructor_param_values)
        try:
            built_additional_params = constructor_params_form % constructor_param_values
        except TypeError:
            print >> sys.stderr, "Got"
            print >> sys.stderr, repr(constructor_params_form)
            print >> sys.stderr, repr(constructor_param_values)
            raise
    return built_additional_params
