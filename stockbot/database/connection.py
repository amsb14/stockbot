from psycopg2.pool import SimpleConnectionPool
from stockbot.config import PG_DB, PG_USER, PG_PASS, PG_HOST, PG_PORT

PG_POOL = SimpleConnectionPool(
    minconn=1,
    maxconn=8,
    dbname=PG_DB,
    user=PG_USER,
    password=PG_PASS,
    host=PG_HOST,
    port=PG_PORT
)

def get_db_conn():
    """Lease a connection from the pool (remember to put it back)."""
    conn = PG_POOL.getconn()
    conn.autocommit = True
    return conn

def put_db_conn(conn):
    PG_POOL.putconn(conn)
