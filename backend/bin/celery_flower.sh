#!/bin/bash
exec celery flower --app zac_lite --workdir src
