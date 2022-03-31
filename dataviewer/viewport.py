import os, webbrowser
from collections import OrderedDict

import pydicom
import dearpygui.dearpygui as dpg
import SimpleITK as sitk
import numpy as np

sitks = sitk.ImageSeriesReader()
texture_registry = set()
whitelist = ['SeriesLength', 'StudyDate', 'StudyTime', 'SeriesDate', 'SeriesTime',
             'Modality', 'Manufacturer', 'ManufacturersModelName', 'SequenceName',
             'PatientID', 'StudyDescription', 'SeriesDescription']
viewport_size = [1024, 768]
max_item_width = 700


def item_get(item, key, alt=None):
    value = item[key]
    return value if value is not None else alt


class Viewer:
    def __init__(self, name, items, kvp=None, series=None):
        dpg.create_context()
        dpg.create_viewport(title=f'RUMC DataViewer ({name})', width=viewport_size[0], height=viewport_size[1])
        dpg.setup_dearpygui()

        self.selection = kvp
        self.items = items
        self.series = series if series is not None else []
        self.explorer = -1

    def create_explorer(self):
        with dpg.window(autosize=True, min_size=[220, 100], no_close=True, max_size=[1000, 768]) as self.explorer:
            try:
                # visualize selection
                if self.selection is not None:
                    with dpg.collapsing_header(label='View --select arguments'):
                        with dpg.table(parent=dpg.last_item(), header_row=False, borders_innerV=True):
                            [dpg.add_table_column(width_fixed=True) for _ in range(2)]
                            for k, v in self.selection.items():
                                with dpg.table_row():
                                    dpg.add_text(k)
                                    dpg.add_input_text(default_value=v, readonly=True, width=200)
                    dpg.add_separator()
                w_c = len(dpg.get_item_children(self.explorer)[1])

                nodes = []
                # create tree structure
                for item in self.items:
                    patient_id = str(item['PatientID'])
                    study_id = str(item['StudyInstanceUID'])
                    series_id = str(item['SeriesInstanceUID'])

                    if not dpg.does_item_exist(patient_id):
                        nodes.append((dpg.add_tree_node(tag=patient_id, label=patient_id), 1))

                    if not dpg.does_item_exist(study_id):
                        nodes.append((dpg.add_tree_node(parent=patient_id, tag=study_id,
                                                        label=item_get(item, 'StudyDescription',
                                                                       f'Study {item["index"]}')),
                                      2))
                    if not dpg.does_item_exist(series_id):
                        s = dpg.add_button(parent=study_id, tag=series_id, user_data=item, callback=callback_item,
                                           label=item_get(item, 'SeriesDescription', f'Series {item["index"]}'))
                        if series_id in self.series:
                            dpg.bind_item_theme(s, 'theme_select')

                plurals = (('patient', 'patients'), ('study', 'studies'), ('series', 'series'))
                count = lambda a, b: f'({b} {plurals[a][0 if b == 1 else 1]})'

                dpg.configure_item(self.explorer,
                                   label=f'Explorer {count(0, len(dpg.get_item_children(self.explorer)[1]) - w_c)}')
                for node, plural in nodes:
                    l, c = dpg.get_item_label(node), len(dpg.get_item_children(node)[1])
                    dpg.configure_item(node, label=f'{l} {count(plural, c)}')
            except Exception as e:
                with dpg.collapsing_header(label='An error occurred while loading results') as c:
                    dpg.bind_item_theme(c, 'theme_error')
                    dpg.add_text(e)

    def run(self):
        with dpg.theme() as global_theme:
            with dpg.theme_component(dpg.mvAll):
                dpg.add_theme_style(dpg.mvStyleVar_ItemSpacing, y=3)
                dpg.add_theme_style(dpg.mvStyleVar_FramePadding, y=2)
                dpg.add_theme_style(dpg.mvStyleVar_CellPadding, x=0, y=0)
        dpg.bind_theme(global_theme)

        with dpg.theme(tag='theme_select'):
            with dpg.theme_component(dpg.mvAll):
                dpg.add_theme_color(dpg.mvThemeCol_Button, (96, 96, 96), category=dpg.mvThemeCat_Core)

        with dpg.theme(tag='theme_item'):
            with dpg.theme_component(dpg.mvAll):
                dpg.add_theme_color(dpg.mvThemeCol_Button, (15, 86, 135), category=dpg.mvThemeCat_Core)

        with dpg.theme(tag='theme_error'):
            with dpg.theme_component(dpg.mvAll):
                dpg.add_theme_color(dpg.mvThemeCol_Header, (128, 0, 0), category=dpg.mvThemeCat_Core)

        with dpg.handler_registry():
            def callback_close(sender, key, _):
                if key == 27:
                    d = list(callback_items.keys()) + [f for f in callback_items.keys() if dpg.is_item_focused(f)]
                    if len(d) > 0:
                        dpg.delete_item(callback_items[(d := d.pop())])
                        callback_items.pop(d)
            dpg.add_key_press_handler(callback=callback_close)

        self.create_explorer()

        def on_exit():
            pass

        dpg.set_exit_callback(callback=on_exit)

        dpg.show_viewport()
        while dpg.is_dearpygui_running():
            dpg.render_dearpygui_frame()

        dpg.destroy_context()


