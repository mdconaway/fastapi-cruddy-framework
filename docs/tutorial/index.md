# Tutorial - User Guide

This tutorial aims to touch on all the major features **Cruddy** brings to the table, step by step. If at any point you would rather just reference the final application, you can find it [here](https://github.com/mdconaway/fastapi-cruddy-framework/tree/master/examples/fastapi_cruddy_sqlite)

## Project Setup and Installation

We're using [Poetry](https://python-poetry.org/docs/) as our Python dependency manager but feel free to use another if Poetry is not your jam.

### Installation

<div class="termy">

```console

$ poetry new fastapi_cruddy_demo

Created package fastapi_cruddy_demo in fastapi_cruddy_demo

$ cd fastapi_cruddy_demo

$ poetry add fastapi-cruddy-framework
Using version ^1.4.8 for fastapi-cruddy-framework

Updating dependencies
Resolving dependencies... (2.4s)

Package operations: 67 installs, 0 updates, 0 removals

  - Installing idna (3.7)
  - Installing mdurl (0.1.2)
  - Installing sniffio (1.3.1)
  - Installing anyio (4.3.0)
  - Installing markdown-it-py (3.0.0)
  - Installing pygments (2.18.0)
  - Installing attrs (23.2.0)
  - Installing certifi (2024.2.2)
  - Installing click (8.1.7)
  - Installing h11 (0.14.0)
  - Installing httptools (0.6.1)
  - Installing python-dotenv (1.0.1)
  - Installing pyyaml (6.0.1)
  - Installing rich (13.7.1)
  - Installing rpds-py (0.18.1)
  - Installing shellingham (1.5.4)
  - Installing typing-extensions (4.11.0)
  - Installing uvloop (0.19.0)
  - Installing watchfiles (0.21.0)
  - Installing websockets (12.0)
  - Installing annotated-types (0.6.0)
  - Installing dnspython (2.6.1)
  - Installing httpcore (1.0.5)
  - Installing markupsafe (2.1.5)
  - Installing pydantic-core (2.18.2)
  - Installing referencing (0.35.1)
  - Installing typer (0.12.3)
  - Installing uvicorn (0.29.0)
  - Installing charset-normalizer (3.3.2)
  - Installing email-validator (2.1.1)
  - Installing fastapi-cli (0.0.3)
  - Installing httpx (0.27.0)
  - Installing jinja2 (3.1.4)
  - Installing jsonschema-specifications (2023.12.1)
  - Installing orjson (3.10.3)
  - Installing pydantic (2.7.1)
  - Installing python-multipart (0.0.9)
  - Installing six (1.16.0)
  - Installing starlette (0.37.2)
  - Installing ujson (5.10.0)
  - Installing urllib3 (2.2.1)
  - Installing fastapi (0.111.0)
  - Installing graphql-core (3.2.3)
  - Installing greenlet (3.0.3)
  - Installing itsdangerous (2.2.0)
  - Installing jsonschema (4.22.0)
  - Installing more-itertools (10.2.0)
  - Installing multidict (6.0.5)
  - Installing pydantic-extra-types (2.7.0)
  - Installing pydantic-settings (2.2.1)
  - Installing python-dateutil (2.9.0.post0)
  - Installing redis (5.0.4)
  - Installing requests (2.31.0)
  - Installing sortedcontainers (2.4.0)
  - Installing sqlalchemy (2.0.30)
  - Installing typeguard (4.2.1)
  - Installing async-asgi-testclient (1.4.11)
  - Installing async-timeout (4.0.3)
  - Installing fakeredis (2.23.1)
  - Installing inflect (7.2.1)
  - Installing pymitter (0.5.1)
  - Installing sqlalchemy-utils (0.41.2)
  - Installing sqlmodel (0.0.16)
  - Installing strawberry-graphql (0.229.0)
  - Installing uuid7 (0.1.0)
  - Installing validator-collection (1.5.0)
  - Installing fastapi-cruddy-framework (1.4.8)

Writing lock file
```

</div>

### Hello World

The simplest Cruddy service is really just a FastAPI application:

```Python title="fastapi_cruddy_demo/main.py"
--8<-- "docs_src/tutorial/hello_world.py"
```

Copy that to a file `fastapi_cruddy_demo/main.py`

---

## Running the app

We're going to leverage the [FastAPI CLI](https://fastapi.tiangolo.com/fastapi-cli/) for running the application.

<div class="termy">

```console

$ poetry run fastapi dev fastapi_cruddy_demo/main.py

<font color="#3465A4">INFO     </font> Using path <font color="#3465A4">fastapi_cruddy_demo/main.py</font>
<font color="#3465A4">INFO     </font> Resolved absolute path <font color="#75507B">/Users/home/dev/fastapi_cruddy_demo/fastapi_cruddy_demo/main.py</font>
<font color="#3465A4">INFO     </font> Searching for package file structure from directories with <font color="#3465A4">__init__.py</font> files
<font color="#3465A4">INFO     </font> Importing from <font color="#3465A4">/Users/home/dev/fastapi_cruddy_demo</font>

 ╭─ Python package file structure ─╮
 │                                 │
 │  📁 fastapi_cruddy_demo         │
 │  ├── 🐍 __init__.py             │
 │  └── 🐍 main.py                 │
 │                                 │
 ╰─────────────────────────────────╯

<font color="#3465A4">INFO     </font>     Importing module fastapi_cruddy_demo.main
<font color="#3465A4">INFO     </font>     Found importable FastAPI app

 ╭────────── <font color="#8AE234"><b>Importable FastAPI app</b></font> ──────────╮
 │                                            │
 │  from fastapi_cruddy_demo.main import app  │
 │                                            │
 ╰────────────────────────────────────────────╯

<font color="#3465A4">INFO     </font>     Using import string fastapi_cruddy_demo.main:app

 ╭────────── FastAPI CLI - Development mode ───────────╮
 │                                                     │
 │  Serving at: http://127.0.0.1:8008                  │
 │                                                     │
 │  API docs: http://127.0.0.1:8008/docs               │
 │                                                     │
 │  Running in development mode, for production use:   │
 │                                                     │
 │  fastapi run                                        │
 │                                                     │
 ╰─────────────────────────────────────────────────────╯

<font color="#3465A4">INFO     </font>:     Will watch for changes in these directories: ['/Users/home/dev/fastapi_cruddy_demo']
<font color="#3465A4">INFO     </font>:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
<font color="#3465A4">INFO     </font>:     Started reloader process [45812] using WatchFiles
<font color="#3465A4">INFO     </font>:     Started server process [45818]
<font color="#3465A4">INFO     </font>:     Waiting for application startup.
<font color="#3465A4">INFO     </font>:     Application startup complete.

```
</div>

In the output, there's a line with something like:

```hl_lines="4"
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

That line shows the URL where your app is being served, in your local machine.

### Check it

Open your browser at [http://127.0.0.1:8000](http://127.0.0.1:8000){: .external-link target='_blank'}.

You will see the JSON response as:

```JSON
{"message": "Hello World"}
```

### Interactive API docs

As this is just a FastAPI service under the hood, you get all the magic that entails!

* Swagger Docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs){: .external-link target='_blank'}
* Alt API Docs: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc){: .external-link target='_blank'}

## Summary

At the heart of every *Cruddy* app lives FastAPI so transitioning from an existing FastAPI service can be done incrementally. As the tutorial progresses you will explore the different ways the framework can improve your DX and make your life just a little more... Cruddy.
