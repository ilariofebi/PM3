from pydantic import BaseModel, validator
from typing import Union

class RetMsg(BaseModel):
    msg: str
    err: bool = False
    warn: bool = False
    payload: Union[list, dict, None]
