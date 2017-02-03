
class GenStruct(object):
    def __init__(self, name, base_class, constructor, self_field_name, title):
        self.init_lines = []
        self.name = name
        self.base_class = base_class
        self.constructor = constructor
        self.self_field_name = self_field_name
        self.title = title
        self.sizer_field_name = None
        """:type: str"""

        self.members = []
        self.layout_lines = []

        self.properties_lines = []

        self.bindings = []

    def add_init_line(self, member_name, constructor, additional_params_expressions, takes_parent, parent_object_name=None):
        self.init_lines.append((member_name, constructor, additional_params_expressions, takes_parent, parent_object_name))

    def add_property_line(self, field_name, property_name, additional_params_expressions):
        self.properties_lines.append((field_name, property_name, additional_params_expressions))

    def add_layout_line(self, parent_field_name, cur_field_name, additional_params_expressions, obj_in_struct=True, method="Add"):
        self.layout_lines.append((parent_field_name, cur_field_name, additional_params_expressions, obj_in_struct, method))

    def add_binding(self, event_handler, event_id, field_to_bind):
        self.bindings.append((event_handler, event_id, field_to_bind))


def golang_str_repr(s):
    # FIXME implement a fully compliant golang string representation
    return '"%s"' % s.replace('"', r'\"').replace('\\', '\\\\')


class GenFile(object):
    """Main code generation class"""

    def __init__(self, generation_comments, wxgo_package_name):
        self.structs = []
        """:type: list of GenStruct"""
        self.generation_comments = generation_comments
        self.wxgo_package_name = wxgo_package_name

    def code_gen(self, output_handle, package_name):
        """Generate a golang source code file for the structs this object has been populated with"""
        print >> output_handle, "package %s" % package_name

        print >> output_handle, ""

        for comment in self.generation_comments:
            print >> output_handle, "// %s" % comment

        print >> output_handle, ""

        print >> output_handle, "import ("
        print >> output_handle, '\t"%s/wx"' % self.wxgo_package_name
        print >> output_handle, ")"

        print >> output_handle, ""

        for struct in self.structs:
            print >> output_handle, "type %s struct {" % struct.name
            print >> output_handle, "\t%s" % struct.base_class
            for name, typename in struct.members:
                print >> output_handle, "\t%s %s" % (name, typename)
            print >> output_handle, "}"
            print >> output_handle, ""

            events_struct_name = "%sEvents" % struct.name

            # interface for bindings
            print >> output_handle, "type %s interface {" % events_struct_name
            for event_handler, event_id, field_to_bind in struct.bindings:
                print >> output_handle, "\t%s(e wx.Event)" % event_handler
            print >> output_handle, "}"

            print >> output_handle, ""

            # init function
            print >> output_handle, "func init%s(eventInterface %s) *%s {" % (struct.name, events_struct_name, struct.name)
            print >> output_handle, "\tout := &%s{}" % struct.name
            print >> output_handle, "\tout.%s = %s(wx.NullWindow, wx.ID_ANY, %s)" % (struct.self_field_name, struct.constructor, golang_str_repr(struct.title))

            for member_name, constructor, additional_params_expressions, takes_parent, parent_object_name in struct.init_lines:
                param_fragments = []
                if takes_parent:
                    if parent_object_name is not None:
                        parent_name = "out.%s" % parent_object_name
                    else:
                        parent_name = "out"
                    param_fragments.append(parent_name)
                if additional_params_expressions is not None:
                    param_fragments.append(additional_params_expressions)
                init_line = "out.%s = %s(%s)" % (member_name, constructor, ", ".join(param_fragments))
                print >> output_handle, "\t%s" % init_line

            print >> output_handle, "\t"
            print >> output_handle, "\tout.set_properties()"
            print >> output_handle, "\tout.do_layout()"
            print >> output_handle, "\t"

            # bindings
            for event_handler, event_id, field_to_bind in struct.bindings:
                print >> output_handle, "\twx.Bind(out, wx.%s, eventInterface.%s, out.%s.GetId())" % (event_id, event_handler, field_to_bind)

            print >> output_handle, "\t"
            print >> output_handle, "\treturn out"
            print >> output_handle, "}"
            print >> output_handle, ""

            # layout method
            print >> output_handle, "func (out %s) do_layout() {" % struct.name
            for parent_field_name, cur_field_name, additional_params_expressions, obj_in_struct, method in struct.layout_lines:
                # assert layout_line.endswith(";")
                if obj_in_struct:
                    cur_field_name = "out.%s" % cur_field_name
                if additional_params_expressions is None:
                    layout_line = "out.%s.%s(%s)" % (parent_field_name, method, cur_field_name)
                else:
                    layout_line = "out.%s.%s(%s, %s)" % (parent_field_name, method, cur_field_name, additional_params_expressions)
                print >> output_handle, "\t%s" % layout_line

            print "\t"
            if struct.sizer_field_name is not None:
                print >> output_handle, "\tout.%s.SetSizer(out.%s)" % (struct.self_field_name, struct.sizer_field_name)
            print >> output_handle, "\tout.%s.Layout()" % struct.self_field_name
            print >> output_handle, "}"
            print >> output_handle, ""

            # properties method
            print >> output_handle, "func (window %s) set_properties() {" % struct.name
            print >> output_handle, "\twindow.SetTitle(%s)" % golang_str_repr(struct.title)
            for field_name, property_name, additional_params_expressions in struct.properties_lines:
                if field_name is None:
                    field_fragment = ""
                else:
                    field_fragment = ".%s" % field_name
                if additional_params_expressions is None:
                    property_line = "window%s.Set%s()" % (field_fragment, property_name)
                else:
                    property_line = "window%s.Set%s(%s)" % (field_fragment, property_name, additional_params_expressions)
                print >> output_handle, "\t%s" % property_line

            print >> output_handle, "}"
            print >> output_handle, ""
