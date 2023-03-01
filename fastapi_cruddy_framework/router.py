import os
import sys
import glob
import importlib.util
from os import path
from fastapi import APIRouter
from types import ModuleType
from .resource import Resource


# -------------------------------------------------------------------------------------------
# APPLICATION ROUTER / HELPERS
# -------------------------------------------------------------------------------------------
def getModuleDir(application_module) -> str:
    return path.dirname(os.path.abspath(application_module.__file__))


def getDirectoryModules(
    application_module: ModuleType = ..., sub_module_path="resources"
):
    app_root = getModuleDir(application_module)
    app_root_name = path.split(app_root)[1]
    normalized_sub_path = os.path.normpath(sub_module_path)
    submodule_tokens = normalized_sub_path.split(os.sep)
    modules = glob.glob(path.join(app_root, sub_module_path, "*.py"))
    full_module_base = [app_root_name] + submodule_tokens
    loaded_modules = []
    for m in modules:
        file_name = path.basename(m)
        module_name = os.path.splitext(file_name)[0]
        if "__init__" != module_name:
            m_module_tokens = full_module_base + [module_name]
            full_module_name = ".".join(m_module_tokens)
            spec = importlib.util.spec_from_file_location(full_module_name, m)
            abstract_module = importlib.util.module_from_spec(spec)
            loaded_modules.append((module_name, abstract_module))
            sys.modules[full_module_name] = abstract_module
            spec.loader.exec_module(abstract_module)
    return loaded_modules


def CreateRouterFromResources(
    application_module: ModuleType = ...,
    resource_path: str = "resources",
    common_resource_name: str = "resource",
) -> APIRouter:
    modules = getDirectoryModules(
        application_module=application_module, sub_module_path=resource_path
    )
    router = APIRouter()

    # We delay binding routes to the router until all resources are ready
    for m in modules:
        module = m[1]
        resource = getattr(module, common_resource_name)

        def setup(router: APIRouter = router, resource: Resource = resource):
            router.include_router(getattr(resource, "controller"))

        resource._on_resolution = setup

    return router
