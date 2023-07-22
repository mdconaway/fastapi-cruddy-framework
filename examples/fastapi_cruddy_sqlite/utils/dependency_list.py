from fastapi import Depends


def dependency_list(*args):
    return [Depends(x) for x in args]
