## WebsocketConnectionManager

`fastapi-cruddy-framework` includes a relatively full-featured `WebsocketConnectionManager` that offers many of the same features as other great websocket libraries, such as [socket.io](https://socket.io/). The easiest way to see the full capabilities of the websocket manager is to look at the example server used to test this library! For instance, [here](examples/fastapi_cruddy_sqlite/services/websocket_1.py) and [here](examples/fastapi_cruddy_sqlite/services/websocket_2.py) you can see how to instantiate a `WebsocketConnectionManager`. You can then bind an instance of a `WebsocketConnectionManager` to your `ApplicationRoute`, as seen [here](examples/fastapi_cruddy_sqlite/router/application.py), using the async context manager's `.connect()` function to initiate a bidirectional websocket context that supports broadcasts, rooms, direct socket-to-socket messages, kill commands, a custom socket identity hook (to identify or kill many sockets owned by the same user), and a horizontally scaling control plane where you can even plugin your own custom commands! Note that you need to `.startup()` and `.dispose()` of a `WebsocketConnectionManager` in your application's `lifespan` hook, as seen [here](examples/fastapi_cruddy_sqlite/main.py).

The `WebsocketConnectionManager` will receive more thorough documentation in the future when it becomes more stable, but it is fully tested in it's current state and is very reliable!

Note that currently the `WebsocketConnectionManager` requires `redis` to function. In the future, other broker types may be added as well! The pub/sub aspect is delegated to a separate class under the hood.

<p align="right">(<a href="#readme-top">back to top</a>)</p>
