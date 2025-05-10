from cachetools import TTLCache, cached

TD_TIME_SERIES_CACHE = TTLCache(maxsize=1_000, ttl=300)
TD_QUOTE_CACHE = TTLCache(maxsize=2_000, ttl=300)
TD_PROFILE_CACHE = TTLCache(maxsize=2_000, ttl=600)

def _make_key(*args, **kwargs):
    parts = [f"{k}={kwargs[k]}" for k in sorted(kwargs)]
    return "|".join(parts)

@cached(TD_QUOTE_CACHE, key=_make_key)
def td_quote_cached(td_client, **kwargs):
    return td_client.quote(**kwargs).as_json()

@cached(TD_TIME_SERIES_CACHE, key=_make_key)
def td_ts_cached(td_client, **kwargs):
    return td_client.time_series(**kwargs).as_json()
