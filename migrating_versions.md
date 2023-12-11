<a name="readme-top"></a>

<!-- PROJECT LOGO -->
<div align="center">
  <h2 align="center">FastAPI - Cruddy Framework: Migrating Versions</h2>
  <a href="https://github.com/mdconaway/fastapi-cruddy-framework">
    <img src="https://raw.githubusercontent.com/mdconaway/fastapi-cruddy-framework/master/logo.png" alt="Logo">
  </a>
  <br/>
</div>

<!-- Migration Guide -->

## Migration Guide

### `fastapi-cruddy-framework` 0.x.x -&gt; 1.x.x

#### Dependency Guides:
- [sqlalchemy 1-&gt;2](https://docs.sqlalchemy.org/en/20/changelog/migration_20.html)
- [pydantic 1-&gt;2](https://docs.pydantic.dev/latest/migration/)

#### Code Mods Required:

1. Modify `BaseSettings` imports:
- Any project files using pydantic's `BaseSettings` ENV config model must shift their import target to `pydantic_settings`
```python
from pydantic import BaseSettings
```
becomes
```python
from pydantic_settings import BaseSettings
```

<p align="right">(<a href="#readme-top">back to top</a>)</p>
