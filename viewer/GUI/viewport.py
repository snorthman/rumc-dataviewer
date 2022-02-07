import os

import dearpygui.dearpygui as dpg
import SimpleITK as sitk

from .explorer import Explorer
from .scan import Scan
from .filter import Filter
from viewer import tools

sitks = sitk.ImageSeriesReader()
texture_registry = set()

viewport_size = [1024, 768]


# def external_callback(sender, app_data, user_data):
#     config.add("EXTERNAL", user_data, app_data)
#
#
# def open_itksnap_callback(sender, app_data, user_data):
#     gdcmconv = config.get("EXTERNAL", "gdcmconv", fallback=None)
#     if gdcmconv is not None:
#         dicom2nifti.settings.set_gdcmconv_path(gdcmconv)
#         nii = dicom2nifti.dicom_series_to_nifti(user_data, os.getcwd() + "\\temp\\", reorient_nifti=True)
#         print(nii['NII_FILE'])
#     else:
#         dpg.configure_item(sender, label="Could not locate gdcmconv", enabled=False)


class Viewer:
    def __init__(self, filedialog):
        dpg.create_context()
        dpg.create_viewport(title='RUMC DataViewer', width=viewport_size[0], height=viewport_size[1], decorated=True)
        dpg.setup_dearpygui()

        self.filedialog = filedialog
        self.filter = None

        with dpg.theme(tag="theme_filter"):
            with dpg.theme_component(dpg.mvAll):
                dpg.add_theme_color(dpg.mvThemeCol_Button, (96, 96, 96), category=dpg.mvThemeCat_Core)

        tools.config.load()
        self.explorers = []
        self.data = dict()

    def _load_data(self, json):
        try:
            self.data = tools.load_data(json) if json else dict()
            if tools.config.get("DATA", "json") != json:
                tools.config.delete_section("DATA")
                tools.config.add("DATA", "json", json)
        except FileNotFoundError:
            self.data = dict()
        if 'patients' in self.data and 'dir' in self.data:
            self.data['dir'] = tools.config.get('DATA', 'dir', fallback=self.data['dir'])

            [dpg.delete_item(e.w) for e in self.explorers]
            self.explorers = [Explorer(self.data)]

            if not self._data_dir_path_exists():
                dpg.show_item("dir_updater")

    def _data_dir_path_exists(self):
        fkey = lambda d: next(iter(d))
        try:
            a = self.data['patients'][0]
            study = fkey(a['data'])
            serie = fkey(a['data'][study])
            dcm = a['data'][study][serie]['dcm']
            path = os.path.isfile(f"{self.data['dir']}/{a['id']}/{study}/{serie}/{dcm}")
        except:
            path = False
        dpg.configure_item("dir_check1", show=not path)
        dpg.configure_item("dir_check2", show=not path)
        dpg.configure_item("dir_updater", show=not path)
        for e in self.explorers:
            e.preview = path
            e.dir = self.data['dir']
        dpg.configure_item("dir_updater_value", default_value=self.data['dir'])
        return path

    def callback_update_dir_path(self):
        self.data['dir'] = self.filedialog.dialog_dir()
        dpg.configure_item("dir_updater_value", default_value=self.data['dir'])
        if self._data_dir_path_exists():
            tools.config.add("DATA", "dir", self.data['dir'])
            self.data['invalid_dir'] = False

    def callback_open_data(self):
        json = self.filedialog.dialog_json()
        if os.path.exists(json) and json.endswith('.json'):
            self._load_data(json)

    def callback_scan_data(self):
        scan_dir = self.filedialog.dialog_dir()
        Scan(scan_dir).run()

    def update_menu_filters(self):
        self.filter = None
        for alias in ["filter_menu", "filter_menu_delete"]:
            for item in dpg.get_item_children(alias, 1):
                if dpg.get_item_alias(item) not in dpg.get_aliases():
                    dpg.delete_item(item)

        sections = list(filter(lambda s: s.startswith("@"), tools.config.sections()))
        for s in sections:
            name = s[1:]
            filt = {'name': name, 'filters': dict()}
            for key in tools.config.keys(s):
                filt['filters'][key] = tools.config.get(s, key, fallback='')

            def delete_menu_filter():
                tools.config.delete_section(s)
                self.update_menu_filters()

            def create_filter():
                self.explorers.append(Explorer(self.data, filt))

            dpg.add_menu_item(parent="filter_menu", label=name, callback=create_filter)
            dpg.add_menu_item(parent="filter_menu_delete", label=name, callback=delete_menu_filter)

        dpg.configure_item("filter_menu_delete", show=len(sections) > 0)

    def create_menu_bar(self):
        with dpg.viewport_menu_bar():
            def show_dir_updater():
                dpg.show_item("dir_updater")
                dpg.focus_item("dir_updater")

            with dpg.menu(label="File"):
                dpg.add_menu_item(label="Open", callback=self.callback_open_data)
                dpg.add_menu_item(label="Scan", callback=self.callback_scan_data)
                dpg.add_separator(tag="dir_check1")
                dpg.add_menu_item(tag="dir_check2", label="Update data dir", callback=show_dir_updater)

            def create_filter_window():
                if self.filter is None:
                    self.filter = Filter(self.update_menu_filters).w
                else:
                    dpg.focus_item(self.filter)

            with dpg.menu(label="Filter", tag="filter_menu"):
                dpg.add_menu_item(label="New filter", tag="filter_menu_new", callback=create_filter_window)
                dpg.add_menu(label="Delete filter...", tag="filter_menu_delete", show=False)
                dpg.add_separator(tag="filter_menu_sep")
            self.update_menu_filters()

    def create_dir_updater(self):
        pos = [xy//3 for xy in viewport_size]
        with dpg.window(no_close=True, show=False, label="data dir not found", pos=pos, tag="dir_updater") as w:
            dpg.add_input_text(tag="dir_updater_value", readonly=True, width=500)
            dpg.add_text("is not a valid directory")
            dpg.add_text("Ignoring this problem disables the previewers")
            dpg.add_button(label="Update dir path", callback=self.callback_update_dir_path)
            dpg.add_button(label="Ignore", callback=lambda: dpg.configure_item(w, show=False))

    # def create_external(self):
    #     itksnap = {'name': "ITK-SNAP", 'url': "http://www.itksnap.org/pmwiki/pmwiki.php?n=Downloads.SNAP3"}
    #     gdcm = {'name': "gdcmconv", 'url': "https://github.com/malaterre/GDCM/releases/"}
    #
    #     with dpg.window(label=f"External tools", autosize=True, show=True) as external:
    #         dpg.add_text("These tools are required to open images from this viewer.")
    #         with dpg.table(header_row=False, pad_outerX=True):
    #             for i in range(3):
    #                 dpg.add_table_column(width_fixed=True)
    #
    #             for item in [itksnap, gdcm]:
    #                 name = item['name']
    #                 with dpg.table_row():
    #                     dpg.add_text(f"{name} directory")
    #                     dpg.add_button(label="?", callback=lambda: webbrowser.open(item['url']))
    #                     with dpg.tooltip(dpg.last_item()):
    #                         dpg.add_text(
    #                             f"Provide directory containing the {name} executable. Click me to navigate to downloads.")
    #                     dpg.add_input_text(default_value=config.get("EXTERNAL", name, fallback=""),
    #                                        user_data=name, callback=external_callback, width=300)
    #
    #     self.external = external

    def run(self):
        try:
            self.create_dir_updater()
            self.create_menu_bar()
            self._load_data(tools.config.get('DATA', 'json', fallback=None))

            def on_exit():
                tools.config.save()

            dpg.set_exit_callback(callback=on_exit)
            dpg.show_viewport()
            while dpg.is_dearpygui_running():
                dpg.render_dearpygui_frame()

            dpg.destroy_context()
        except Exception as e:
            print(e)
        finally:
            self.filedialog.end_process()
