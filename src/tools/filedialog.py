import os
import threading, queue
import tkinter as tk
from tkinter import filedialog as fd

root = tk.Tk()
root.withdraw()

class FileDialog:
    def __init__(self):
        self._q1 = queue.Queue()
        self._q2 = queue.Queue()

    def end_process(self):
        self._q1.put('Q')

    def _dialog(self, key):
        self._q1.put(key)
        q = self._q2.get()
        return q

    def dialog_json(self):
        return os.path.normpath(self._dialog('j'))

    def dialog_dir(self):
        return os.path.normpath(self._dialog('d'))

    def process(self):
        while True:
            q = self._q1.get()
            if q == 'j':
                self._q2.put(fd.askopenfilename(filetypes=[("json files","*.json")]))
            if q == 'd':
                self._q2.put(fd.askdirectory(mustexist=True))
            if q == 'Q':
                break

filedialog = FileDialog()
