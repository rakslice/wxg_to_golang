import xml.dom.minidom

import sys

from class_definition_classes import WxContainer, WxObjectClass
from codegen import golang_str_repr, GenStruct, GenFile
from xml_helpers import child_elements, child_element_text


def const_convert(s):
    """Convert a wxg const value to the golang expression for the relevant constant"""
    if s.startswith("wx") and s[2:].isupper():
        return "wx.%s" % s[2:]
    else:
        assert False, "can't convert const %r" % s


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


BOX_SIZER = WxContainer("wxBoxSizer", "EditBoxSizer", "wx.BoxSizer", "wx.NewBoxSizer",
                        "%s", [("orient", const_convert)],
                        "sizeritem",
                        "%s, %s, %s", [("option", int), ("flag", const_convert, "0"), ("border", int)],
                        constructor_needs_parent=False
                        )
LABEL = WxObjectClass("wxStaticText", "EditStaticText", "wx.StaticText", "wx.NewStaticText",
                      "wx.ID_ANY, %s", [("label", golang_str_repr, '""')])
LIST_BOX = WxObjectClass("wxListBox", "EditListBox", "wx.ListBox", "wx.NewListBox",
                         "wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, []string {}"
                         )
LIST_BOX.add_property("tooltip", "ToolTip", golang_str_repr)

STATIC_BITMAP = WxObjectClass(wxg_name="wxStaticBitmap", base_name="EditStaticBitmap", wx_class_name="wx.StaticBitmap",
                              constructor_name="wx.NewStaticBitmap", constructor_params_form="wx.ID_ANY, wx.NullBitmap")


STATIC_BITMAP.add_property("size", "MinSize", make_size_expr)
IGNORE_OBJECTS = ["EditSpacer", "EditButton", STATIC_BITMAP.base_name]

OBJECTS = [
    BOX_SIZER,
    LABEL,
    LIST_BOX,
    STATIC_BITMAP,
]
""":type: list of WxObject"""


def convert(input_filename, output_filename):
    with open(output_filename, "w") as output_handle:
        dom = xml.dom.minidom.parse(input_filename)

        out = GenFile()

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
                    st.add_property_line(None, "Size", size_expr)

                bgcolor = child_element_text(form, "background", None)
                if bgcolor is not None:
                    color_obj_expr = colour_obj_for_web_colour(bgcolor)
                    st.add_property_line(None, "BackgroundColour", color_obj_expr)

                item_pops = [(obj, form_struct_field_name) for obj in child_elements(form, "object")]

                need_sizer = True

                while len(item_pops) > 0:
                    obj, parent_field_name = item_pops.pop(0)

                    object_base = obj.getAttribute("base")
                    if object_base in IGNORE_OBJECTS:
                        pass
                    elif object_base in wx_object_classes_map:
                        member_class_obj = wx_object_classes_map[object_base]
                        assert isinstance(member_class_obj, WxObjectClass)

                        member_name = obj.getAttribute("name")
                        if need_sizer:
                            st.sizer_field_name = member_name
                            need_sizer = False

                        st.members.append((member_name, member_class_obj.wx_class_name))

                        built_additional_params = build_additional_params(member_class_obj.constructor_params_form,
                                                                          member_class_obj.properties_for_constructor, obj)
                        st.add_init_line(member_name, member_class_obj.constructor_name, built_additional_params,
                                         member_class_obj.constructor_needs_parent)

                        for tag_name, (go_property_name, value_func) in member_class_obj.properties.iteritems():
                            value = child_element_text(obj, tag_name, None)
                            if value is not None:
                                if value_func is not None:
                                    value = value_func(value)
                                st.add_property_line(member_name, go_property_name, value)

                        if isinstance(member_class_obj, WxContainer):
                            for subobject in child_elements(obj, "object"):
                                subobject_class = subobject.getAttribute("class")
                                assert subobject_class == subobject_class

                                sizer_item_children = list(child_elements(subobject, "object"))
                                assert len(sizer_item_children) == 1
                                item_child = sizer_item_children[0]

                                ic_base = item_child.getAttribute("base")
                                if ic_base in IGNORE_OBJECTS:
                                    continue

                                item_child_name = item_child.getAttribute("name")
                                item_pops.append((item_child, member_name))

                                additional_params = build_additional_params(member_class_obj.subobject_constructor_params_form,
                                                                            member_class_obj.subobject_properties_for_constructor,
                                                                            subobject)
                                # if parent_field_name == form_struct_field_name:
                                #     continue

                                st.layout_lines.append((member_name, item_child_name, additional_params))

                    else:
                        assert False, "Unknown base " + object_base

        out.code_gen(output_handle)


def colour_obj_for_web_colour(color_str):
    assert color_str.startswith("#") and len(color_str) == 7
    color_str = color_str[1:]
    rgb = [int(color_str[i:i + 2], 16) for i in (0, 2, 4)]
    color_obj_expr = "wx.NewColour(%s)" % ", ".join(["byte(%d)" % x for x in rgb])
    return color_obj_expr


def build_additional_params(constructor_params_form, properties_for_constructor, dom_obj):
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
                msg = "During conversion of %s class=%s %s value %r, got converted value %r" % (dom_obj.nodeName, dom_obj.getAttribute("class"), property_name,
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
