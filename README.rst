Dropbox Time Machine - RETIRED!
==============================================================================

.. DANGER::

    Dropbox recently changed their API which effectively breaks this system. It can be fixed but I have neither the time nor the interest to do so at this time.

An app that adds a time machine feature to Dropbox, instead of restoring per
file you can simply jump back in time (before some idiot deleted all files for
example) and restore all files deleted within that period.

Demo
------------------------------------------------------------------------------

A working implementation can be found on: http://dropbox.wol.ph/

Usage
------------------------------------------------------------------------------

 1. Copy the `example_settings.py` in the `dropbox_timemachine` to
     `settings.py` and change the broker settings and your Dropbox application
     information.

 2. Install all requirements `pip install -r requirements.txt`

 3. Run flask (the `web.py` file, see http://flask.pocoo.org/docs/deploying/
     for other deployment options.

 4. Run celery `celeryd --config settings -I tasks` (I recommend running it
     through `supervisord`)


Questions? 
------------------------------------------------------------------------------

Just create an issue at Github
(https://github.com/WoLpH/dropbox-time-machine/issues) or send me a mail. 

