import json
import typing
from io import StringIO
from urllib.parse import urlencode

import pytest
from quart import Quart, Response, url_for
from quart.testing import QuartClient

from tests.app import create_app


@pytest.fixture
async def app(request) -> Quart:
    app = create_app()
    ctx = app.app_context()
    await ctx.push()
    return app


@pytest.fixture
def client(app: Quart) -> QuartClient:
    return app.test_client()


async def url_string(app: Quart, url_params: typing.Dict) -> str:
    async with app.test_request_context("/"):
        string = url_for("graphql")
        if url_params:
            string += "?" + urlencode(url_params)
        return string


async def response_json(response: Response) -> typing.Dict:
    return json.loads(await response.get_data())


@pytest.mark.asyncio
async def test_allows_get_with_query_param(
    app: Quart, client: QuartClient
) -> typing.NoReturn:
    async with app.test_request_context("/"):
        response = await client.get(await url_string(app, {"query": "{test}"}))
        assert response.status_code == 200
        assert (await response_json(response)) == {"data": {"test": "Hello World"}}


@pytest.mark.asyncio
async def test_allows_get_with_variable_values(
    app: Quart, client: QuartClient
) -> typing.NoReturn:
    async with app.test_request_context("/"):
        response = await client.get(
            await url_string(
                app,
                {
                    "query": "query helloWho($who: String){ test(who: $who) }",
                    "variables": json.dumps({"who": "Dolly"}),
                },
            )
        )
        assert response.status_code == 200
        assert await (response_json(response)) == {"data": {"test": "Hello Dolly"}}


@pytest.mark.asyncio
async def test_allows_get_with_operation_name(
    app: Quart, client: QuartClient
) -> typing.NoReturn:
    async with app.test_request_context("/"):
        response = await client.get(
            await url_string(
                app,
                {
                    "query": """
                query helloYou { test(who: "You"), ...shared }
                query helloWorld { test(who: "World"), ...shared }
                query helloDolly { test(who: "Dolly"), ...shared }
                fragment shared on QueryRoot {
                  shared: test(who: "Everyone")
                }
                """,
                    "operationName": "helloWorld",
                },
            )
        )
        assert response.status_code == 200
        assert (await response_json(response)) == {
            "data": {"test": "Hello World", "shared": "Hello Everyone"}
        }


@pytest.mark.asyncio
async def test_reports_validation_errors(
    app: Quart, client: QuartClient
) -> typing.NoReturn:
    async with app.test_request_context("/"):
        response = await client.get(
            await url_string(app, {"query": "{ test, unknownOne, unknownTwo }"})
        )
        assert response.status_code == 400
        assert (await response_json(response)) == {
            "errors": [
                {
                    "message": 'Cannot query field "unknownOne" on type "QueryRoot".',
                    "locations": [{"line": 1, "column": 9}],
                },
                {
                    "message": 'Cannot query field "unknownTwo" on type "QueryRoot".',
                    "locations": [{"line": 1, "column": 21}],
                },
            ]
        }


@pytest.mark.asyncio
async def test_errors_when_missing_operation_name(
    app: Quart, client: QuartClient
) -> typing.NoReturn:
    async with app.test_request_context("/"):
        response = await client.get(
            await url_string(
                app,
                {
                    "query": """
            query TestQuery { test }
            mutation TestMutation { writeTest { test } }
            """
                },
            )
        )
        assert response.status_code == 400
        assert (await response_json(response)) == {
            "errors": [
                {
                    "message": "Must provide operation name if query contains multiple operations."
                }
            ]
        }


@pytest.mark.asyncio
async def test_errors_when_sending_a_mutation_via_get(
    app: Quart, client: QuartClient
) -> typing.NoReturn:
    async with app.test_request_context("/"):
        response = await client.get(
            await url_string(
                app,
                {
                    "query": """
            mutation TestMutation { writeTest { test } }
            """
                },
            )
        )
        assert response.status_code == 405
        assert (await response_json(response)) == {
            "errors": [
                {
                    "message": "Can only perform a mutation operation from a POST request."
                }
            ]
        }


