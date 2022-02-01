import threading, os, sys, argparse, queue

import viewer.tools as tools
import viewer.GUI as GUI

def run():
    parser = argparse.ArgumentParser(description="View data downloaded from RUMC", )
    parser.add_argument('-s', '--scan', help="Path to RUMC patient level data")
    args = parser.parse_args()
    if args.scan is not None:
        Q = queue.Queue()
        t = len(os.listdir(args.scan))
        threading.Thread(target=tools.scan_data, args=(args.scan, os.getcwd(), Q)).start()
        while True:
            q = Q.get()
            if q <= 0:
                break
            percent = round(100 * q / t)
            arrow = '-' * int(percent / 100 * 20 - 1) + '>'
            spaces = ' ' * (20 - len(arrow))
            print('Progress: [%s%s] %d %%' % (arrow, spaces, percent), end='\r')
        print(f'Scan complete, wrote result to {os.getcwd()}', end='\r')
        quit(0)

    # no opts? -> create GUI

    dataviewer = GUI.Viewer(tools.filedialog)
    threading.Thread(target=dataviewer.run).start()
    tools.filedialog.process()


if __name__ == '__main__':
    run()
