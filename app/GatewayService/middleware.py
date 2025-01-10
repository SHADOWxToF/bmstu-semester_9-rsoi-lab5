from fastapi import *
from fastapi.responses import *
from sqlmodel import *
import os
import requests

import jwt
from jwt.algorithms import RSAAlgorithm


identityProviderURL = f'{os.environ["IDENTITY_PROVIDER"]}:8080'
JWK_URL = f"http://{identityProviderURL}/realms/ticketbuy/protocol/openid-connect/certs"




# Загрузка JWKs
def get_jwks():
    response = requests.get(JWK_URL)
    response.raise_for_status()
    return response.json()["keys"]


def alg(kid):
    jwks = get_jwks()
    for key in jwks:
        if key["kid"] == kid:
            return RSAAlgorithm.from_jwk(key)

# Валидация JWT
def validate_jwt(token: str):
    unverified_header = jwt.get_unverified_header(token)
    rsa_key = alg(unverified_header["kid"])
    
    # Декодировать токен
    try:
        payload = jwt.decode(token, rsa_key, algorithms=["RS256"], audience="account", options={"verify_exp": True})
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")
