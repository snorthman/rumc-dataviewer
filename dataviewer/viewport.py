import os

import dearpygui.dearpygui as dpg
import SimpleITK as sitk

sitks = sitk.ImageSeriesReader()
texture_registry = set()
viewport_size = [1024, 768]

class Viewer:
    def __init__(self, items):
        dpg.create_context()
        dpg.create_viewport(title='RUMC DataViewer', width=viewport_size[0], height=viewport_size[1], decorated=True)
        dpg.setup_dearpygui()

        with dpg.theme(tag="theme_filter"):
            with dpg.theme_component(dpg.mvAll):
                dpg.add_theme_color(dpg.mvThemeCol_Button, (96, 96, 96), category=dpg.mvThemeCat_Core)

        self.items = items

    def create_menu_bar(self):
        with dpg.viewport_menu_bar():
            dpg.add_menu_item(label="Exit", callback=dpg.destroy_context)
            # with dpg.menu(label="File"):
            #     dpg.add_menu_item(label="Source")
            #     dpg.add_menu_item(label="Scan")
            #     dpg.add_menu_item(label="Exit", callback=dpg.destroy_context)

            # def create_filter_window():
            #     if self.filter is None:
            #         self.filter = Filter(self.update_menu_filters).w
            #     else:
            #         dpg.focus_item(self.filter)
            #
            # with dpg.menu(label="Select", tag="filter_menu"):
            #     dpg.add_menu_item(label="New filter", tag="filter_menu_new", callback=create_filter_window)
            #     dpg.add_menu(label="Delete filter...", tag="filter_menu_delete", show=False)
            #     dpg.add_separator(tag="filter_menu_sep")
            # self.update_menu_filters()

    def run(self):
        try:
            self.create_menu_bar()

            def on_exit():
                pass

            dpg.set_exit_callback(callback=on_exit)
            dpg.show_viewport()
            while dpg.is_dearpygui_running():
                dpg.render_dearpygui_frame()

            dpg.destroy_context()
        except Exception as e:
            print(e)