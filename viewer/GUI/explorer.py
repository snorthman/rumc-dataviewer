import webbrowser, os

import dearpygui.dearpygui as dpg
from thefuzz import fuzz
import pydicom
import numpy as np

import SimpleITK as sitk

from .. import tools

whitelist_data_keys = {"type", "sequence", "dob", "gender", "date"}
sitki = sitk.ImageFileReader()

class Explorer:
    def __init__(self, data, filter_info=None):
        no_filter = filter_info is None
        self.data = data['patients']
        self.dir = data['dir']
        self.preview = False
        if no_filter:
            self.filter = None
        else:
            print(filter_info)
            self.filter = filter_info['filters'].copy()
            for f in self.filter:
                self.filter[f] = [s.strip() for s in self.filter[f].split(',')]

        self.stats = dict()

        with dpg.window(label=f"Explorer ({len(self.data)} patients)" if no_filter else "Filter:" + filter_info['name'],
                        autosize=True, min_size=[220, 100], no_close=no_filter) as self.w:
            # Filter header
            if not no_filter:
                with dpg.collapsing_header(label="Filter"):
                    with dpg.table(parent=dpg.last_item(), header_row=False, borders_innerV=True):
                        [dpg.add_table_column(width_fixed=True) for _ in range(2)]
                        for k, v in self.filter.items():
                            with dpg.table_row():
                                dpg.add_text(k)
                                dpg.add_text(', '.join(v))

            # Stats var
            stats_id = dpg.add_collapsing_header(label="Statistics")
            stats_patients = len(self.data)
            stats_studies = []
            stats_series = []
            stats_hits = []

            dpg.add_separator()

            # Tree view
            for p in self.data:
                if len(p['data']) == 0:
                    continue
                stats_studies.append(len(p['data']))
                hits = [0 for _ in range(stats_studies[-1])]

                node_patient = dpg.add_tree_node(label=f"{p['id']} ({len(p['data'])} studies)")
                for i, study in enumerate(p['data'].keys()):
                    stats_series.append(len(p['data'][study]))

                    node_study = dpg.add_tree_node(label=f"study {i}", parent=node_patient)
                    for serie in p['data'][study].keys():
                        item = p['data'][study][serie]
                        item['header'] = f"{p['id']}/study {i}/{item.get('description')}"
                        leaf = dpg.add_button(label=item.get('description'), parent=node_study, small=True,
                                              user_data=item,
                                              callback=self._explorer_callback)
                        # Apply filter
                        if not no_filter:
                            if self.apply_filter(item):
                                dpg.bind_item_theme(leaf, "theme_filter")
                                hits[i] += 1

                    if hits[i] > 0:
                        dpg.configure_item(node_study, label=f"study {i} ({hits[i]} matches)")
                stats_hits.append(sum(hits))
                if not no_filter and sum(hits) == 0:
                    dpg.delete_item(node_patient)

            # Stats header
            stats = [("# patients", stats_patients),
                     ("# studies", sum(stats_studies)),
                     ("# studies per patient", sum(stats_studies) / len(stats_studies)),
                     ("# series", sum(stats_series)),
                     ("# series per study", sum(stats_series) / len(stats_series)),
                     ("# matches", sum(stats_hits))]
            with dpg.table(parent=stats_id, header_row=False, borders_innerV=True):
                [dpg.add_table_column(width_fixed=True) for _ in range(2)]
                for s in stats:
                    if s[1] > 0:
                        with dpg.table_row():
                            dpg.add_text(s[0])
                            dpg.add_text(str(round(s[1], 2)))

    def apply_filter(self, item):
        for key in self.filter:
            v = item.get(key, None)
            if v is None:
                continue
            for f in self.filter[key]:
                if fuzz.partial_token_sort_ratio(v, f) >= 80:
                    return True
        return False

    def _explorer_callback(self, sender, app_data, user_data):
        with dpg.window(label=user_data.get('header'), autosize=True):
            with dpg.table(header_row=False, pad_outerX=True) as t:
                dpg.add_table_column(label="key", width_fixed=True)
                dpg.add_table_column(label="value")
                with dpg.table_row():
                    dpg.add_button(label="Expand", user_data=t, callback=self._expand_item_callback)

                with dpg.table_row(user_data=True):
                    dpg.add_text("dicoms")
                    dpg.add_text(str(len(user_data.get('files'))))
                for v in tools.dicom_kvp.values():
                    s = v in whitelist_data_keys
                    with dpg.table_row(show=s, user_data=s):
                        dpg.add_text(v)
                        dpg.add_text(user_data.get(v))

            if self.preview:
                fp = f"{self.dir}/{user_data['id_patient'].strip()}/{user_data['id_study']}/{user_data['id_series']}"
                dpg.add_input_text(default_value=fp, readonly=True, width=250)
                dpg.add_button(label="Explore to path", callback=lambda: webbrowser.open(user_data['path']), width=250)
                img = pydicom.read_file(f"{fp}/{user_data['dcm']}").pixel_array
                with dpg.texture_registry():
                    texture_data = []
                    [texture_data.extend([px, px, px, 1]) for px in np.flipud(img).flatten() / img.max(initial=1)]
                    tex = dpg.add_static_texture(img.shape[0], img.shape[1], texture_data)
                with dpg.plot(label=user_data['dcm'], height=img.shape[0] * 2, width=img.shape[1] * 2):
                    ax = [dpg.add_plot_axis(axis, no_tick_marks=True) for axis in [dpg.mvXAxis, dpg.mvYAxis]]
                    dpg.draw_image(tex, pmin=[0, 0], pmax=[1, 1])#img.shape)
                    # [dpg.set_axis_limits(ax[i], 0, img.shape[i]) for i in range(len(ax))]



            # reader.SetFileName(inputImageFileName)

    def _expand_item_callback(self, sender, app_data, user_data):
        rows = dpg.get_item_children(user_data, 1)[1:]
        if dpg.get_item_configuration(sender).get('label') == "Expand":
            [dpg.configure_item(r, show=True) for r in rows]
            dpg.configure_item(sender, label="Collapse")
        else:
            [dpg.configure_item(r, show=dpg.get_item_user_data(r)) for r in rows]
            dpg.configure_item(sender, label="Expand")
