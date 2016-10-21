# yandex-disk-client
Unofficial Yandex.Disk synchronization client  

Project discussion (russian): http://forum.ubuntu.ru/index.php?topic=282770

Files:

OAuth.py - Yandex OAuth authorisation via verification code (CLI/GUI) + tests - completed

jconfig.py - configuration object (dict | file in JSON) + tests - completed

Cloud.py - wraper class for YD rest API + tests - completed (but still is beeing amended)

PoolExecutor.py - modified concurrent.futures.ThreadPoolExecutor - completed
   * added method unfinished() - the number of unfinished tasks (which are currently executed and wait in queue). It's required for executor status control (when unfinished returns 0 then executor is in the idle state).
   * new working thread is created when number of existing threads is less than maximum allowed and if the number of unfinished tasks greater than number of threads.

xmpp.py - some samples of xmpp client - draft

pyinotify.py - fixed version (see https://github.com/seb-m/pyinotify/pull/135)

Disk.py - primary YD client class - in progress (iNotify events handling - done, status tracking - done, fullSync with history data - done, xmpp client events handling - not started)
