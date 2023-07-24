from httpx import Response
from typing import Any, Dict, Iterable, Mapping, Optional, Sequence, Union
from httpx._types import (
    AuthTypes,
    CookieTypes,
    HeaderTypes,
    RequestContent,
    RequestFiles,
    URLTypes,
    QueryParamTypes,
)
from httpx._client import UseClientDefault, USE_CLIENT_DEFAULT
from httpx._types import TimeoutTypes
from httpx._models import Cookies
from fastapi.testclient import TestClient

_RequestData = Mapping[str, Union[str, Iterable[str]]]


class BrowserTestClient:
    def __init__(
        self,
        client: TestClient,
        cookies: Union[Cookies, None] = None,
        headers: Union[HeaderTypes, None] = None,
        ws_headers: Union[Dict, None] = None,
    ):
        self.client = client
        self.cookies = cookies
        self.headers = headers
        self.ws_headers = ws_headers
        self.client.cookies = Cookies()

    def _process_cookies(self, result: Response) -> Response:
        self.cookies = result.cookies
        self.client.cookies = Cookies()
        return result

    def request(  # type: ignore[override]
        self,
        method: str,
        url: URLTypes,
        *,
        content: Optional[RequestContent] = None,
        data: Optional[_RequestData] = None,
        files: Optional[RequestFiles] = None,
        json: Any = None,
        params: Optional[QueryParamTypes] = None,
        headers: Optional[HeaderTypes] = None,
        cookies: Optional[CookieTypes] = None,
        auth: Union[AuthTypes, UseClientDefault] = USE_CLIENT_DEFAULT,
        follow_redirects: Optional[bool] = None,
        allow_redirects: Optional[bool] = None,
        timeout: Union[TimeoutTypes, UseClientDefault] = USE_CLIENT_DEFAULT,
        extensions: Optional[Dict[str, Any]] = None,
    ) -> Response:
        use_cookies = self.cookies if self.cookies else cookies
        use_headers = self.headers if self.headers else headers
        result = self.client.request(
            method,
            url,
            content=content,
            data=data,
            files=files,
            json=json,
            params=params,
            headers=use_headers,
            cookies=use_cookies,
            auth=auth,
            allow_redirects=allow_redirects,
            follow_redirects=follow_redirects,
            timeout=timeout,
            extensions=extensions,
        )
        return self._process_cookies(result)

    def get(  # type: ignore[override]
        self,
        url: URLTypes,
        *,
        params: Optional[QueryParamTypes] = None,
        headers: Optional[HeaderTypes] = None,
        cookies: Optional[CookieTypes] = None,
        auth: Union[AuthTypes, UseClientDefault] = USE_CLIENT_DEFAULT,
        follow_redirects: Optional[bool] = None,
        allow_redirects: Optional[bool] = None,
        timeout: Union[TimeoutTypes, UseClientDefault] = USE_CLIENT_DEFAULT,
        extensions: Optional[Dict[str, Any]] = None,
    ) -> Response:
        use_cookies = self.cookies if self.cookies else cookies
        use_headers = self.headers if self.headers else headers
        result = self.client.get(
            url,
            params=params,
            headers=use_headers,
            cookies=use_cookies,
            auth=auth,
            follow_redirects=follow_redirects,
            allow_redirects=allow_redirects,
            timeout=timeout,
            extensions=extensions,
        )
        return self._process_cookies(result)

    def options(  # type: ignore[override]
        self,
        url: URLTypes,
        *,
        params: Optional[QueryParamTypes] = None,
        headers: Optional[HeaderTypes] = None,
        cookies: Optional[CookieTypes] = None,
        auth: Union[AuthTypes, UseClientDefault] = USE_CLIENT_DEFAULT,
        follow_redirects: Optional[bool] = None,
        allow_redirects: Optional[bool] = None,
        timeout: Union[TimeoutTypes, UseClientDefault] = USE_CLIENT_DEFAULT,
        extensions: Optional[Dict[str, Any]] = None,
    ) -> Response:
        use_cookies = self.cookies if self.cookies else cookies
        use_headers = self.headers if self.headers else headers
        result = self.client.options(
            url,
            params=params,
            headers=use_headers,
            cookies=use_cookies,
            auth=auth,
            follow_redirects=follow_redirects,
            allow_redirects=allow_redirects,
            timeout=timeout,
            extensions=extensions,
        )
        return self._process_cookies(result)

    def head(  # type: ignore[override]
        self,
        url: URLTypes,
        *,
        params: Optional[QueryParamTypes] = None,
        headers: Optional[HeaderTypes] = None,
        cookies: Optional[CookieTypes] = None,
        auth: Union[AuthTypes, UseClientDefault] = USE_CLIENT_DEFAULT,
        follow_redirects: Optional[bool] = None,
        allow_redirects: Optional[bool] = None,
        timeout: Union[TimeoutTypes, UseClientDefault] = USE_CLIENT_DEFAULT,
        extensions: Optional[Dict[str, Any]] = None,
    ) -> Response:
        use_cookies = self.cookies if self.cookies else cookies
        use_headers = self.headers if self.headers else headers
        result = self.client.head(
            url,
            params=params,
            headers=use_headers,
            cookies=use_cookies,
            auth=auth,
            follow_redirects=follow_redirects,
            allow_redirects=allow_redirects,
            timeout=timeout,
            extensions=extensions,
        )
        return self._process_cookies(result)

    def post(  # type: ignore[override]
        self,
        url: URLTypes,
        *,
        content: Optional[RequestContent] = None,
        data: Optional[_RequestData] = None,
        files: Optional[RequestFiles] = None,
        json: Any = None,
        params: Optional[QueryParamTypes] = None,
        headers: Optional[HeaderTypes] = None,
        cookies: Optional[CookieTypes] = None,
        auth: Union[AuthTypes, UseClientDefault] = USE_CLIENT_DEFAULT,
        follow_redirects: Optional[bool] = None,
        allow_redirects: Optional[bool] = None,
        timeout: Union[TimeoutTypes, UseClientDefault] = USE_CLIENT_DEFAULT,
        extensions: Optional[Dict[str, Any]] = None,
    ) -> Response:
        use_cookies = self.cookies if self.cookies else cookies
        use_headers = self.headers if self.headers else headers
        result = self.client.post(
            url,
            content=content,
            data=data,  # type: ignore[arg-type]
            files=files,
            json=json,
            params=params,
            headers=use_headers,
            cookies=use_cookies,
            auth=auth,
            follow_redirects=follow_redirects,
            allow_redirects=allow_redirects,
            timeout=timeout,
            extensions=extensions,
        )
        return self._process_cookies(result)

    def put(  # type: ignore[override]
        self,
        url: URLTypes,
        *,
        content: Optional[RequestContent] = None,
        data: Optional[_RequestData] = None,
        files: Optional[RequestFiles] = None,
        json: Any = None,
        params: Optional[QueryParamTypes] = None,
        headers: Optional[HeaderTypes] = None,
        cookies: Optional[CookieTypes] = None,
        auth: Union[AuthTypes, UseClientDefault] = USE_CLIENT_DEFAULT,
        follow_redirects: Optional[bool] = None,
        allow_redirects: Optional[bool] = None,
        timeout: Union[TimeoutTypes, UseClientDefault] = USE_CLIENT_DEFAULT,
        extensions: Optional[Dict[str, Any]] = None,
    ) -> Response:
        use_cookies = self.cookies if self.cookies else cookies
        use_headers = self.headers if self.headers else headers
        result = self.client.put(
            url,
            content=content,
            data=data,  # type: ignore[arg-type]
            files=files,
            json=json,
            params=params,
            headers=use_headers,
            cookies=use_cookies,
            auth=auth,
            follow_redirects=follow_redirects,
            allow_redirects=allow_redirects,
            timeout=timeout,
            extensions=extensions,
        )
        return self._process_cookies(result)

    def patch(  # type: ignore[override]
        self,
        url: URLTypes,
        *,
        content: Optional[RequestContent] = None,
        data: Optional[_RequestData] = None,
        files: Optional[RequestFiles] = None,
        json: Any = None,
        params: Optional[QueryParamTypes] = None,
        headers: Optional[HeaderTypes] = None,
        cookies: Optional[CookieTypes] = None,
        auth: Union[AuthTypes, UseClientDefault] = USE_CLIENT_DEFAULT,
        follow_redirects: Optional[bool] = None,
        allow_redirects: Optional[bool] = None,
        timeout: Union[TimeoutTypes, UseClientDefault] = USE_CLIENT_DEFAULT,
        extensions: Optional[Dict[str, Any]] = None,
    ) -> Response:
        use_cookies = self.cookies if self.cookies else cookies
        use_headers = self.headers if self.headers else headers
        result = self.client.patch(
            url,
            content=content,
            data=data,  # type: ignore[arg-type]
            files=files,
            json=json,
            params=params,
            headers=use_headers,
            cookies=use_cookies,
            auth=auth,
            follow_redirects=follow_redirects,
            allow_redirects=allow_redirects,
            timeout=timeout,
            extensions=extensions,
        )
        return self._process_cookies(result)

    def delete(  # type: ignore[override]
        self,
        url: URLTypes,
        *,
        params: Optional[QueryParamTypes] = None,
        headers: Optional[HeaderTypes] = None,
        cookies: Optional[CookieTypes] = None,
        auth: Union[AuthTypes, UseClientDefault] = USE_CLIENT_DEFAULT,
        follow_redirects: Optional[bool] = None,
        allow_redirects: Optional[bool] = None,
        timeout: Union[TimeoutTypes, UseClientDefault] = USE_CLIENT_DEFAULT,
        extensions: Optional[Dict[str, Any]] = None,
    ) -> Response:
        use_cookies = self.cookies if self.cookies else cookies
        use_headers = self.headers if self.headers else headers
        result = self.client.delete(
            url,
            params=params,
            headers=use_headers,
            cookies=use_cookies,
            auth=auth,
            follow_redirects=follow_redirects,
            allow_redirects=allow_redirects,
            timeout=timeout,
            extensions=extensions,
        )
        return self._process_cookies(result)

    def websocket_connect(
        self, url: str, subprotocols: Union[Sequence[str], None] = None, **kwargs: Any
    ) -> Any:
        # use cookies as headers?
        if self.ws_headers:
            kwargs["headers"] = {**self.ws_headers}
        return self.client.websocket_connect(
            url=url, subprotocols=subprotocols, **kwargs  # type: ignore
        )
