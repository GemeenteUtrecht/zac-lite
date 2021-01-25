========
ZAC Lite
========

:Version: 0.1.0
:Source: https://github.com/GemeenteUtrecht/zac-lite
:Keywords: Zaakgericht werken, Camunda, zaken, Open Zaak
:PythonVersion: 3.8

|build-status| |docs|

User-task interface for "Zaakgericht Werken" processes.

Introduction
============

In the public service space, (business) processes exist to serve *customers*, where
customer is a broad definition of people internal and external to the organization.

One common theme is that the "Zaakgericht Werken" principles are followed to provide
information. The business processes are modeled using BPMN, and they are executable
in the Camunda process engine.

Often, input is required from the customer or other external parties not belonging to
the organization executing/performing the processes.

The ZAC Lite provides the interface to provide this input.

Features are:

* Secure links to input information, without required login, using signed URLs.
* Optional (and future) DigiD, e-Herkenning login
* Simple input form generation from Camunda process models
* Camunda API integration
* Zaakgericht Werken API's integration
* NLX support out of the box

Documentation
=============

See ``INSTALL.rst`` for installation instructions, available settings and
commands.

References
==========

* `Issues <https://github.com/GemeenteUtrecht/zac-lite/issues>`_
* `Code <https://github.com/GemeenteUtrecht/zac-lite>`_

.. |build-status| image:: https://github.com/GemeenteUtrecht/zac-lite/workflows/Run%20CI/badge.svg
    :alt: Build status
    :target: https://github.com/GemeenteUtrecht/zac-lite/actions?query=workflow%3A%22Run+CI%22

.. |docs| image:: https://readthedocs.org/projects/zac-lite/badge/?version=latest
    :target: https://zac-lite.readthedocs.io/en/latest/?badge=latest
    :alt: Documentation Status
