Apache + mod-wsgi configuration
===============================

An example Apache2 vhost configuration follows::

    WSGIDaemonProcess zac_lite-<target> threads=5 maximum-requests=1000 user=<user> group=staff
    WSGIRestrictStdout Off

    <VirtualHost *:80>
        ServerName my.domain.name

        ErrorLog "/srv/sites/zac_lite/log/apache2/error.log"
        CustomLog "/srv/sites/zac_lite/log/apache2/access.log" common

        WSGIProcessGroup zac_lite-<target>

        Alias /media "/srv/sites/zac_lite/media/"
        Alias /static "/srv/sites/zac_lite/static/"

        WSGIScriptAlias / "/srv/sites/zac_lite/src/zac_lite/wsgi/wsgi_<target>.py"
    </VirtualHost>


Nginx + uwsgi + supervisor configuration
========================================

Supervisor/uwsgi:
-----------------

.. code::

    [program:uwsgi-zac_lite-<target>]
    user = <user>
    command = /srv/sites/zac_lite/env/bin/uwsgi --socket 127.0.0.1:8001 --wsgi-file /srv/sites/zac_lite/src/zac_lite/wsgi/wsgi_<target>.py
    home = /srv/sites/zac_lite/env
    master = true
    processes = 8
    harakiri = 600
    autostart = true
    autorestart = true
    stderr_logfile = /srv/sites/zac_lite/log/uwsgi_err.log
    stdout_logfile = /srv/sites/zac_lite/log/uwsgi_out.log
    stopsignal = QUIT

Nginx
-----

.. code::

    upstream django_zac_lite_<target> {
      ip_hash;
      server 127.0.0.1:8001;
    }

    server {
      listen :80;
      server_name  my.domain.name;

      access_log /srv/sites/zac_lite/log/nginx-access.log;
      error_log /srv/sites/zac_lite/log/nginx-error.log;

      location /500.html {
        root /srv/sites/zac_lite/src/zac_lite/templates/;
      }
      error_page 500 502 503 504 /500.html;

      location /static/ {
        alias /srv/sites/zac_lite/static/;
        expires 30d;
      }

      location /media/ {
        alias /srv/sites/zac_lite/media/;
        expires 30d;
      }

      location / {
        uwsgi_pass django_zac_lite_<target>;
      }
    }
