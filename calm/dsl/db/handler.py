import atexit

from calm.dsl.config import get_init_data
from .table_config import dsl_database, SecretTable, DataTable, CacheTable, VersionTable
from calm.dsl.tools import get_logging_handle

LOG = get_logging_handle(__name__)


class Database:
    """DSL database connection"""

    db = None

    @classmethod
    def update_db(cls, db_instance):
        cls.db = db_instance

    @staticmethod
    def instantiate_db():
        init_obj = get_init_data()
        db_location = init_obj["DB"].get("location")
        dsl_database.init(db_location)
        return dsl_database

    def __init__(self):
        if not self.db:
            self.update_db(self.instantiate_db())

        self.connect()
        self.secret_table = self.set_and_verify(SecretTable)
        self.data_table = self.set_and_verify(DataTable)
        self.cache_table = self.set_and_verify(CacheTable)
        self.version_table = self.set_and_verify(VersionTable)

    def set_and_verify(self, table_cls):
        """ Verify whether this class exists in db
            If not, then creates one
        """

        if not self.db.table_exists((table_cls.__name__).lower()):
            self.db.create_tables([table_cls])

        return table_cls

    def connect(self):

        LOG.debug("Connecting to local DB")
        self.db.connect()
        atexit.register(self.close)
        LOG.debug("Success")

    def close(self):

        LOG.debug("Closing connection to local DB")
        self.db.close()
        LOG.debug("Success")


_Database = None


def get_db_handle():
    """Returns the db handle"""

    global _Database
    if not _Database:
        _Database = Database()

    return _Database
