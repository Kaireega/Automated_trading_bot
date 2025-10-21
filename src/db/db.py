import os
from pymongo import MongoClient, errors
import certifi

class DataDB:

    SAMPLE_COLL = "forex_sample"
    CALENDAR_COLL = "forex_calendar"
    INSTRUMENTS_COLL = "forex_instruments"

    def __init__(self, uri: str | None = None, db_name: str = "forex_learning"):
        # Prefer env var; fallback to provided uri
        self._uri = uri or os.getenv('MONGODB_URI')
        if not self._uri:
            raise ValueError("MONGODB_URI is required for database connectivity")
        self._db_name = db_name
        self.client = None
        self.db = None
        self._connect()

    def _connect(self):
        # Secure TLS with certifi CA bundle; enable pooling
        # Use tlsAllowInvalidCertificates=True for macOS compatibility
        self.client = MongoClient(
            self._uri,
            tls=True,
            tlsAllowInvalidCertificates=True,  # For macOS SSL certificate issues
            serverSelectionTimeoutMS=20000,
            connectTimeoutMS=20000,
            socketTimeoutMS=20000,
            maxPoolSize=10,
            retryWrites=True,
        )
        self.db = self.client[self._db_name]

    def ping(self) -> bool:
        try:
            self.client.admin.command('ping')
            return True
        except Exception:
            try:
                self._connect()
                self.client.admin.command('ping')
                return True
            except Exception:
                return False


    def test_connection(self):
        try:
            ok = self.ping()
            if ok:
                print(self.db.list_collection_names())
            else:
                print("Database ping failed")
        except Exception as e:
            print(f"DB test_connection error: {e}")

    
    def delete_many(self, collection, **kwargs):
        try:
            _ = self.db[collection].delete_many(kwargs)
        except errors.InvalidOperation as error:
            print("delete_many error:", error)


    def add_one(self, collection, ob):
        try:
            _ = self.db[collection].insert_one(ob)
        except errors.InvalidOperation as error:
            print("add_one error:", error)


    def add_many(self, collection, list_ob):
        try:
            _ = self.db[collection].insert_many(list_ob)
        except errors.InvalidOperation as error:
            print("add_many error:", error)


    def query_distinct(self, collection, key):
        try:            
            return self.db[collection].distinct(key)
        except errors.InvalidOperation as error:
            print("query_distinct error:", error) 
    
    
    def query_single(self, collection, **kwargs):
        try:            
            r = self.db[collection].find_one(kwargs, {'_id':0})
            return r
        except errors.InvalidOperation as error:
            print("query_single error:", error)


    def query_all(self, collection, **kwargs):
        try:
            data = []
            r = self.db[collection].find(kwargs, {'_id':0})
            for item in r:
                data.append(item)
            return data
        except errors.InvalidOperation as error:
            print("query_all error:", error)

































