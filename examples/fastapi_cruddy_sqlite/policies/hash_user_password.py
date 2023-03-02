from bcrypt import hashpw, gensalt
from fastapi import Request, HTTPException

min_pw_length = 6
payload_key = "user"
field_key = "password"


async def hash_user_password(request: Request):
    # isloate the request body for modification
    request_body: dict = request._json

    # make sure the request body has the proper keys for the password...
    if request_body == None or type(request_body) != dict:
        raise HTTPException(
            status_code=400, detail="Request body must be in JSON format."
        )
    elif not payload_key in request_body or type(request_body[payload_key]) != dict:
        raise HTTPException(
            status_code=400,
            detail=f"Request body must contain a '{payload_key}' key which contains the object payload.",
        )
    elif (
        not field_key in request_body[payload_key]
        or type(request_body[payload_key][field_key]) != str
        or len(request_body[payload_key][field_key]) < min_pw_length
    ):
        raise HTTPException(
            status_code=400,
            detail=f"'{payload_key.upper()}' object payload must have a '{field_key}' value that is at least {min_pw_length} characters long.",
        )

    # encode the password in utf-8 so bcrypt won't complain
    encoded = f"{request_body[payload_key][field_key]}".encode("utf-8")
    # do the hashing, update the json key (this will propagate to the controller action)
    request_body[payload_key][
        field_key
    ] = f"{hashpw(password=encoded, salt=gensalt(12))}"
    # fin!
