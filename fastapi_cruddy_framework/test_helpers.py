from typing import Any
from requests.cookies import RequestsCookieJar
from async_asgi_testclient.response import Response
from async_asgi_testclient.testing import SimpleCookie, CIMultiDict, sentinel
from async_asgi_testclient.websocket import WebSocketSession
from async_asgi_testclient import TestClient


class BrowserTestClient:
    def __init__(
        self,
        client: TestClient,
        cookies: RequestsCookieJar | SimpleCookie | dict | None = None,
        headers: CIMultiDict | dict | None = None,
    ):
        self.client = client
        self.cookies = cookies
        self.headers = headers
        self.client.cookie_jar = SimpleCookie()

    def _format_cookies(self, cookies: RequestsCookieJar):
        cookie_dictionary: dict = cookies.get_dict()
        new_dict = {}
        # Prune all falsy cookies, as the server wants the browser to remove them
        for k, v in cookie_dictionary.items():
            if v is not None and v != "null" and v is not False:
                new_dict[k] = v
        return new_dict

    # _process_cookies allows each BrowserTestClient to maintain its own
    # internal "cookie" store, so app builders can pretend to be multiple
    # simultaneous users with different session values
    def _process_cookies(self, result: Response) -> Response:
        self.cookies = self._format_cookies(result.cookies)
        self.client.cookie_jar = SimpleCookie()
        return result

    async def open(
        self,
        url: str,
        *,
        method: str = "GET",
        headers: dict | CIMultiDict | None = None,
        data: Any = None,
        form: dict | None = None,
        files: dict | None = None,
        query_string: dict | None = None,
        json: Any = None,
        scheme: str = "http",
        cookies: RequestsCookieJar | SimpleCookie | dict | None = None,
        stream: bool = False,
        allow_redirects: bool = True,
    ):
        use_cookies = cookies if cookies else self.cookies
        use_headers = headers if headers else self.headers
        if isinstance(use_cookies, RequestsCookieJar):
            use_cookies = use_cookies.get_dict()
        if isinstance(use_cookies, SimpleCookie):
            new_dict = {}
            for k, v in use_cookies.items():
                new_dict[k] = v.value
            use_cookies = new_dict
        result = await self.client.open(
            url,
            method=method,
            headers=use_headers,
            data=data,
            form=form,
            files=files,
            query_string=query_string,
            json=sentinel if json is None else json,
            scheme=scheme,
            cookies=use_cookies,
            stream=stream,
            allow_redirects=allow_redirects,
        )
        return self._process_cookies(result)

    async def request(
        self,
        url: str,
        *,
        method: str = "GET",
        headers: dict | CIMultiDict | None = None,
        data: Any = None,
        form: dict | None = None,
        files: dict | None = None,
        query_string: dict | None = None,
        json: Any = None,
        scheme: str = "http",
        cookies: RequestsCookieJar | SimpleCookie | dict | None = None,
        stream: bool = False,
        allow_redirects: bool = True,
    ) -> Response:
        return await self.open(
            url=url,
            method=method,
            headers=headers,
            data=data,
            form=form,
            files=files,
            query_string=query_string,
            json=json,
            scheme=scheme,
            cookies=cookies,
            stream=stream,
            allow_redirects=allow_redirects,
        )

    async def get(  # type: ignore[override]
        self,
        url: str,
        *,
        headers: dict | CIMultiDict | None = None,
        data: Any = None,
        form: dict | None = None,
        files: dict | None = None,
        query_string: dict | None = None,
        json: Any = None,
        scheme: str = "http",
        cookies: RequestsCookieJar | SimpleCookie | dict | None = None,
        stream: bool = False,
        allow_redirects: bool = True,
    ) -> Response:
        return await self.request(
            url=url,
            method="GET",
            headers=headers,
            data=data,
            form=form,
            files=files,
            query_string=query_string,
            json=json,
            scheme=scheme,
            cookies=cookies,
            stream=stream,
            allow_redirects=allow_redirects,
        )

    async def options(  # type: ignore[override]
        self,
        url: str,
        *,
        headers: dict | CIMultiDict | None = None,
        data: Any = None,
        form: dict | None = None,
        files: dict | None = None,
        query_string: dict | None = None,
        json: Any = None,
        scheme: str = "http",
        cookies: RequestsCookieJar | SimpleCookie | dict | None = None,
        stream: bool = False,
        allow_redirects: bool = True,
    ) -> Response:
        return await self.request(
            url=url,
            method="OPTIONS",
            headers=headers,
            data=data,
            form=form,
            files=files,
            query_string=query_string,
            json=json,
            scheme=scheme,
            cookies=cookies,
            stream=stream,
            allow_redirects=allow_redirects,
        )

    async def head(  # type: ignore[override]
        self,
        url: str,
        *,
        headers: dict | CIMultiDict | None = None,
        data: Any = None,
        form: dict | None = None,
        files: dict | None = None,
        query_string: dict | None = None,
        json: Any = None,
        scheme: str = "http",
        cookies: RequestsCookieJar | SimpleCookie | dict | None = None,
        stream: bool = False,
        allow_redirects: bool = True,
    ) -> Response:
        return await self.request(
            url=url,
            method="HEAD",
            headers=headers,
            data=data,
            form=form,
            files=files,
            query_string=query_string,
            json=json,
            scheme=scheme,
            cookies=cookies,
            stream=stream,
            allow_redirects=allow_redirects,
        )

    async def post(  # type: ignore[override]
        self,
        url: str,
        *,
        headers: dict | CIMultiDict | None = None,
        data: Any = None,
        form: dict | None = None,
        files: dict | None = None,
        query_string: dict | None = None,
        json: Any = None,
        scheme: str = "http",
        cookies: RequestsCookieJar | SimpleCookie | dict | None = None,
        stream: bool = False,
        allow_redirects: bool = True,
    ) -> Response:
        return await self.request(
            url=url,
            method="POST",
            headers=headers,
            data=data,
            form=form,
            files=files,
            query_string=query_string,
            json=json,
            scheme=scheme,
            cookies=cookies,
            stream=stream,
            allow_redirects=allow_redirects,
        )

    async def put(  # type: ignore[override]
        self,
        url: str,
        *,
        headers: dict | CIMultiDict | None = None,
        data: Any = None,
        form: dict | None = None,
        files: dict | None = None,
        query_string: dict | None = None,
        json: Any = None,
        scheme: str = "http",
        cookies: RequestsCookieJar | SimpleCookie | dict | None = None,
        stream: bool = False,
        allow_redirects: bool = True,
    ) -> Response:
        return await self.request(
            url=url,
            method="PUT",
            headers=headers,
            data=data,
            form=form,
            files=files,
            query_string=query_string,
            json=json,
            scheme=scheme,
            cookies=cookies,
            stream=stream,
            allow_redirects=allow_redirects,
        )

    async def patch(  # type: ignore[override]
        self,
        url: str,
        *,
        headers: dict | CIMultiDict | None = None,
        data: Any = None,
        form: dict | None = None,
        files: dict | None = None,
        query_string: dict | None = None,
        json: Any = None,
        scheme: str = "http",
        cookies: RequestsCookieJar | SimpleCookie | dict | None = None,
        stream: bool = False,
        allow_redirects: bool = True,
    ) -> Response:
        return await self.request(
            url=url,
            method="PATCH",
            headers=headers,
            data=data,
            form=form,
            files=files,
            query_string=query_string,
            json=json,
            scheme=scheme,
            cookies=cookies,
            stream=stream,
            allow_redirects=allow_redirects,
        )

    async def delete(  # type: ignore[override]
        self,
        url: str,
        *,
        headers: dict | CIMultiDict | None = None,
        data: Any = None,
        form: dict | None = None,
        files: dict | None = None,
        query_string: dict | None = None,
        json: Any = None,
        scheme: str = "http",
        cookies: RequestsCookieJar | SimpleCookie | dict | None = None,
        stream: bool = False,
        allow_redirects: bool = True,
    ) -> Response:
        return await self.request(
            url=url,
            method="DELETE",
            headers=headers,
            data=data,
            form=form,
            files=files,
            query_string=query_string,
            json=json,
            scheme=scheme,
            cookies=cookies,
            stream=stream,
            allow_redirects=allow_redirects,
        )

    async def trace(  # type: ignore[override]
        self,
        url: str,
        *,
        headers: dict | CIMultiDict | None = None,
        data: Any = None,
        form: dict | None = None,
        files: dict | None = None,
        query_string: dict | None = None,
        json: Any = None,
        scheme: str = "http",
        cookies: RequestsCookieJar | SimpleCookie | dict | None = None,
        stream: bool = False,
        allow_redirects: bool = True,
    ) -> Response:
        return await self.request(
            url=url,
            method="TRACE",
            headers=headers,
            data=data,
            form=form,
            files=files,
            query_string=query_string,
            json=json,
            scheme=scheme,
            cookies=cookies,
            stream=stream,
            allow_redirects=allow_redirects,
        )

    def websocket_connect(self, url: str, *args, **kwargs: Any) -> WebSocketSession:
        # use cookies too?
        incoming_headers = kwargs.get("headers", None)
        if incoming_headers is None and self.headers:
            kwargs["headers"] = {**self.headers}
        return self.client.websocket_connect(path=url, *args, **kwargs)