callback_items = OrderedDict()


def callback_item(sender, _, user_data: dict):
    if sender in callback_items:
        return

    item = sender
    labels = []
    for _ in range(3):
        labels.append(dpg.get_item_label(item).rsplit('(')[0].strip())
        item = dpg.get_item_parent(item)
    labels.reverse()

    def exception_text(label, e):
        with dpg.collapsing_header(label=label) as c:
            dpg.bind_item_theme(c, 'theme_error')
            dpg.add_input_text(default_value=e, readonly=True, width=max_item_width)


    with dpg.window(label='/'.join(labels), autosize=True, on_close=lambda: callback_items.pop(sender)) as w:
        dpg.bind_item_theme(w, 'theme_item')

        expand = dpg.add_button(label='Expand', callback=callback_toggle_item, width=200)

        dpg.add_separator()
        try:
            with dpg.table(header_row=False, pad_outerX=True) as t:
                dpg.set_item_user_data(expand, t)

                dpg.add_table_column(label='key', width_fixed=True)
                dpg.add_table_column(label='value')

                (keys := list(user_data.keys())).sort()
                [keys.remove(k) for k in ['index', 'Sample', 'Path', 'SeriesLength']]

                key_column, value_column = [], []
                for ks, white in ((['SeriesLength'] + keys, False), (whitelist, True)):
                    for k in ks:
                        v = item_get(user_data, k)
                        v_exists = v is not None and len(str(v).strip()) > 0
                        with dpg.table_row(show=white, user_data=white):
                            key_column.append(dpg.add_text(k, color=(-255, 0, 0) if v_exists else (128, 128, 128)))
                            if v_exists:
                                value_column.append(dpg.add_input_text(default_value=v, readonly=True))

                max_column_width = max([dpg.get_text_size(dpg.get_value(c))[0] for c in key_column])
                [dpg.set_item_width(c, max_item_width - max_column_width) for c in value_column]
            dpg.add_separator()

            # explore to path
            path = user_data['Path']
            dpg.add_button(label='Open in explorer', enabled=os.path.exists(path), width=200,
                           callback=lambda: webbrowser.open(path))

        except Exception as e:
            exception_text('Failed to read this series', e)

        # preview
        try:
            img = pydicom.read_file(os.path.join(path, user_data['Sample'])).pixel_array
            with dpg.texture_registry():
                texture_data = []
                [texture_data.extend([px, px, px, 1]) for px in np.flipud(img).flatten() / img.max(initial=1)]
                tex = dpg.add_static_texture(img.shape[0], img.shape[1], texture_data)
            with dpg.plot(label=user_data['Sample'], height=img.shape[0] * 2, width=img.shape[1] * 2):
                [dpg.add_plot_axis(axis, no_tick_marks=True) for axis in [dpg.mvXAxis, dpg.mvYAxis]]
                dpg.draw_image(tex, pmin=[0, 0], pmax=[1, 1])  # img.shape)

        except Exception as e:
            exception_text('Failed to load DICOM image for preview', e)
    callback_items[sender] = w


def callback_toggle_item(sender, _, user_data):
    rows = dpg.get_item_children(user_data, 1)
    collapse = dpg.get_item_label(sender) == 'Collapse'
    white = (lambda a: a) if collapse else (lambda a: not a)

    [dpg.configure_item(r, show=white(dpg.get_item_user_data(r))) for r in rows]
    dpg.configure_item(sender, label='Expand' if collapse else 'Collapse')