@pytest.mark.asyncio
async def test_errors_when_selecting_a_mutation_within_a_get(
    app: Quart, client: QuartClient
) -> typing.NoReturn:
    async with app.test_request_context("/"):
        response = await client.get(
            await url_string(
                app,
                {
                    "query": """
            query TestQuery { test }
            mutation TestMutation { writeTest { test } }
            """,
                    "operationName": "TestMutation",
                },
            )
        )
        assert response.status_code == 405
        assert (await response_json(response)) == {
            "errors": [
                {
                    "message": "Can only perform a mutation operation from a POST request."
                }
            ]
        }


@pytest.mark.asyncio
async def test_allows_mutation_to_exist_within_a_get(
    app: Quart, client: QuartClient
) -> typing.NoReturn:
    async with app.test_request_context("/"):
        response = await client.get(
            await url_string(
                app,
                {
                    "query": """
                query TestQuery { test }
                mutation TestMutation { writeTest { test } }
                """,
                    "operationName": "TestQuery",
                },
            )
        )
        assert response.status_code == 200
        assert await (response_json(response)) == {"data": {"test": "Hello World"}}


@pytest.mark.asyncio
async def test_allows_post_with_json_encoding(
    app: Quart, client: QuartClient
) -> typing.NoReturn:
    async with app.test_request_context("/"):
        response = await client.open(
            method="POST", path=(await url_string(app, {})), json={"query": "{test}"}
        )
        assert response.status_code == 200
        assert (await response_json(response)) == {"data": {"test": "Hello World"}}


@pytest.mark.asyncio
async def test_allows_sending_a_mutation_via_post(
    app: Quart, client: QuartClient
) -> typing.NoReturn:
    async with app.test_request_context("/"):
        response = await client.post(
            path=(await url_string(app, {})),
            json=({"query": "mutation TestMutation { writeTest { test } }"}),
        )
        assert response.status_code == 200
        assert (await response_json(response)) == {
            "data": {"writeTest": {"test": "Hello World"}}
        }


