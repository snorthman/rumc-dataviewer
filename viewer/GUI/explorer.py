import webbrowser, threading

import dearpygui.dearpygui as dpg
from thefuzz import fuzz
import pydicom
import numpy as np

import SimpleITK as sitk

from .. import db
from .. import tools

whitelist_data_keys = {"type", "sequence", "dob", "gender", "date"}
sitki = sitk.ImageFileReader()

class Explorer:
    def __init__(self, filter_info=None, explorer_func=None):
        no_filter = filter_info is None
        self.data = range(len(db.patients))
        self.dir = db.dir
        self.preview = False
        self.nodes = {}

        if no_filter:
            self.filter = None
            self.name = "Explorer"
        else:
            self.filter = filter_info['filters'].copy()
            self.name = f"Filter: {filter_info['name']}"
            for f in self.filter:
                self.filter[f] = [s.strip() for s in self.filter[f].split(',')]

        self.stats = dict()

        with dpg.window(label=self.name, autosize=True, min_size=[220, 100], no_close=no_filter, max_size=[1000, 768]) as self.w:
            # Filter header
            if not no_filter:
                with dpg.collapsing_header(label="Filter"):
                    with dpg.table(parent=dpg.last_item(), header_row=False, borders_innerV=True):
                        [dpg.add_table_column(width_fixed=True) for _ in range(2)]
                        for k, v in self.filter.items():
                            with dpg.table_row():
                                dpg.add_text(k)
                                dpg.add_input_text(default_value=', '.join(v), readonly=True, width=150)
                dpg.add_separator()

            self.scanning = dpg.add_text(f"(0/{len(self.data)})")
        threading.Thread(target=self.scan).start()

    def populate(self):
        n_patients = len(self.data)
        d_patients = len(str(n_patients))

        for i, p in enumerate(self.data):
            id = db.patients[p]['id']
            patient = db.patients[p]['data']
            studies = len(patient)
            idx = str(i + 1).rjust(d_patients, ' ')
            if studies == 0:
                continue
            if studies == 1:
                studies = f"{studies} study"
            else:
                studies = f"{studies} studies"

            node_patient = dpg.add_tree_node(label=f"{idx} ~ {id} ({studies})", parent=self.w,
                                             user_data={'id': id, 'patient': patient})
            with dpg.item_handler_registry() as handler:
                dpg.add_item_toggled_open_handler(callback=self.callback_patient_node, user_data=node_patient)
            dpg.bind_item_handler_registry(node_patient, handler)

        dpg.configure_item(self.w, label=f"{self.name} ({n_patients} results)")

    def scan(self):
        def can_apply_filter(p):
            patient = db.patients[p]['data']
            for study in patient.keys():
                for serie in patient[study].keys():
                    item = patient[study][serie]
                    if self.apply_filter(item):
                        return p
            return -1

        lenp = len(db.patients)
        if self.filter is not None:
            self.data = []
            for p in range(lenp):
                if can_apply_filter(p) >= 0:
                    self.data.append(p)
                dpg.configure_item(self.scanning, default_value=f"({p + 1}/{lenp})")

        dpg.delete_item(self.scanning)
        self.populate()

    def apply_filter(self, item):
        for key in self.filter:
            found = False
            v = item.get(key, None)
            if v is None:
                continue

            for f in self.filter[key]:
                negation = f.startswith('!')
                if negation and fuzz.partial_token_sort_ratio(v, f) < 100:
                    found = True
                    break
                if not negation and fuzz.partial_token_sort_ratio(v, f) == 100:
                    found = True
                    break

            if not found:
                return False
        return True


    def callback_patient_node(self, sender, app_data, user_data):
        if user_data is not None:
            dpg.set_item_user_data(sender, None)

            data = dpg.get_item_user_data(user_data)
            patient = data['patient']
            for i, study in enumerate(patient.keys()):
                node_study = dpg.add_tree_node(label=f"study {i}", parent=user_data)
                matches = 0
                for serie in patient[study].keys():
                    item = patient[study][serie]
                    item['header'] = f"{data['id']}/study {i}/{item.get('description')}"
                    leaf = dpg.add_button(label=item.get('description'), parent=node_study, small=True,
                                          user_data=item,
                                          callback=self.callback_item)
                    # Apply filter
                    if self.filter:
                        if self.apply_filter(item):
                            dpg.bind_item_theme(leaf, "theme_filter")
                            matches += 1
                match_text = f"({matches} matches)" if matches > 1 else f"(1 match)"
                if matches > 0:
                    dpg.configure_item(node_study, label=f"study {i} {match_text}")

    def callback_item(self, sender, app_data, user_data):
        with dpg.window(label=user_data.get('header'), autosize=True):
            with dpg.table(header_row=False, pad_outerX=True) as t:
                dpg.add_table_column(label="key", width_fixed=True)
                dpg.add_table_column(label="value")
                with dpg.table_row():
                    dpg.add_button(label="Expand", user_data=t, callback=self.callback_expand_item)

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

    def callback_expand_item(self, sender, app_data, user_data):
        rows = dpg.get_item_children(user_data, 1)[1:]
        if dpg.get_item_configuration(sender).get('label') == "Expand":
            [dpg.configure_item(r, show=True) for r in rows]
            dpg.configure_item(sender, label="Collapse")
        else:
            [dpg.configure_item(r, show=dpg.get_item_user_data(r)) for r in rows]
            dpg.configure_item(sender, label="Expand")
