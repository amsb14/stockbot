# All SQL queries used in the project


# ←– the one place you set your free-tier daily limit
FREE_DAILY_FEATURE_LIMIT = 15


SUBSCRIBER_SELECT = """
SELECT
  subscription_type,
  expires_at,
  last_usage_reset   AS last_reset,
  usage_count,
  usage_limit
FROM subscribers
WHERE chat_id = %s
"""

SUBSCRIBER_UPDATE_PROFILE = """
UPDATE subscribers
SET first_name = %s,
    username = %s,
    language_code = %s,
    is_active = TRUE
WHERE chat_id = %s
"""

SUBSCRIBER_UPDATE_FREE = f"""
UPDATE subscribers
SET first_name = %s,
    username = %s,
    language_code = %s,
    subscription_type = 'free',
    usage_limit = {FREE_DAILY_FEATURE_LIMIT},
    usage_count = CASE WHEN %s THEN 0 ELSE usage_count END,
    last_usage_reset = CASE WHEN %s THEN %s ELSE last_usage_reset END,
    is_active = TRUE
WHERE chat_id = %s
"""

SUBSCRIBER_INSERT = f"""
INSERT INTO subscribers (
    chat_id, first_name, username, language_code,
    subscription_type, usage_limit, usage_count,
    subscribed_at, last_usage_reset, is_active
) VALUES (
    %s, %s, %s, %s,
    'free', {FREE_DAILY_FEATURE_LIMIT}, 0,
    CURRENT_TIMESTAMP, %s, TRUE
)
"""

PREMIUM_KEY_SELECT = """
SELECT is_used, expires_at FROM premium_keys WHERE key_code=%s
"""

PREMIUM_KEY_UPDATE_USED = """
UPDATE premium_keys
SET is_used = TRUE,
    used_by_chat = %s,
    used_at = NOW()
WHERE key_code = %s
"""

SUBSCRIBER_UPSERT_PREMIUM = """
INSERT INTO subscribers(chat_id, subscription_type, expires_at)
VALUES (%s, 'premium', %s)
ON CONFLICT (chat_id) DO UPDATE
  SET subscription_type = 'premium',
      expires_at = %s
"""

SUBSCRIBER_CONSUME_FREE_CREDIT = """
UPDATE subscribers
SET usage_count = usage_count + 1
WHERE chat_id = %s
  AND subscription_type = 'free'
  AND usage_count < usage_limit
RETURNING usage_count;
"""

SUBSCRIBER_SELECT_USAGE = """
SELECT subscription_type FROM subscribers WHERE chat_id = %s
"""

SUBSCRIBER_RESET_DAILY_USAGE = """
UPDATE subscribers
SET usage_count = 0,
    last_usage_reset = %s
WHERE subscription_type = 'free'
"""
