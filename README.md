Mapping Session Handler Daemon
==================================

MASHd is a small python program that tries to restore the mapping network
established between device peers using [libmapper](http://libmapper.org)
in scenarios where devices are relaunched after crashing or shutting down.
After a configurable timeout period records for inactive devices are
flushed from memory.

to run:

    $ python ./mashd.py

for help and usage:

    $ python ./mashd.py --help

to run with GUI:

    $ python ./mashGUI.py
