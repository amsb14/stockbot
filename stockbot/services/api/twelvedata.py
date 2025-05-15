
import os
from twelvedata import TDClient
from stockbot.config import TWELVEDATA_API_KEY

td_client = TDClient(apikey=TWELVEDATA_API_KEY)

def td_kwargs(is_saudi: bool):
    """Return {'country':'Saudi Arabia'} when needed."""
    return {"country": "Saudi Arabia"} if is_saudi else {}
