from quart import Quart
from quart_graphql import AsyncGraphQLView
from .schema import Schema
from graphql import GraphQLCachedBackend


def create_app(path="/graphql", **kwargs):
    backend = None
    app = Quart(__name__)
    app.debug = True
    app.config['TESTING'] = True
    app.add_url_rule(
        path,
        view_func=AsyncGraphQLView.as_view(
            "graphql", schema=Schema, backend=backend, **kwargs
        ),
    )
    return app


if __name__ == "__main__":
    app = create_app(graphiql=True)
    app.run()
