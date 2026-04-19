import dagster as dg
import psycopg2
from contextlib import contextmanager

class PostgresResource(dg.ConfigurableResource):
    host: str
    port: int
    user: str
    password: str
    dbname: str

    @contextmanager
    def get_connection(self):
        conn = psycopg2.connect(
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password,
            dbname=self.dbname
        )
        try:
            yield conn
        finally:
            conn.close()

    def get_conn_string(self):
        return f'postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.dbname}?sslmode=disable'