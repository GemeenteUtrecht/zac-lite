from zgw_consumers.client import Client
from zgw_consumers.nlx import NLXClientMixin


class NLXClient(NLXClientMixin, Client):
    pass
