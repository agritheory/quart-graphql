import typing

import pytest
from quart import Quart, url_for
from quart.testing import QuartClient

from tests.app import create_app


@pytest.fixture
async def app() -> Quart:
    app = create_app(graphiql=True)
    ctx = app.app_context()
    await ctx.push()
    return app


@pytest.fixture
def client(app: Quart) -> QuartClient:
    return app.test_client()


@pytest.mark.asyncio
async def test_graphiql_is_enabled(app: Quart, client: QuartClient) -> typing.NoReturn:
    async with app.test_request_context("/"):
        response = await client.get(
            url_for("graphql", externals=False), headers={"Accept": "text/html"}
        )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_graphiql_renders_pretty(
    app: Quart, client: QuartClient
) -> typing.NoReturn:
    async with app.test_request_context("/"):
        response = await client.get(
            url_for("graphql", query="{test}"), headers={"Accept": "text/html"}
        )
        assert response.status_code == 200
        pretty_response = (
            '{\n'
            '  "data": {\n'
            '    "test": "Hello World"\n'
            '  }\n'
            '}'
        ).replace("\"", "\\\"").replace("\n", "\\n")
        assert pretty_response in str(await response.get_data(), 'utf-8')


@pytest.mark.asyncio
async def test_graphiql_default_title(
    app: Quart, client: QuartClient
) -> typing.NoReturn:
    async with app.test_request_context("/"):
        response = await client.get(url_for("graphql"), headers={"Accept": "text/html"})
        assert "<title>GraphiQL</title>" in str(await response.get_data())


@pytest.mark.parametrize(
    "app", [create_app(graphiql=True, graphiql_html_title="Awesome")]
)
@pytest.mark.asyncio
async def test_graphiql_custom_title(
    app: Quart, client: QuartClient
) -> typing.NoReturn:
    async with app.test_request_context("/"):
        response = await client.get(url_for("graphql"), headers={"Accept": "text/html"})
        data = str(await response.get_data())
        assert "<title>Awesome</title>" in data
