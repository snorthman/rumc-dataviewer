import dearpygui.dearpygui as dpg

from viewer import tools


class Filter:
    def __init__(self, on_create=None):
        self.on_create = on_create
        self.items = ['description']
        with dpg.window(label=f"Filter options", autosize=True) as self.w:
            with dpg.table(pad_outerX=True, header_row=False, width=300):
                [dpg.add_table_column() for _ in range(2)]
                with dpg.table_row():
                    dpg.add_text("Name")
                    self.name = dpg.add_input_text(default_value="UntitledFilter", width=250)

            self.menu = dpg.add_menu(label="Add key...")
            dpg.add_separator()
            dpg.add_text('OR \',\'; NOT \'!\')')

            with dpg.table(pad_outerX=True):
                [dpg.add_table_column(label=l, width_fixed=True) for l in ['', 'key', 'contains']]
                self.rows = []
                for v in tools.dicom_kvp.values():
                    with dpg.table_row(show=False, user_data=v) as r:
                        dpg.add_button(callback=self.remove_item, user_data=v)
                        dpg.add_text(v)
                        dpg.add_input_text(width=250)
                    self.rows.append(r)

            dpg.add_button(label="Create filter", callback=self.create_filter)
            self.update_items()

    def menu(self):
        with dpg.menu(label="Filter") as self.menu:
            dpg.add_menu_item(label="New filter", callback=self.w)
            dpg.add_separator()

    def create_filter(self):
        section = f"@{dpg.get_value(self.name)}"
        for row in self.rows:
            if dpg.get_item_configuration(row).get('show'):
                cells = dpg.get_item_children(row, 1)
                tools.config.add(section, dpg.get_value(cells[1]), dpg.get_value(cells[2]))
        tools.config.save()
        dpg.delete_item(self.w)
        self.on_create()

    def update_items(self):
        f = set(list(tools.dicom_kvp.values())).difference(set(self.items))
        dpg.delete_item(self.menu, children_only=True)
        [dpg.add_menu_item(parent=self.menu, label=v, callback=self.add_item, user_data=v) for v in f]
        for row in self.rows:
            dpg.configure_item(row, show=dpg.get_item_user_data(row) in self.items)
            is_final = len(self.items) == 1
            dpg.configure_item(dpg.get_item_children(row, 1)[0], label=" " if is_final else "x", enabled=not is_final)

    def add_item(self, sender, app_data, user_data):
        self.items.append(user_data)
        self.update_items()

    def remove_item(self, sender, app_data, user_data):
        self.items.remove(user_data)
        self.update_items()
