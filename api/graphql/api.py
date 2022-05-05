import random
import uvicorn
from ariadne import QueryType, gql, make_executable_schema
from ariadne.asgi import GraphQL
from ariadne import MutationType
from readerwriterlock import rwlock

from graphql_schema import tinyolap_gql, tinyolap_db, random_read, random_write

tiny_lock = rwlock.RWLockWriteD()

type_defs = gql(tinyolap_gql())
query = QueryType()  # Create type instance for Query type defined in our schema...
mutation = MutationType()

database = tinyolap_db()


@query.field("random_read")
def resolve_random_read(_, info):
    global database
    request = info.context["request"]
    with tiny_lock.gen_rlock():
        db, cube, address, value = random_read(database)
        result = {"db": db,
                   "cube": cube,
                   "address": address,
                   "value": value
                   }
    return result


@query.field("random_write")
def resolve_random_read(_, info):
    global database
    request = info.context["request"]
    with tiny_lock.gen_wlock():
        db, cube, address, value = random_write(database)
        result = {"db": db,
                   "cube": cube,
                   "address": address,
                   "value": value
                   }
    return result


@query.field("read")
def resolve_read(_, info, db, cube, address):
    request = info.context["request"]
    with tiny_lock.gen_rlock():
        result = {"db": db,
                   "cube": cube,
                   "address": address,
                   "value": round(random.random() * 1000.0, 0)
                   }
    return result


@mutation.field("write")
def resolve_write(_, info, server, cube, address, value):
    request = info.context["request"]
    with tiny_lock.gen_wlock():
        result = True
    return result


schema = make_executable_schema(type_defs, query)
app = GraphQL(schema, debug=True)

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
