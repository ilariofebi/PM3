from pydantic import BaseModel
from typing import Union
from collections import namedtuple

# id or Name schema
ION = namedtuple('Id_or_Name', 'type, data, proc')

# Messaggio di ritorno simulato di psutil.wait
alive_gone = namedtuple('AliveGone', 'pid')

class RetMsg(BaseModel):
    msg: str
    err: bool = False
    warn: bool = False
    payload: Union[list, dict, None]

class KillMsg(BaseModel):
    msg: str = ''
    err: bool = False
    warn: bool = False
    gone: list = []
    alive: list = []
