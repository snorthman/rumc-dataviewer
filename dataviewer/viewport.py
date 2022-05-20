import os, webbrowser, threading, queue, concurrent.futures
from collections import OrderedDict
from pathlib import Path

import pandas as pd, pydicom, dearpygui.dearpygui as dpg, numpy as np, SimpleITK as sitk

isr = sitk.ImageSeriesReader()
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
    def __init__(self, db: Path, input_path: Path, items, kvp=None, series=None):
        dpg.create_context()
        dpg.create_viewport(title=f'RUMC data viewer ({db.name})', width=viewport_size[0], height=viewport_size[1])
        dpg.setup_dearpygui()

        self.input_path = str(input_path)
        self.input_path_default = self.input_path
        self.selection = kvp
        self.items = items
        self.series = series if series is not None else []
        self.explorer = -1
        self.queue = queue.SimpleQueue()

    def populate_tree(self):
        total_items = len(self.items)
        dpg.configure_item(self.explorer, label=f'Explorer (loading {total_items} results)')

        def thread_populate():
            def create_item(item):
                with dpg.stage() as stage:
                    patient_id = str(item['PatientID'])
                    study_id = str(item['StudyInstanceUID'])
                    series_id = str(item['SeriesInstanceUID'])

                    patient = None if dpg.does_item_exist(patient_id) else dpg.add_tree_node(tag=patient_id, label=patient_id, user_data=0)
                    study = None if dpg.does_item_exist(study_id) else \
                        dpg.add_tree_node(parent=patient_id, tag=study_id, user_data=0, label=item_get(item, 'StudyDescription', f'Study {item["index"]}'))

                    if not dpg.does_item_exist(series_id):
                        s = dpg.add_button(parent=study_id, tag=series_id, user_data=(item, lambda: self.input_path), callback=callback_item,
                                           label=item_get(item, 'SeriesDescription', f'Series {item["index"]}'))
                        if series_id in self.series:
                            dpg.bind_item_theme(s, 'theme_select')
                            for id in [study_id, patient_id, self.explorer]:
                                dpg.set_item_user_data(id, dpg.get_item_user_data(id) + 1)
                self.queue.put((stage, patient, study))

            with concurrent.futures.ThreadPoolExecutor(min(32, (os.cpu_count() or 1) + 4)) as executor:
                executor.map(create_item, self.items)

            self.queue.put(-1)

        (t_populate := threading.Thread(target=thread_populate)).start()

        def thread_load():
            gets = []
            progress = dpg.add_progress_bar(parent=self.explorer, overlay='0%')
            while t_populate.is_alive():
                if (get := self.queue.get()) != -1:
                    gets.append(get)
                    dpg.set_value(progress, p := (len(gets) / total_items))
                    dpg.configure_item(progress, overlay=str(round(p * 100)) + '%')

            stages, patients, studies = tuple(list(filter(None, x)) for x in zip(*gets))
            plurals = (('patient', 'patients'), ('study', 'studies'), ('series', 'series'))

            def label_summary(tier, count, results = 0):
                sing, plu = plurals[tier]
                plural = lambda s, p, c: f'{c} {s}' if c == 1 else f'{c} {p}'
                count = plural(sing, plu, count)
                if results > 0:
                    results = plural('result', 'results', results)
                    return f'({count}, {results})'
                return f'({count})'

            dpg.configure_item(self.explorer, label=f'Explorer {label_summary(0, len(patients), dpg.get_item_user_data(self.explorer))}')

            for nodes, tier in [(patients, 1), (studies, 2)]:
                for node in nodes:
                    l, c = dpg.get_item_label(node), len(dpg.get_item_children(node)[1])
                    dpg.configure_item(node, label=f'{l} {label_summary(tier, c, dpg.get_item_user_data(node))}')

            dpg.delete_item(progress)

            for stage in stages:
                dpg.push_container_stack(self.explorer)
                dpg.unstage(stage)
                dpg.pop_container_stack()

        (t_load := threading.Thread(target=thread_load)).start()
        return t_populate, t_load

    def create_explorer(self):
        with dpg.window(autosize=True, min_size=[300, 100], no_close=True, max_size=viewport_size, user_data=0) as self.explorer:
            try:
                dpg.add_button(label='Edit source directory', callback=lambda: dpg.show_item('source'), width=300)

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

                self.populate_tree()
            except Exception as e:
                with dpg.collapsing_header(label='An error occurred while loading results') as c:
                    dpg.bind_item_theme(c, 'theme_error')
                    dpg.add_input_text(readonly=True, default_value=e)

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
            # ESC hotkey functionality
            def callback_close(sender, key, _):
                if key == 27:
                    d = list(callback_items.keys()) + [f for f in callback_items.keys() if dpg.is_item_focused(f)]
                    if len(d) > 0:
                        dpg.delete_item(callback_items[(d := d.pop())])
                        callback_items.pop(d)
            dpg.add_key_press_handler(callback=callback_close)

        def callback_source_input(sender):
            self.input_path = dpg.get_value(sender)
            dpg.set_item_width('source_input', w := dpg.get_text_size(self.input_path)[0])
            dpg.set_item_width('source', w + 20)

        def callback_source_default():
            self.input_path = self.input_path_default
            dpg.set_value('source_input', self.input_path)
            callback_source_input('source_input')

        with dpg.window(tag='source',popup=True, autosize=True):
            dpg.add_input_text(tag='source_input', callback=callback_source_input, width=viewport_size[0] // 2)
            dpg.add_text('The source directory is the parent directory of all data shown,\nused for loading previews.')
            dpg.add_button(tag='source_default', label=" Reset to default ", callback=callback_source_default)

        self.create_explorer()
        with dpg.viewport_menu_bar(tag='menu'):
            dpg.add_menu_item(label="Close (ESC) ", callback=dpg.destroy_context)

        def on_exit():
            pass

        dpg.set_exit_callback(callback=on_exit)

        dpg.show_viewport(maximized=True)

        dpg.render_dearpygui_frame()
        callback_source_default()

        while dpg.is_dearpygui_running():
            dpg.render_dearpygui_frame()

        dpg.destroy_context()


callback_items = OrderedDict()


def callback_item(sender, _, user_data):
    item, get_input_path = user_data

    if sender in callback_items:
        return

    labels = []
    for _ in range(3):
        labels.append(dpg.get_item_label(sender).rsplit('(')[0].strip())
        sender = dpg.get_item_parent(sender)
    labels.reverse()

    def exception_text(label, e):
        with dpg.collapsing_header(label=label) as c:
            dpg.bind_item_theme(c, 'theme_error')
            dpg.add_input_text(default_value=e, readonly=True, width=max_item_width)


    with dpg.window(label='/'.join(labels), autosize=True, on_close=lambda: callback_items.pop(sender)) as w:
        dpg.bind_item_theme(w, 'theme_item')

        expand = dpg.add_button(label='Expand', callback=callback_toggle_item, width=300)

        dpg.add_separator()
        try:
            with dpg.table(header_row=False, pad_outerX=True) as t:
                dpg.set_item_user_data(expand, t)

                dpg.add_table_column(label='key', width_fixed=True)
                dpg.add_table_column(label='value')

                (keys := list(item.keys())).sort()
                [keys.remove(k) for k in ['index', 'Sample', 'Path', 'SeriesLength']]

                key_column, value_column = [], []
                for ks, white in ((['SeriesLength'] + keys, False), (whitelist, True)):
                    for k in ks:
                        v = item_get(item, k)
                        v_exists = v is not None and len(str(v).strip()) > 0
                        with dpg.table_row(show=white, user_data=white):
                            key_column.append(dpg.add_text(k, color=(-255, 0, 0) if v_exists else (128, 128, 128)))
                            if v_exists:
                                value_column.append(dpg.add_input_text(default_value=v, readonly=True))

                max_column_width = max([dpg.get_text_size(dpg.get_value(c))[0] for c in key_column])
                [dpg.set_item_width(c, int(max_item_width - max_column_width)) for c in value_column]
            dpg.add_separator()

            # explore to path
            path = os.path.join(get_input_path(), item['Path'])
            dpg.add_button(label='Open in explorer', enabled=os.path.exists(path), width=300,
                           callback=lambda: webbrowser.open(path))
            with dpg.tooltip(dpg.last_item()):
                dpg.add_text(path)

        except Exception as e:
            exception_text('Failed to read this series', e)

        # clipboard
        sample = os.path.join(get_input_path(), item['Path'], item['Sample'])
        dpg.add_button(label='Copy sample path to clipboard', enabled=os.path.exists(sample), width=300,
                       callback=lambda: pd.DataFrame([sample]).to_clipboard(index=False,header=False))
        with dpg.tooltip(dpg.last_item()):
            dpg.add_text('Copy: ' + os.path.join(item['Path'], item['Sample']))

        # preview
        try:
            img = pydicom.read_file(sample).pixel_array
            with dpg.texture_registry():
                texture_data = []
                [texture_data.extend([px, px, px, 1]) for px in np.flipud(img).flatten() / img.max(initial=1)]
                tex = dpg.add_static_texture(img.shape[0], img.shape[1], texture_data)
            with dpg.collapsing_header(label=f'Sample: {item["Sample"]}', default_open=True):
                with dpg.plot(height=img.shape[0] * 2, width=img.shape[1] * 2):
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
