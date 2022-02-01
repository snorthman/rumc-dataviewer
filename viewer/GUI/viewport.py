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
        json = tools.config.get('DATA', 'json', fallback=None)
        try:
            self.data = tools.load_data(json) if json else []
        except FileNotFoundError:
            self.data = []
        if len(self.data) > 0:
            Explorer(self.data)

    def callback_open_data(self):
        json = self.filedialog.dialog_json()
        if os.path.exists(json) and json.endswith('.json'):
            self.data = tools.load_data(json)
            tools.config.add("DATA", "json", json)
            Explorer(self.data)

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

            def dd():
                Explorer(self.data, filt)

            dpg.add_menu_item(parent="filter_menu", label=name, callback=dd)
            dpg.add_menu_item(parent="filter_menu_delete", label=name, callback=delete_menu_filter)

        dpg.configure_item("filter_menu_delete", show=len(sections) > 0)

    def create_menu_bar(self):
        with dpg.viewport_menu_bar():
            with dpg.menu(label="File"):
                dpg.add_menu_item(label="Open", callback=self.callback_open_data)
                dpg.add_menu_item(label="Scan", callback=self.callback_scan_data)

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
            self.create_menu_bar()

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
