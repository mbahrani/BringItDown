import click
import requests
import threading
from appJar import gui
import time;

progress = dict()
thread_progress = dict()
chunks = dict()
dl_id_counter = 0

def start_gui():
    def threaded_button_handler(button):
        if button == "Start":
            url = app.getEntry("urlEntry")
            name = app.getEntry("nameEntry")
            dir = app.getEntry("dirEntry")
            if len(name.split()) == 0:
                download_file(app,url)
            download_file(app,url, dest=dir + "/" + name)
        else:
            pass

    def button_handler(button):
        t = threading.Thread(target=threaded_button_handler,
                             kwargs={"button": button})
        t.setDaemon(True)
        t.start()

    app = gui()
    app.setTitle("BringItDown")
    app.setGeometry(300, 300)
    app.setResizable(canResize=True)
    app.startLabelFrame("New Download")
    app.setSticky("ew")
    app.addLabel("Download Link", "Download Link", 0, 0)
    app.addEntry("urlEntry", 0, 1)
    app.addLabel("File Name", "filename",1,0)
    app.addEntry("nameEntry", 1, 1)
    app.addDirectoryEntry("dirEntry",2,0,2)
    app.addButtons(["Start"],button_handler,3,0,2)
    app.stopLabelFrame()
    app.startTabbedFrame("Downloads")
    app.stopTabbedFrame()
    app.go()


def Handler(url, filename, dl_id, help_others=True):
    # specify the starting and ending of the file
    me = threading.current_thread();
    start = chunks[dl_id][me][0]
    end = chunks[dl_id][me][1]
    thread_progress[me]=0
    headers = {'Range': 'bytes=%d-%d' % (start, end)}

    # request the specified part and get into variable
    r = requests.get(url, headers=headers, stream=True)

    # open the file and write the content of the html page
    # into file.
    tot = 0
    with open(filename, "r+b") as fp:
        fp.seek(start)
        for data in r.iter_content(chunk_size=4096):
            start = chunks[dl_id][me][0]
            end = chunks[dl_id][me][1]
            if tot >= end - start:
                r.close()
                break
            var = fp.tell()
            fp.write(data)
            tot += len(data)
            progress[dl_id] += len(data)
            thread_progress[me] = tot
            #if ((tot*100)//(end-start)) % 10 == 0:
                #print(threading.current_thread().getName())
                #print("---Progress % "+str(tot*100//(end-start)))

    if help_others:
        best_thread = me
        mn = 1
        for key, values in chunks[dl_id].items():
            if thread_progress[key]/(values[1]-values[0]) < mn:
                mn = thread_progress[key]/(values[1]-values[0])
                best_thread = key
        if best_thread != me:
            new_end = (chunks[dl_id][best_thread][1]+thread_progress[best_thread])//2
            end = chunks[dl_id][best_thread][1]
            chunks[dl_id][best_thread] = (chunks[dl_id][best_thread][0], new_end)
            chunks[dl_id][me] = (new_end, end)
            print("Dbug Info"+str(me))
            Handler(url, filename, dl_id, False)


def download_file(app,url, dest=""):
    number_of_threads = 8
    r = requests.head(url)
    if dest != "":
        file_name = dest
    else:
        file_name = url.split('/')[-1]
    try:
        file_size = int(r.headers['content-length'])
    except:
        print("Invalid URL")
        return

    part = int(file_size) // number_of_threads
    fp = open(file_name, "wb")
    fp.write(('\0' * file_size).encode())
    fp.close()
    global dl_id_counter
    dl_id = dl_id_counter+1
    dl_id_counter += 1
    progress[dl_id] = 0

    #GUI
    app.openTabbedFrame("Downloads")
    tabname = str(dl_id)+"-"+file_name.split("/")[-1]
    app.startTab(tabname)
    app.addMeter(tabname+"progress")
    app.setMeter(tabname+"progress",0)
    app.addLabel(tabname+"speed label","Cur Speed: %d, Avg Speed %d"%(0,0))
    helper = [time.time(), time.time(), 0]

    def update_meter():
        if helper[2] >= file_size:
            return

        curspeed = (progress[dl_id]-helper[2])/(time.time()-helper[1])/1000
        avgspeed = (progress[dl_id])/(time.time()-helper[0])/1000
        helper[1]=time.time()
        helper[2]=progress[dl_id]
        app.setMeter(tabname + "progress", (progress[dl_id]/file_size)*100)
        app.setLabel(tabname+"speed label","Cur Speed: %d KB/s, Avg Speed %d KB/s " % (curspeed, avgspeed))

    app.registerEvent(update_meter)
    app.stopTab()
    app.stopTabbedFrame()

    chunks[dl_id] = dict()
    my_chunks = chunks[dl_id]
    list_threads = list()
    for i in range(number_of_threads):
        start = part * i
        end = start + part
        if i == number_of_threads-1:
            end = file_size
        # create a Thread with start and end locations
        t = threading.Thread(target=Handler,
                             kwargs={'url': url, 'filename': file_name, "dl_id": dl_id})
        my_chunks[t] = (start, end)
        t.setDaemon(True)
        list_threads.append(t)
        t.start()

    #main_thread = threading.current_thread()
    for t in list_threads:
        t.join()
    print('%s downloaded' % file_name)

if __name__ == "__main__":
    start_gui()

