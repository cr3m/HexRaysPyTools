import HexRaysPyTools.Actions as Actions
from HexRaysPyTools.Core.TemporaryStructure import *
import HexRaysPyTools.Forms as Forms
import idaapi


# import Core.QtShim as QtShim


def hexrays_events_callback(*args):
    hexrays_event = args[0]
    if hexrays_event == idaapi.hxe_keyboard:
        hx_view, key, shift = args[1:]
        if key == ord('F'):
            if Actions.ScanVariable.check(hx_view.cfunc, hx_view.item):
                idaapi.process_ui_action("my:ScanVariable")

    elif hexrays_event == idaapi.hxe_populating_popup:
        form, popup, hx_view = args[1:]
        item = hx_view.item  # current ctree_item_t

        if Actions.ScanVariable.check(hx_view.cfunc, item):
            idaapi.attach_action_to_popup(form, popup, "my:ScanVariable", None)

        elif item.citype == idaapi.VDI_FUNC:
            # If we clicked on function
            if not hx_view.cfunc.entry_ea == idaapi.BADADDR:  # Probably never happen
                idaapi.attach_action_to_popup(form, popup, "my:RemoveReturn", None)

        elif item.citype == idaapi.VDI_LVAR:
            # If we clicked on argument
            local_variable = hx_view.item.get_lvar()          # idaapi.lvar_t
            if local_variable.is_arg_var:
                idaapi.attach_action_to_popup(form, popup, "my:RemoveArgument", None)

        elif item.citype == idaapi.VDI_EXPR and item.e.op == idaapi.cot_num:
            number_format = item.e.n.nf                       # idaapi.number_format_t
            print "(number) flags: {0:#010X}, type_name: {1}, opnum: {2}".format(
                number_format.flags,
                number_format.type_name,
                number_format.opnum
            )
            idaapi.attach_action_to_popup(form, popup, Actions.GetStructureBySize.name, None)

    elif hexrays_event == idaapi.hxe_double_click:
        hx_view = args[1]
        item = hx_view.item
        if item.citype == idaapi.VDI_EXPR and item.e.op == idaapi.cot_memptr:
            # Look if we double clicked on expression that is member pointer. Then get tinfo_t of  the structure.
            # After that remove pointer and get member name with the same offset
            structure_tinfo = item.e.x.type
            member_offset = item.e.m
            if structure_tinfo.is_ptr():
                structure_tinfo.remove_ptr_or_array()
                if structure_tinfo.is_udt():
                    udt_data = idaapi.udt_type_data_t()
                    structure_tinfo.get_udt_details(udt_data)
                    member_name = filter(lambda x: x.offset == member_offset * 8, udt_data)[0].name

                    # And finally look through all functions and find the same name. Sigh...
                    for idx in xrange(idaapi.get_func_qty()):
                        function = idaapi.getn_func(idx)
                        if idaapi.get_func_name2(function.startEA) == member_name:
                            idaapi.open_pseudocode(function.startEA, 0)
                            return 1
    return 0


class MyPlugin(idaapi.plugin_t):
    # flags = idaapi.PLUGIN_HIDE
    flags = 0
    comment = "Plugin for automatic classes reconstruction"
    help = "This is help"
    wanted_name = "My Python plugin"
    wanted_hotkey = "Alt-F8"
    structure_builder = None
    temporary_structure = None

    @staticmethod
    def init():
        idaapi.msg("init() called\n")
        if not idaapi.init_hexrays_plugin():
            return idaapi.PLUGIN_SKIP

        MyPlugin.temporary_structure = TemporaryStructureModel()

        Actions.register(Actions.CreateVtable)
        Actions.register(Actions.ShowGraph)
        Actions.register(Actions.GetStructureBySize)
        Actions.register(Actions.RemoveArgument)
        Actions.register(Actions.RemoveReturn)
        Actions.register(Actions.ScanVariable, MyPlugin.temporary_structure)

        idaapi.install_hexrays_callback(hexrays_events_callback)

        return idaapi.PLUGIN_KEEP

    @staticmethod
    def run(arg):
        idaapi.msg("run() called!\n")

        if not MyPlugin.structure_builder:
            MyPlugin.structure_builder = Forms.StructureBuilder(MyPlugin.temporary_structure)
        MyPlugin.structure_builder.Show()

    @staticmethod
    def term():
        MyPlugin.temporary_structure.clear()
        idaapi.msg("term() called!\n")
        Actions.unregister(Actions.CreateVtable)
        Actions.unregister(Actions.ShowGraph)
        Actions.unregister(Actions.GetStructureBySize)
        Actions.unregister(Actions.RemoveArgument)
        Actions.unregister(Actions.RemoveReturn)
        Actions.unregister(Actions.ScanVariable)
        idaapi.term_hexrays_plugin()


def PLUGIN_ENTRY():
    return MyPlugin()
