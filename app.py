import threading, os, sys, getopt, queue

import viewer

def main(argv):
    try:
        opts, args = getopt.getopt(argv, "hs", ["help=", "scan="])
    except getopt.GetoptError:
        print('viewer.py -h')
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print('test.py -s <target dir> (no args opens the GUI)')
            sys.exit()
        elif opt in ("-s", "--scan"):
            Q = queue.Queue()
            t = len(os.listdir(arg))
            threading.Thread(target=viewer.tools.scan_data, args=(arg, os.getcwd(), Q))
            while True:
                q = Q.get()
                if q == -1:
                    break
                percent = round(100 * q / t)
                arrow = '-' * int(percent / 100 * 20 - 1) + '>'
                spaces = ' ' * (20 - len(arrow))
                print('Progress: [%s%s] %d %%' % (arrow, spaces, percent), end='\r')
            print('Scan complete, wrote result to ', os.getcwd())
            quit(0)

    # no opts? -> create GUI

    dataviewer = viewer.GUI.Viewer(viewer.tools.filedialog)
    threading.Thread(target=dataviewer.run).start()
    viewer.tools.filedialog.process()


if __name__ == '__main__':
    main(sys.argv[1:])
