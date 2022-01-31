import os, threading, queue, time

import dearpygui.dearpygui as dpg

import viewer.tools as tools



class Scan:
    def __init__(self, path):
        self.dir = path
        if os.path.exists(self.dir):
            self.total = len(os.listdir(self.dir))
            with dpg.window(label="Scan ()", no_resize=True, autosize=True) as self.w:
                with dpg.drawlist(width=500, height=30):
                    with dpg.draw_layer():
                        self.rect = dpg.draw_rectangle(pmin=(0, 0), pmax=(0, 30), fill=(0, 192, 0))
                    with dpg.draw_layer():
                        dpg.draw_rectangle(pmin=(0, 0), pmax=(500, 30), color=(192, 192, 192))
                self.progress = dpg.add_text(default_value=f"0/{self.total} scanned")
                self.eta = dpg.add_text(default_value="ETA\t")
                self.log = dpg.add_listbox(items=["Scanning " + path], width=500, num_items=1)
            self.Q = queue.Queue()

    def run(self):
        threading.Thread(target=tools.scan_data, args=(self.dir, os.getcwd(), self.Q)).start()
        threading.Thread(target=self._update_scan_data).start()

    def _update_scan_data(self):
        v = []
        while True:
            t = time.time()
            q = self.Q.get()
            if q <= 0:
                i = dpg.get_item_configuration(self.log)['items']
                if q == -1: # bad directory
                    dpg.configure_item(self.w, label="Scan (ERROR)")
                    dpg.configure_item(self.log, items=i + ["ERROR: Directory does not contain a valid patient dataset"], num_items=len(i) + 1)
                    return
                if q <= -2: # bad patient
                    dpg.configure_item(self.log, items=i + [f"ERROR: patient {-1 * q}"], num_items=len(i) + 1)
                break
            p = q / self.total
            v.append(time.time() - t)
            dpg.configure_item(self.rect, pmax=(p * 500, 30))
            dpg.configure_item(self.w, label=f"Scan ({round(p * 100, 1)}%)")
            dpg.configure_item(self.progress, default_value=f"{q}/{self.total} scanned")
            ss = (sum(v) / len(v)) * (self.total - q)
            mm = ss // 60
            hh = mm // 60
            dpg.configure_item(self.eta, default_value=f"ETA\t{'%02d:%02d:%02d' % (hh, mm % 60, ss % 60)}")

        i = dpg.get_item_configuration(self.log)['items']
        dpg.configure_item(self.log, items=i + ["Scan complete"], num_items=len(i) + 1)
        dpg.add_text(parent=self.w, default_value="Results saved in:")
        dpg.add_input_text(parent=self.w, default_value=os.getcwd(), readonly=True, width=500)
