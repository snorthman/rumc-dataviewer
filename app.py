import threading, os, json

import viewer.tools as tools
import viewer.GUI as GUI

def run():
    dataviewer = GUI.Viewer(tools.filedialog)
    threading.Thread(target=dataviewer.run).start()
    tools.filedialog.process()


if __name__ == '__main__':
    run()