@pytest.mark.asyncio
async def test_allows_post_with_url_encoding(
    app: Quart, client: QuartClient
) -> typing.NoReturn:
    async with app.test_request_context("/"):
        response = await client.post(
            path=(await url_string(app, {})),
            data=urlencode({"query": "{test}"}),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert response.status_code == 200
        assert (await response_json(response)) == {"data": {"test": "Hello World"}}


@pytest.mark.asyncio
async def test_supports_post_json_query_with_string_variables(
    app: Quart, client: QuartClient
) -> typing.NoReturn:
    async with app.test_request_context("/"):
        response = await client.post(
            path=(await url_string(app, {})),
            json={
                "query": "query helloWho($who: String){ test(who: $who) }",
                "variables": json.dumps({"who": "Dolly"}),
            },
        )
        assert response.status_code == 200
        assert (await response_json(response)) == {"data": {"test": "Hello Dolly"}}


@pytest.mark.asyncio
async def test_supports_post_json_query_with_json_variables(
    app: Quart, client: QuartClient
) -> typing.NoReturn:
    async with app.test_request_context("/"):
        response = await client.post(
            path=(await url_string(app, {})),
            json=(
                {
                    "query": "query helloWho($who: String){ test(who: $who) }",
                    "variables": {"who": "Dolly"},
                }
            ),
        )
        assert response.status_code == 200
        assert (await response_json(response)) == {"data": {"test": "Hello Dolly"}}


@pytest.mark.asyncio
async def test_supports_post_url_encoded_query_with_string_variables(
    app: Quart, client: QuartClient
) -> typing.NoReturn:
    async with app.test_request_context("/"):
        response = await client.post(
            path=(await url_string(app, {})),
            data=urlencode(
                {
                    "query": "query helloWho($who: String){ test(who: $who) }",
                    "variables": json.dumps({"who": "Dolly"}),
                }
            ),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert response.status_code == 200
        assert (await response_json(response)) == {"data": {"test": "Hello Dolly"}}


@pytest.mark.asyncio
async def test_supports_post_json_quey_with_get_variable_values(
    app: Quart, client: QuartClient
) -> typing.NoReturn:
    async with app.test_request_context("/"):
        response = await client.post(
            path=(await url_string(app, {"variables": json.dumps({"who": "Dolly"})})),
            json=({"query": "query helloWho($who: String){ test(who: $who) }"}),
        )

        assert response.status_code == 200
        assert (await response_json(response)) == {"data": {"test": "Hello Dolly"}}


@pytest.mark.asyncio
async def test_post_url_encoded_query_with_get_variable_values(
    app: Quart, client: QuartClient
) -> typing.NoReturn:
    async with app.test_request_context("/"):
        response = await client.post(
            path=(await url_string(app, {"variables": json.dumps({"who": "Dolly"})})),
            data=urlencode(
                {"query": "query helloWho($who: String){ test(who: $who) }"}
            ),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert response.status_code == 200
        assert (await response_json(response)) == {"data": {"test": "Hello Dolly"}}


@pytest.mark.asyncio
async def test_supports_post_raw_text_query_with_get_variable_values(
    app: Quart, client: QuartClient
) -> typing.NoReturn:
    async with app.test_request_context("/"):
        response = await client.post(
            await url_string(app, {"variables": json.dumps({"who": "Dolly"})}),
            data="query helloWho($who: String){ test(who: $who) }",
            headers={"Content-Type": "application/graphql"},
        )
        assert response.status_code == 200
        assert (await response_json(response)) == {"data": {"test": "Hello Dolly"}}


@pytest.mark.asyncio
async def test_allows_post_with_operation_name(
    app: Quart, client: QuartClient
) -> typing.NoReturn:
    async with app.test_request_context("/"):
        response = await client.post(
            path=(await url_string(app, {})),
            json={
                "query": """
                query helloYou { test(who: "You"), ...shared }
                query helloWorld { test(who: "World"), ...shared }
                query helloDolly { test(who: "Dolly"), ...shared }
                fragment shared on QueryRoot {
                  shared: test(who: "Everyone")
                }
                """,
                "operationName": "helloWorld",
            },
        )
        assert response.status_code == 200
        assert (await response_json(response)) == {
            "data": {"test": "Hello World", "shared": "Hello Everyone"}
        }


@pytest.mark.asyncio
async def test_allows_post_with_get_operation_name(
    app: Quart, client: QuartClient
) -> typing.NoReturn:
    async with app.test_request_context("/"):
        response = await client.post(
            path=(await url_string(app, {"operationName": "helloWorld"})),
            data="""
            query helloYou { test(who: "You"), ...shared }
            query helloWorld { test(who: "World"), ...shared }
            query helloDolly { test(who: "Dolly"), ...shared }
            fragment shared on QueryRoot {
              shared: test(who: "Everyone")
            }
            """,
            headers={"Content-Type": "application/graphql"},
        )

        assert response.status_code == 200
        assert (await response_json(response)) == {
            "data": {"test": "Hello World", "shared": "Hello Everyone"}
        }


@pytest.mark.parametrize('app', [create_app(pretty=True)])
@pytest.mark.asyncio
async def test_supports_pretty_printing(
    app: Quart, client: QuartClient
) -> typing.NoReturn:
    async with app.test_request_context("/"):
        response = await client.get(await url_string(app, {'query': '{test}'}))
        assert str(await response.get_data(), 'utf-8') == (
            '{\n'
            '  "data": {\n'
            '    "test": "Hello World"\n'
            '  }\n'
            '}'
        )


@pytest.mark.parametrize('app', [create_app(pretty=False)])
@pytest.mark.asyncio
async def test_not_pretty_by_default(
    app: Quart, client: QuartClient
) -> typing.NoReturn:
    async with app.test_request_context("/"):
        response = await client.get(await url_string(app, {'query': '{test}'}))
        assert str(await response.get_data(), 'utf-8') == (
            '{"data":{"test":"Hello World"}}'
        )


@pytest.mark.asyncio
async def test_supports_pretty_printing_by_request(
    app: Quart, client: QuartClient
) -> typing.NoReturn:
    async with app.test_request_context("/"):
        response = await client.get(
            await url_string(app, {"query": "{test}", "pretty": "1"})
        )
        assert str(await response.get_data(), 'utf-8') == (
            '{\n'
            '  "data": {\n'
            '    "test": "Hello World"\n'
            '  }\n'
            '}'
        )


@pytest.mark.asyncio
async def test_handles_field_errors_caught_by_graphql(
    app: Quart, client: QuartClient
) -> typing.NoReturn:
    async with app.test_request_context("/"):
        response = await client.get(await url_string(app, {"query": "{thrower}"}))
        assert response.status_code == 200
        assert await (response_json(response)) == {
            "data": None,
            "errors": [
                {
                    "locations": [{"column": 2, "line": 1}],
                    "path": ["thrower"],
                    "message": "Throws!",
                }
            ],
        }


@pytest.mark.asyncio
async def test_handles_syntax_errors_caught_by_graphql(
    app: Quart, client: QuartClient
) -> typing.NoReturn:
    async with app.test_request_context("/"):
        response = await client.get(await url_string(app, {"query": "syntaxerror"}))
        assert response.status_code == 400
        assert (await response_json(response)) == {
            "errors": [
                {
                    "locations": [{"column": 1, "line": 1}],
                    "message": "Syntax Error GraphQL (1:1) "
                    'Unexpected Name "syntaxerror"\n\n1: syntaxerror\n   ^\n',
                }
            ]
        }


@pytest.mark.asyncio
async def test_handles_errors_caused_by_a_lack_of_query(
    app: Quart, client: QuartClient
) -> typing.NoReturn:
    async with app.test_request_context("/"):
        response = await client.get(await url_string(app, {}))
        assert response.status_code == 400
        assert await (response_json(response)) == {
            "errors": [{"message": "Must provide query string."}]
        }


@pytest.mark.asyncio
async def test_graphql_params_should_be_dict(
    app: Quart, client: QuartClient
) -> typing.NoReturn:
    async with app.test_request_context("/"):
        response = await client.post(await url_string(app, {}), json="[]")
        assert response.status_code == 400
        assert await (response_json(response)) == {
            "errors": [{"message": "GraphQL params should be a dict. Received '[]'."}]
        }


@pytest.mark.asyncio
async def test_handles_batch_correctly_if_is_disabled(
    app: Quart, client: QuartClient
) -> typing.NoReturn:
    async with app.test_request_context("/"):
        response = await client.post(
            await url_string(app, {}),
            data="[{}]",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 400
        assert await (response_json(response)) == {
            "errors": [{"message": "Batch GraphQL requests are not enabled."}]
        }


@pytest.mark.asyncio
async def test_handles_incomplete_json_bodies(
    app: Quart, client: QuartClient
) -> typing.NoReturn:
    async with app.test_request_context("/"):
        response = await client.post(
            await url_string(app, {}),
            data='{"query":',
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 400
        assert (await response_json(response)) == {
            "errors": [{"message": "POST body sent invalid JSON."}]
        }


@pytest.mark.asyncio
async def test_handles_plain_post_text(
    app: Quart, client: QuartClient
) -> typing.NoReturn:
    async with app.test_request_context("/"):
        response = await client.post(
            await url_string(app, {"variables": json.dumps({"who": "Dolly"})}),
            data="query helloWho($who: String){ test(who: $who) }",
            headers={"Content-Type": "text/plain"},
        )
        assert response.status_code == 400
        assert (await response_json(response)) == {
            "errors": [{"message": "Must provide query string."}]
        }


@pytest.mark.asyncio
async def test_handles_poorly_formed_variables(
    app: Quart, client: QuartClient
) -> typing.NoReturn:
    async with app.test_request_context("/"):
        response = await client.get(
            await url_string(
                app,
                {
                    "query": "query helloWho($who: String){ test(who: $who) }",
                    "variables": "who:You",
                },
            )
        )
        assert response.status_code == 400
        assert await (response_json(response)) == {
            "errors": [{"message": "Variables are invalid JSON."}]
        }


@pytest.mark.asyncio
async def test_handles_unsupported_http_methods(
    app: Quart, client: QuartClient
) -> typing.NoReturn:
    async with app.test_request_context("/"):
        response = await client.put(await url_string(app, {"query": "{test}"}))
        assert response.status_code == 405
        assert response.headers["Allow"] in ["GET, POST", "HEAD, GET, POST, OPTIONS"]
        assert await (response_json(response)) == {
            "errors": [{"message": "GraphQL only supports GET and POST requests."}]
        }


@pytest.mark.asyncio
async def test_passes_request_into_request_context(
    app: Quart, client: QuartClient
) -> typing.NoReturn:
    async with app.test_request_context("/"):
        response = await client.get(
            await url_string(app, {"query": "{request}", "q": "testing"})
        )
        assert response.status_code == 200
        assert (await response_json(response)) == {"data": {"request": "testing"}}


@pytest.mark.parametrize('app', [create_app(get_context=lambda:"CUSTOM CONTEXT")])
@pytest.mark.asyncio
async def test_supports_pretty_printing(
    app: Quart, client: QuartClient
) -> typing.NoReturn:
    async with app.test_request_context("/"):
        response = await client.get(await url_string(app, {'query': '{context}'}))
        assert response.status_code == 200
        assert (await response_json(response)) == {
            'data': {
                'context': 'CUSTOM CONTEXT'
            }
        }


@pytest.mark.asyncio
async def test_post_multipart_data(app: Quart, client: QuartClient) -> typing.NoReturn:
    async with app.test_request_context("/"):
        query = "mutation TestMutation { writeTest { test } }"
        data = ('------quartgraphql\r\n' +
                'Content-Disposition: form-data; name="query"\r\n' +
                '\r\n' +
                query + '\r\n' +
                '------quartgraphql--\r\n' +
                'Content-Type: text/plain; charset=utf-8\r\n' +
                'Content-Disposition: form-data; name="file"; filename="text1.txt"; filename*=utf-8\'\'text1.txt\r\n' +
                '\r\n' +
                '\r\n' +
                '------quartgraphql--\r\n'
        )
        response = await client.post(
            await url_string(app, {}),
            data=data,
            headers={'content-type': 'multipart/form-data; boundary=----quartgraphql'}
        )
        assert response.status_code == 200
        assert (await response_json(response)) == {
            "data": {u"writeTest": {u"test": u"Hello World"}}
        }


@pytest.mark.parametrize('app', [create_app(batch=True)])
@pytest.mark.asyncio
async def test_batch_allows_post_with_json_encoding(
    app: Quart, client: QuartClient
) -> typing.NoReturn:
    async with app.test_request_context("/"):
        response = await client.post(
            await url_string(app, {}), json=[{'query': "{test}"}])
        assert response.status_code == 200
        assert (await response_json(response)) == [
            {
                "data": {"test": "Hello World"}
            }
        ]


@pytest.mark.parametrize('app', [create_app(batch=True)])
@pytest.mark.asyncio
async def test_batch_supports_post_json_query_with_json_variables(
    app: Quart, client: QuartClient
) -> typing.NoReturn:
    async with app.test_request_context("/"):
        response = await client.post(
            await url_string(app, {}),
            json=[{
                'query': "query helloWho($who: String){ test(who: $who) }",
                'variables': {"who": "Dolly"},
            }]
        )

        assert response.status_code == 200
        assert (await response_json(response)) == [
            {
                "data": {"test": "Hello Dolly"}
            }
        ]


@pytest.mark.parametrize('app', [create_app(batch=True)])
@pytest.mark.asyncio
async def test_batch_allows_post_with_operation_name(
    app: Quart,
    client: QuartClient
) -> typing.NoReturn:
    async with app.test_request_context("/"):
        response = await client.post(
            await url_string(app, {}),
            data=json.dumps([{'query': """
                query helloYou { test(who: "You"), ...shared }
                query helloWorld { test(who: "World"), ...shared }
                query helloDolly { test(who: "Dolly"), ...shared }
                fragment shared on QueryRoot {
                  shared: test(who: "Everyone")
                }
                """,
                'operationName': "helloWorld"}]),
                headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 200
        assert (await response_json(response)) == [
            {
                "data": {"test": "Hello World", "shared": "Hello Everyone"}
            }
        ]
