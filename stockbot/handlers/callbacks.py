import logging
import textwrap
from datetime import date, datetime
from io import BytesIO
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import BadRequest
from telegram.ext import CallbackContext
from psycopg2.extras import RealDictCursor
from stockbot.database.connection import get_db_conn, put_db_conn
from stockbot.database.queries import SUBSCRIBER_CONSUME_FREE_CREDIT
from stockbot.services.api.twelvedata import td_client, td_kwargs
from stockbot.services.api.cache import (
    TD_QUOTE_CACHE,
    TD_TIME_SERIES_CACHE,
    TD_PROFILE_CACHE,
    td_quote_cached,
    td_ts_cached,
    _make_key,
)
from stockbot.services.subscription import check_usage_quota_for_query
from stockbot.services.rate_limiter import is_rate_limited
from stockbot.utils.formatting import format_huge_numbers, safe_format
from stockbot.handlers.base import with_subscription_check
from stockbot.services.ticker_service import parse_symbol
from stockbot.templates.keyboards import get_main_keyboard
import plotly.graph_objects as go
from stockbot.handlers.texts import (
    SUMMARY_TEMPLATE,
    PROFILE_TEMPLATE,
    FINANCIAL_TEMPLATE,
    INCOME_TEMPLATE,
    BALANCE_TEMPLATE,
    LEARN_TEMPLATE
)
from stockbot.utils.formatting import arabic_day_name, arabic_exchange_name
from stockbot.utils.helpers import get_arabic_name_from_db
from random import randint



# For tracking cache hits in the summary branch
CACHE_HIT_COUNTS = {}

@with_subscription_check
def button(update: Update, context: CallbackContext) -> None:
    query    = update.callback_query
    user_id  = query.from_user.id
    data     = query.data
    message  = ""  # initialized to avoid UnboundLocalError

    try:
        # =========== ❶ فرع اختيار السهم من قائمة الاقتراحات ===========
        if data.startswith("select_"):
            selected_sym = data[len("select_"):]
            db_symbol, api_symbol, is_saudi = parse_symbol(selected_sym)
            context.user_data.update({
                "db_symbol":  db_symbol,
                "api_symbol": api_symbol,
                "is_saudi":   is_saudi
            })
            return query.edit_message_text(
                text=f"تم اختيار السهم: {db_symbol} ✅\n"
                     "اختر الخدمة المطلوبة 👇",
                reply_markup=get_main_keyboard(),
                parse_mode="Markdown"
            )

        # =========== ❷ التأكد من وجود رمز المخزون في السياق ===========
        db_symbol  = context.user_data.get("db_symbol")
        api_symbol = context.user_data.get("api_symbol", db_symbol)
        is_saudi   = context.user_data.get("is_saudi", False)

        if not db_symbol:
            return query.edit_message_text("👋 أرسل اسم أو رمز الشركة أولاً.")

        # =========== ❸ ملف الشركة (profile) ===========
        if data == 'profile':
            chat_id = query.message.chat.id
            if not check_usage_quota_for_query(query, chat_id):
                return

            try:
                # محاولة جلب من الـ DB
                conn = get_db_conn()
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(
                        """
                        SELECT * FROM stock_data
                        WHERE symbol = %s
                        ORDER BY updated_date DESC
                        LIMIT 1
                        """,
                        (db_symbol,)
                    )
                    profile = cur.fetchone()
                put_db_conn(conn)

                if not profile:
                    raise ValueError("Profile not found in DB")

                # بيانات من الـ DB
                # name        = profile.get('name') or api_symbol
                name        = get_arabic_name_from_db(api_symbol) or profile.get('name', "غير متوفر")
                exchange    = profile.get('exchange') or "غير متوفر"
                sector      = profile.get('sector') or "غير متوفر"
                industry    = profile.get('industry') or "غير متوفر"
                employees   = profile.get('employees') or "غير متوفر"
                country     = profile.get('country') or "غير متوفر"
                website     = profile.get('website') or "غير متوفر"
                address     = profile.get('address1') or "غير متوفر"
                city        = profile.get('city') or "غير متوفر"
                zip_code    = profile.get('zip') or "غير متوفر"
                phone       = profile.get('phone') or "غير متوفر"
                fax         = profile.get('fax') or "غير متوفر"
                description = profile.get('longBusinessSummary') or 'No description available.'

                print(f"✅ [Data Source] PostgreSQL for {api_symbol}")

            except Exception as db_error:
                logging.warning(f"PostgreSQL profile fetch failed: {db_error}")
                print("/profile fetch costs 10 credits")
                prof = td_client.get_profile(symbol=api_symbol, **td_kwargs(is_saudi)).as_json()
                # name        = prof.get('name', api_symbol)
                name = get_arabic_name_from_db(api_symbol) or profile.get('name', "غير متوفر")
                exchange    = prof.get('exchange', "غير متوفر")
                sector      = prof.get('sector', "غير متوفر")
                industry    = prof.get('industry', "غير متوفر")
                employees   = prof.get('employees', "غير متوفر")
                country     = prof.get('country', "غير متوفر")
                website     = prof.get('website', "غير متوفر")
                address     = prof.get('address1', "غير متوفر")
                city        = prof.get('city', "غير متوفر")
                zip_code    = prof.get('zip', "غير متوفر")
                phone       = prof.get('phone', "غير متوفر")
                fax         = prof.get('fax', "غير متوفر")
                description = prof.get('description', 'No description available.')

            # خزن الوصف الطويل للـ read_more
            context.user_data['full_summary'] = description

            keyboard = [
                [InlineKeyboardButton("📖 قراءة الوصف الكامل", callback_data='read_more')],
                [InlineKeyboardButton("🔙 الرجوع للقائمة الرئيسية", callback_data='back_to_menu')]
            ]

            new_text = PROFILE_TEMPLATE.format(
                name=name,
                symbol=api_symbol,
                exchange=exchange,
                sector=sector,
                industry=industry,
                employees=employees,
                country=country,
                website=website if website != 'N/A' else 'غير متوفر',
                address=address,
                city=city,
                zip_code=zip_code,
                phone=phone,
                fax=fax,
                description=textwrap.shorten(description, width=300, placeholder="...")
            )

            return query.edit_message_text(
                text=new_text,
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

        # =========== ❹ قراءة المزيد ===========
        elif data == 'read_more':
            full_summary = context.user_data.get('full_summary', 'No summary available.')

            if len(full_summary) > 4000:
                chunks = [full_summary[i:i+4000] for i in range(0, len(full_summary), 4000)]
                for idx, chunk in enumerate(chunks, start=1):
                    context.bot.send_message(
                        chat_id=query.message.chat.id,
                        text=f"📖 *Full Summary (Part {idx}):*\n\n{chunk}",
                        parse_mode='Markdown'
                    )
                return

            message = f"📖 *وصف الشركة الكامل:*\n\n{full_summary}"
            reply_markup = InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 الرجوع للقائمة الرئيسية", callback_data='profile')
            ]])
            return query.edit_message_text(
                text=message,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )

        # =========== ❺ رجوع للقائمة الرئيسية ===========
        elif data == 'back_to_menu':
            return query.edit_message_text(
                text=f"رجعناك للقائمة الرئيسية لـ {api_symbol}. اختر خيار 👇",
                parse_mode='Markdown',
                reply_markup=get_main_keyboard()
            )

        # =========== ❻ الملخص (summary) ===========
        elif data == 'summary':
            chat_id = query.message.chat.id
            if not check_usage_quota_for_query(query, chat_id):
                return

            # Rate limiting
            if is_rate_limited(user_id):
                return query.answer(
                    "تهدي شوي! بمعدل عالي جداً 🙏",
                    show_alert=True,
                    cache_time=0
                )
            query.answer()

            td_args = {"symbol": api_symbol, **td_kwargs(is_saudi)}
            cache_key = _make_key(**td_args)
            cached_quote = TD_QUOTE_CACHE.get(cache_key)
            if cached_quote is not None:
                CACHE_HIT_COUNTS[api_symbol] = CACHE_HIT_COUNTS.get(api_symbol, 0) + 1

            try:
                quote = td_quote_cached(td_client, **td_args)  # ← pass td_client first
                print("/quote fetch costs 1 credit")
            except Exception as api_err:
                logging.warning(f"Summary API error: {api_err}")
                return query.edit_message_text(
                    text=(
                        f"⚠️ ما قدرت أجيب بيانات {api_symbol} الحية.\n"
                        "رمز خاطئ أو الخدمة مشغولة.\n"
                        "جرب بعد شوي."
                    ),
                    parse_mode='Markdown',
                    reply_markup=get_main_keyboard()
                )

            # استخلاص البيانات
            symbol         = quote.get('symbol', "غير متوفر")
            # name           = quote.get('name',   "غير متوفر")
            name = get_arabic_name_from_db(symbol) or quote.get('name', "غير متوفر")

            exchange       = quote.get('exchange', "غير متوفر")
            currency       = quote.get('currency', "غير متوفر")
            date_str       = quote.get('datetime', "غير متوفر")
            day_name = arabic_day_name(datetime.strptime(date_str, "%Y-%m-%d"))
            is_open        = quote.get('is_market_open', False)
            price          = float(quote.get('close', 0))
            change         = float(quote.get('change', 0))
            percent_change = float(quote.get('percent_change', 0))
            today_open     = float(quote.get('open', 0))
            day_high       = float(quote.get('high', 0))
            day_low        = float(quote.get('low', 0))
            volume         = float(quote.get('volume', 0))
            low_52         = float(quote.get('fifty_two_week', {}).get('low', 0))
            high_52        = float(quote.get('fifty_two_week', {}).get('high', 0))

            cache_note = f" _(from cache, hit #{CACHE_HIT_COUNTS[api_symbol]})_" if cached_quote else ""



            # … بعد معالجة البيانات …
            direction_emoji = '🟩' if change >= 0 else '🟥'
            direction_word = 'طالع' if change >= 0 else 'نازل'

            new_text = SUMMARY_TEMPLATE.format(
                name=name,
                symbol=symbol,
                day=day_name,  # اسم اليوم بالعربية
                date=date_str,  # التاريخ بصيغة 08-مايو-2025
                exchange= arabic_exchange_name(exchange),
                status="مفتوح 🟢" if is_open else "مغلق 🔴",
                price=safe_format(price),
                direction_emoji=('🟩' if change >= 0 else '🟥'),
                direction_word=('طالع' if change >= 0 else 'نازل'),
                pct_change=safe_format(percent_change),
                change=safe_format(change),
                open_price=safe_format(today_open),
                high=safe_format(day_high),
                low=safe_format(day_low),
                low52=safe_format(low_52),
                high52=safe_format(high_52),
                volume=format_huge_numbers(volume),
            )

            try:
                return query.edit_message_text(
                    text=new_text,
                    parse_mode='Markdown',
                    reply_markup=get_main_keyboard()
                )
            except BadRequest as e:
                if 'Message is not modified' in str(e):
                    return
                else:
                    raise

        # =========== ❼ البيانات التاريخية (historical_data) ===========
        elif data == 'historical_data':
            chat_id = query.message.chat.id
            if not check_usage_quota_for_query(query, chat_id):
                return

            keyboard = [
                [InlineKeyboardButton("يوم واحد",   callback_data='hist_1day')],
                [InlineKeyboardButton("خمسة أيام", callback_data='hist_5day')],
                [InlineKeyboardButton("30 يوم",     callback_data='hist_30day')],
                [InlineKeyboardButton("🔙 رجوع",     callback_data='back_to_menu')],
            ]
            message = f"*اختر فترة البيانات التاريخية لـ {api_symbol}:*"
            return query.edit_message_text(
                text=message,
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

        # =========== ❽ بناء المخطط التاريخي (hist_1day/5day/30day) ===========
        elif data in ('hist_1day', 'hist_5day', 'hist_30day'):
            chat_id = query.message.chat.id
            if not check_usage_quota_for_query(query, chat_id):
                return

            try:
                if data == 'hist_1day':
                    days, interval, outputsize = 1,   "15min", 50
                elif data == 'hist_5day':
                    days, interval, outputsize = 5,   "1h",    5*7
                else:
                    days, interval, outputsize = 30,  "1h",    30*7

                print("/time_series fetch costs 1 credit")
                df = td_client.time_series(
                    symbol=api_symbol,
                    interval=interval,
                    outputsize=outputsize,
                    **td_kwargs(is_saudi)
                ).as_pandas()
                df['datetime'] = df.index.strftime('%Y-%m-%d %H:%M')

                # بناء الرسم
                fig = go.Figure()
                fig.add_trace(go.Candlestick(
                    x=df['datetime'],
                    open=df['open'], high=df['high'], low=df['low'], close=df['close'],
                    name="OHLC"
                ))
                fig.add_trace(go.Scatter(
                    x=df['datetime'], y=df['close'],
                    mode='lines', line=dict(width=1.5), name="Close"
                ))
                fig.update_layout(
                    title=f"{api_symbol} History ({days}d)",
                    xaxis_rangeslider_visible=False,
                    template="plotly_white",
                    width=960, height=480
                )
                buf = BytesIO(fig.to_image(format="png"))
                buf.seek(0)

                # إحصائيات إضافية
                start_price = df['open'].iloc[-1]
                end_price   = df['close'].iloc[0]
                pct_change  = (end_price - start_price) / start_price * 100

                caption = (
                    f"*{api_symbol} — {days} day history*\n"
                    f"Change: {pct_change:+.2f}% "
                    f"({safe_format(start_price)} → {safe_format(end_price)})"
                )
                context.user_data['chart_buf']     = buf
                context.user_data['chart_caption'] = caption

                keyboard = [
                    [InlineKeyboardButton("📊 عرض المخطط", callback_data='send_chart')],
                    [InlineKeyboardButton("🔙 الفترات",    callback_data='historical_data')],
                ]
                return query.edit_message_text(
                    text=caption,
                    parse_mode='Markdown',
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )

            except Exception as e:
                logging.error(f"History error: {e}")
                return query.edit_message_text(
                    text="⚠️ خطأ في إنشاء الرسم البياني. حاول لاحقاً.",
                    parse_mode='Markdown',
                    reply_markup=get_main_keyboard()
                )

        # =========== ❾ إرسال المخطط (send_chart) ===========
        elif data == 'send_chart':
            try:
                buf     = context.user_data.get('chart_buf')
                caption = context.user_data.get('chart_caption', api_symbol)
                if buf:
                    buf.seek(0)
                    context.bot.send_photo(
                        chat_id=query.message.chat.id,
                        photo=buf,
                        caption=caption,
                        parse_mode='Markdown'
                    )
                else:
                    return query.edit_message_text(
                        text="⚠️ لا يوجد رسم بياني.",
                        parse_mode='Markdown'
                    )
            except Exception as e:
                logging.error(f"Send chart error: {e}")
                return query.edit_message_text(
                    text="⚠️ خطأ أثناء إرسال المخطط.",
                    parse_mode='Markdown'
                )
            return

        # =========== 🔟 توزيعات الأرباح (dividends) ===========
        elif data == 'dividends':
            chat_id = query.message.chat.id
            if not check_usage_quota_for_query(query, chat_id):
                return
            query.answer()
            try:
                conn = get_db_conn()
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(
                        """
                        SELECT fiscal_year, dividend_date, amount
                        FROM dividends
                        WHERE symbol = %s
                        ORDER BY fiscal_year DESC, dividend_date DESC
                        """,
                        (db_symbol,)
                    )
                    rows = cur.fetchall()
                put_db_conn(conn)

                if not rows:
                    return query.edit_message_text(
                        text=f"📉 لا توجد توزيعات تاريخية لـ {api_symbol}",
                        parse_mode='Markdown',
                        reply_markup=get_main_keyboard()
                    )

                from collections import defaultdict
                by_year = defaultdict(list)
                for r in rows:
                    year = r['fiscal_year']
                    date_str = r['dividend_date'].strftime('%Y-%m-%d')
                    amt = float(r['amount'])
                    by_year[year].append((date_str, amt))

                keyboard = [
                    [InlineKeyboardButton(f"📆 {yr}", callback_data=f"dividends_{yr}")]
                    for yr in sorted(by_year.keys(), reverse=True)
                ]
                keyboard.append([InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="back_to_menu")])

                return query.edit_message_text(
                    text=f"*توزيعات الأرباح لـ {api_symbol}*\n\nاختر السنة:",
                    parse_mode='Markdown',
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )

            except Exception as e:
                logging.error(f"Dividends error: {e}")
                return query.edit_message_text(
                    text=f"⚠️ خطأ في جلب توزيعات {api_symbol}.",
                    parse_mode='Markdown',
                    reply_markup=get_main_keyboard()
                )

        elif data.startswith("dividends_"):
            try:
                year = int(data.split("_")[1])
                conn = get_db_conn()
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(
                        """
                        SELECT dividend_date, amount
                        FROM dividends
                        WHERE symbol = %s AND fiscal_year = %s
                        ORDER BY dividend_date DESC
                        """,
                        (db_symbol, year)
                    )
                    year_data = cur.fetchall()

                    cur.execute(
                        """
                        SELECT DISTINCT fiscal_year
                        FROM dividends
                        WHERE symbol = %s
                        ORDER BY fiscal_year DESC
                        """,
                        (db_symbol,)
                    )
                    all_years = [r['fiscal_year'] for r in cur.fetchall()]
                put_db_conn(conn)

                if not year_data:
                    message = f"📉 لا توجد توزيعات لعام {year} لـ {api_symbol}."
                else:
                    LBL_DIV = "توزيعات الأرباح"
                    message = f"*{get_arabic_name_from_db(api_symbol) or api_symbol}* _({api_symbol})_ - *" + LBL_DIV + "*\n\n"
                    # message = f"*📆 توزيعات الأرباح {year} لسهم شركة {get_arabic_name_from_db(api_symbol) or api_symbol}*"
                    total = 0
                    for r in year_data:
                        date_str = r['dividend_date'].strftime('%Y-%m-%d')
                        amt = float(r['amount'])
                        total += amt
                        message += f"\n▫️ {amt:.2f} في {date_str}"
                    message += f"\n\n🔢 *الإجمالي:* {total:.2f}\u200C"

                keyboard = [
                    [InlineKeyboardButton(f"📆 {yr}", callback_data=f"dividends_{yr}")]
                    for yr in all_years
                ]
                keyboard.append([InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="back_to_menu")])

                return query.edit_message_text(
                    text=message,
                    parse_mode='Markdown',
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )

            except Exception as e:
                logging.error(f"Dividend fetch error: {e}")
                return query.edit_message_text(
                    text=f"⚠️ حصل خطأ أثناء جلب توزيعات {api_symbol}.",
                    parse_mode='Markdown',
                    reply_markup=get_main_keyboard()
                )


        # =========== ⓫ البيانات المالية (financial_data) ===========
        elif data == 'financial_data':
            keyboard = [
                [
                    InlineKeyboardButton("قائمة الدخل", callback_data='income_statement'),
                    InlineKeyboardButton("الميزانية",   callback_data='balance_sheet'),
                ],
                [
                    InlineKeyboardButton("🔙 رجوع", callback_data='back_to_menu')
                ]
            ]
            return query.edit_message_text(
                text="اختر نوع البيانات المالية:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

        # =========== ⓬ قائمة الدخل (income_statement) ===========
        elif data == 'income_statement':
            chat_id = query.message.chat.id
            if not check_usage_quota_for_query(query, chat_id):
                return
            query.answer()

            # 1) Load up to 5 recent years from DB only
            conn = get_db_conn()
            try:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("""
                        SELECT DISTINCT EXTRACT(YEAR FROM "Fiscal_Date") AS yr
                          FROM income_statements
                         WHERE "Ticker" = %s
                           AND "Statement_Type" = 'Annual'
                         ORDER BY yr DESC
                         LIMIT 5
                    """, (db_symbol,))
                    years = [int(r['yr']) for r in cur.fetchall()]
            finally:
                put_db_conn(conn)

            # 2) If DB has no years, fetch ONLY the year list via API (no statement data yet)
            if not years:
                logging.info(f"No DB years for {api_symbol}; pulling year list from API")
                inc_json = td_client.get_income_statement(
                    symbol=api_symbol, period='annual', **td_kwargs(is_saudi)
                ).as_json().get("income_statement", [])
                years = sorted({
                    int(item.get("fiscal_date", "")[:4])  # Use underscore
                    for item in inc_json if item.get("fiscal_date")
                }, reverse=True)[:5]

            # 3) Build year‑selection menu
            keyboard = [
                           [InlineKeyboardButton(f"📅 {yr}", callback_data=f"income_year_{yr}")]
                           for yr in years
                       ] + [[
                InlineKeyboardButton("🍃 قائمة الدخل", callback_data='income_statement'),
                InlineKeyboardButton("🧮 المركز المالي", callback_data='balance_sheet'),
            ], [
                InlineKeyboardButton("🔙 رجوع", callback_data='back_to_menu')
            ]]

            return query.edit_message_text(
                text=f"*قائمة الدخل لـ {api_symbol}*\n\nاختر السنة:",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )


        # ───────── ⓭ عرض بيانات السنة المختارة (income_year_YYYY) ───────────
        elif data.startswith("income_year_"):
            year = int(data.split("_")[2])
            query.answer()

            # 1) Re‑fetch years list (DB first, fallback to API for list only)
            conn = get_db_conn()
            try:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("""
                        SELECT DISTINCT EXTRACT(YEAR FROM "Fiscal_Date") AS yr
                          FROM income_statements
                         WHERE "Ticker" = %s
                           AND "Statement_Type" = 'Annual'
                         ORDER BY yr DESC
                         LIMIT 5
                    """, (db_symbol,))
                    years = [int(r['yr']) for r in cur.fetchall()]
            finally:
                put_db_conn(conn)

            if not years:
                logging.info(f"No DB years for {api_symbol}; pulling list from API")
                inc_json = td_client.get_income_statement(
                    symbol=api_symbol, period='annual', **td_kwargs(is_saudi)
                ).as_json().get("income_statement", [])
                years = sorted({
                    int(item.get("fiscal_date", "")[:4])
                    for item in inc_json if item.get("fiscal_date")
                }, reverse=True)[:5]

            # 2) Fetch income data for the selected year (DB first)
            conn = get_db_conn()
            try:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("""
                        SELECT *
                          FROM income_statements
                         WHERE "Ticker" = %s
                           AND EXTRACT(YEAR FROM "Fiscal_Date") = %s
                           AND "Statement_Type" = 'Annual'
                         LIMIT 1
                    """, (db_symbol, year))
                    inc = cur.fetchone()

                    cur.execute("""
                        SELECT "TotalRevenue"
                          FROM income_statements
                         WHERE "Ticker" = %s
                           AND EXTRACT(YEAR FROM "Fiscal_Date") = %s
                           AND "Statement_Type" = 'Annual'
                         LIMIT 1
                    """, (db_symbol, year - 1))
                    prev_row = cur.fetchone()
            finally:
                put_db_conn(conn)

            # 3) If DB row missing, fetch FULL statement from API now (this is the only credit‑consuming point)
            if not inc:
                logging.info(f"No DB income row for {api_symbol} {year}; fetching via API")
                inc_json = td_client.get_income_statement(
                    symbol=api_symbol, period='annual', **td_kwargs(is_saudi)
                ).as_json().get("income_statement", [])
                latest = next((r for r in inc_json if r.get("fiscal_date", "").startswith(str(year))), {})
                prev_api = next((r for r in inc_json if r.get("fiscal_date", "").startswith(str(year - 1))), {})

                inc = {
                    "TotalRevenue": latest.get("revenue"),
                    "GrossProfit": latest.get("gross_profit"),
                    "OperatingIncome": latest.get("operating_income"),
                    "NetIncome": latest.get("net_income"),
                    "EBITDA": latest.get("ebitda"),
                    "BasicEPS": latest.get("eps_basic")
                }
                prev_row = {"TotalRevenue": prev_api.get("revenue")} if prev_api else None

            # 4) Parse & format figures
            def to_float(x):
                try:
                    return float(x)
                except (TypeError, ValueError):
                    return 0.0

            rev = to_float(inc.get("TotalRevenue"))
            grossp = to_float(inc.get("GrossProfit"))
            op_i = to_float(inc.get("OperatingIncome"))
            net = to_float(inc.get("NetIncome"))
            ebitda = to_float(inc.get("EBITDA"))
            eps = to_float(inc.get("BasicEPS"))
            prev_rev = to_float(prev_row["TotalRevenue"]) if prev_row and prev_row.get(
                "TotalRevenue") is not None else None

            name = get_arabic_name_from_db(api_symbol) or api_symbol

            rev_fmt = format_huge_numbers(rev)
            grossp_fmt = format_huge_numbers(grossp)
            op_i_fmt = format_huge_numbers(op_i)
            net_fmt = format_huge_numbers(net)
            ebitda_fmt = format_huge_numbers(ebitda)
            eps_fmt = safe_format(eps)

            gross_margin = safe_format((grossp / rev) * 100) if rev else "0.00"
            op_margin = safe_format((op_i / rev) * 100) if rev else "0.00"
            net_margin = safe_format((net / rev) * 100) if rev else "0.00"
            ebitda_margin = safe_format((ebitda / rev) * 100) if rev else "0.00"

            if prev_rev and prev_rev > 0:
                growth = (rev - prev_rev) / prev_rev * 100
                rev_growth = safe_format(growth) + "% " + ("🟢" if growth >= 0 else "🟥")
            else:
                rev_growth = "غير متوفر"

            new_text = INCOME_TEMPLATE.format(
                name=name,
                year=year,
                symbol=api_symbol,
                revenue=rev_fmt,
                gross_profit=grossp_fmt,
                gross_margin=gross_margin,
                op_income=op_i_fmt,
                op_margin=op_margin,
                net_income=net_fmt,
                net_margin=net_margin,
                ebitda=ebitda_fmt,
                ebitda_margin=ebitda_margin,
                eps=eps_fmt,
                rev_growth=rev_growth
            )

            # 5) Rebuild year menu
            keyboard = [
                           [InlineKeyboardButton(f"📅 {yr}", callback_data=f"income_year_{yr}")]
                           for yr in years
                       ] + [[
                InlineKeyboardButton("🍃 قائمة الدخل", callback_data='income_statement'),
                InlineKeyboardButton("🧮 المركز المالي", callback_data='balance_sheet'),
            ], [
                InlineKeyboardButton("🔙 رجوع", callback_data='back_to_menu')
            ]]

            try:
                return query.edit_message_text(
                    text=new_text,
                    parse_mode='Markdown',
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            except BadRequest as e:
                if 'Message is not modified' in str(e):
                    return
                raise




        # ─────────── ⓮ قائمة المركز المالي (balance_sheet) ────────────
        elif data == 'balance_sheet':
            chat_id = query.message.chat.id
            if not check_usage_quota_for_query(query, chat_id):
                return
            query.answer()

            # 1) Try DB for up to 5 recent years
            conn = get_db_conn()
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT DISTINCT EXTRACT(YEAR FROM "Fiscal_Date") AS yr
                      FROM balance_sheets
                     WHERE "Ticker" = %s
                       AND "Statement_Type" = 'Annual'
                     ORDER BY yr DESC
                     LIMIT 5
                """, (db_symbol,))
                years = [int(r['yr']) for r in cur.fetchall()]
            put_db_conn(conn)

            # 2) Fallback to API if no DB data
            if not years:
                bal_json = td_client.get_balance_sheet(
                    symbol=api_symbol, period='annual', **td_kwargs(is_saudi)
                ).as_json().get("balance_sheet", [])
                years = sorted({
                    int(item.get("fiscal_date", "")[:4])
                    for item in bal_json if item.get("fiscal_date")
                }, reverse=True)[:5]

            # 3) Build keyboard
            keyboard = [
                           [InlineKeyboardButton(f"📅 {yr}", callback_data=f"balance_year_{yr}")]
                           for yr in years
                       ] + [[
                InlineKeyboardButton("🍃 قائمة الدخل", callback_data='income_statement'),
                InlineKeyboardButton("🧮 المركز المالي", callback_data='balance_sheet'),
            ], [
                InlineKeyboardButton("🔙 رجوع", callback_data='back_to_menu')
            ]]

            return query.edit_message_text(
                text=f"*الميزانية العمومية لـ {api_symbol}*\n\nاختر السنة:",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )


        # ───────── ⓯ عرض بيانات السنة المختارة (balance_year_YYYY) ───────────
        elif data.startswith("balance_year_"):
            year = int(data.split("_")[2])
            query.answer()

            years = []
            try:
                conn = get_db_conn()
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("""
                        SELECT DISTINCT EXTRACT(YEAR FROM "Fiscal_Date") AS yr
                        FROM balance_sheets
                        WHERE "Ticker" = %s AND "Statement_Type" = 'Annual'
                        ORDER BY yr DESC LIMIT 5
                    """, (db_symbol,))
                    years = [int(r['yr']) for r in cur.fetchall()]

                    # current year
                    cur.execute("""
                        SELECT *
                        FROM balance_sheets
                        WHERE "Ticker" = %s AND EXTRACT(YEAR FROM "Fiscal_Date") = %s
                        AND "Statement_Type" = 'Annual'
                        LIMIT 1
                    """, (db_symbol, year))
                    bal = cur.fetchone()

                    # optional: prior year for comparisons if needed
                    cur.execute("""
                        SELECT "TotalAssets"
                        FROM balance_sheets
                        WHERE "Ticker" = %s AND EXTRACT(YEAR FROM "Fiscal_Date") = %s
                        AND "Statement_Type" = 'Annual'
                        LIMIT 1
                    """, (db_symbol, year - 1))
                    prev_row = cur.fetchone()
                put_db_conn(conn)

                if not bal:
                    raise ValueError("No DB row")

                total_assets = float(bal.get("TotalAssets") or 0)
                total_liab = float(bal.get("TotalLiabilitiesNetMinorityInterest") or 0)
                current_assets = float(bal.get("TotalCurrentAssets") or 0)
                current_liab = float(bal.get("TotalCurrentLiabilities") or 0)
                cash = float(bal.get("CashAndCashEquivalents") or 0)
                equity = total_assets - total_liab
                name = get_arabic_name_from_db(api_symbol) or api_symbol

            except Exception as e:
                logging.warning(f"DB balance fetch failed ({api_symbol} {year}): {e}")

                bal_json = td_client.get_balance_sheet(
                    symbol=api_symbol, period='annual', **td_kwargs(is_saudi)
                ).as_json().get("balance_sheet", [])

                # find exact year
                latest = next((r for r in bal_json if r.get("fiscal_date", "").startswith(str(year))), {})
                prev = next((r for r in bal_json if r.get("fiscal_date", "").startswith(str(year - 1))), None)

                total_assets = float(latest.get("assets", {}).get("total_assets") or 0)
                total_liab = float(latest.get("liabilities", {}).get("total_liabilities") or 0)
                current_assets = float(
                    latest.get("assets", {}).get("current_assets", {}).get("total_current_assets") or 0)
                current_liab = float(
                    latest.get("liabilities", {}).get("current_liabilities", {}).get("total_current_liabilities") or 0)
                cash = float(latest.get("assets", {}).get("current_assets", {}).get("cash_and_cash_equivalents") or 0)
                equity = total_assets - total_liab
                name = get_arabic_name_from_db(api_symbol) or api_symbol

                # rebuild year list from API
                years = sorted({
                    int(item.get("fiscal_date", "")[:4])
                    for item in bal_json if item.get("fiscal_date")
                }, reverse=True)[:5]

            # formatting
            assets_fmt = format_huge_numbers(total_assets)
            liab_fmt = format_huge_numbers(total_liab)
            equity_fmt = format_huge_numbers(equity)
            cur_assets_fmt = format_huge_numbers(current_assets)
            cur_liab_fmt = format_huge_numbers(current_liab)
            wc_fmt = format_huge_numbers(current_assets - current_liab)
            de_ratio = (total_liab / equity) if equity else None
            de_ratio_fmt = safe_format(de_ratio)

            new_text = BALANCE_TEMPLATE.format(
                name=name,
                year=year,
                symbol=api_symbol,
                total_assets=assets_fmt,
                total_liabilities=liab_fmt,
                equity=equity_fmt,
                current_assets=cur_assets_fmt,
                current_liabilities=cur_liab_fmt,
                working_capital=wc_fmt,
                de_ratio=de_ratio_fmt
            )

            keyboard = [
                           [InlineKeyboardButton(f"📅 {yr}", callback_data=f"balance_year_{yr}")]
                           for yr in years
                       ] + [[
                InlineKeyboardButton("🍃 قائمة الدخل", callback_data='income_statement'),
                InlineKeyboardButton("🧮 المركز المالي", callback_data='balance_sheet'),
            ], [
                InlineKeyboardButton("🔙 رجوع", callback_data='back_to_menu')
            ]]

            try:
                return query.edit_message_text(
                    text=new_text,
                    parse_mode='Markdown',
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            except BadRequest as e:
                if 'Message is not modified' in str(e):
                    return
                raise


        # =========== ⓮ الفحص الشرعي (shariah_check) ===========
        elif query.data == 'shariah_check':
            try:
                try:
                    # === Fetch required data from PostgreSQL via pool =============
                    conn = get_db_conn()  # 🆕 lease connection
                    try:
                        with conn.cursor(cursor_factory=RealDictCursor) as cur:
                            # Latest annual income statement
                            cur.execute(
                                """
                                SELECT *
                                FROM income_statements
                                WHERE "Ticker" = %s
                                  AND "Statement_Type" = 'Annual'
                                ORDER BY "Fiscal_Date" DESC
                                LIMIT 1;
                                """,
                                (db_symbol,),
                            )
                            latest_income = cur.fetchone() or {}

                            # Latest annual balance sheet
                            cur.execute(
                                """
                                SELECT *
                                FROM balance_sheets
                                WHERE "Ticker" = %s
                                  AND "Statement_Type" = 'Annual'
                                ORDER BY "Fiscal_Date" DESC
                                LIMIT 1;
                                """,
                                (db_symbol,),
                            )
                            latest_balance = cur.fetchone() or {}

                            # Latest market‑cap snapshot
                            cur.execute(
                                """
                                SELECT *
                                FROM stock_data
                                WHERE symbol = %s
                                ORDER BY updated_date DESC
                                LIMIT 1;
                                """,
                                (db_symbol,),
                            )
                            stock_data = cur.fetchone() or {}
                    finally:
                        put_db_conn(conn)  # 🆕 release to pool

                    print(f"✅ [Data Source] PostgreSQL database used for {api_symbol}")

                    # ---- Use DB values directly ---------------------------------
                    total_revenue = float(latest_income.get("TotalRevenue") or 0)
                    interest_income = float(latest_income.get("InterestIncome") or 0)
                    total_debt = float(latest_balance.get("TotalDebt") or 0)
                    market_cap = float(stock_data.get("marketCap") or 0)

                except Exception as db_error:
                    logging.warning(f"PostgreSQL fetch failed. Falling back to API. Error: {str(db_error)}")
                    print("/income_statement fetch costs 100 credits per symbol")
                    print("/balance_sheet fetch costs 100 credits per symbol")
                    print("/statistics fetch costs 50 credits per symbol")

                    # === Fallback to TwelveData API ===
                    income = td_client.get_income_statement(symbol=api_symbol, period='annual',
                                                            **td_kwargs(is_saudi)).as_json()
                    balance = td_client.get_balance_sheet(symbol=api_symbol, period='annual',
                                                          **td_kwargs(is_saudi)).as_json()
                    stats = td_client.get_statistics(symbol=api_symbol, **td_kwargs(is_saudi)).as_json()

                    latest_income = income.get("income_statement", [{}])[0]
                    latest_balance = balance.get("balance_sheet", [{}])[0]

                    revenue = stats['statistics']['financials']['income_statement']
                    total_revenue = float(revenue.get("revenue_ttm") or 0)
                    interest_income = float(latest_income.get('non_operating_interest', {}).get('income') or 0)
                    short_term_debt = float(latest_balance.get("liabilities", {}).get("current_liabilities", {}).get(
                        "short_term_debt") or 0)
                    long_term_debt = float(latest_balance.get("liabilities", {}).get("non_current_liabilities", {}).get(
                        "long_term_debt") or 0)
                    total_debt = short_term_debt + long_term_debt
                    market_cap = float(
                        stats.get("statistics", {}).get("valuations_metrics", {}).get("market_capitalization") or 0)

                    print(f"🔁 [Data Source] TwelveData API used for {api_symbol}")

                # === Calculate Shariah Ratios + Decision Logic ===
                if total_revenue == 0 or market_cap == 0:
                    interest_ratio = 0
                    debt_ratio = 0
                    compliance_result = "⚠️ لا توجد بيانات مالية كافية للحكم على توافق السهم."
                else:
                    interest_ratio = (interest_income / total_revenue) * 100
                    debt_ratio = (total_debt / market_cap) * 100
                    is_compliant = interest_ratio < 5 and debt_ratio < 33
                    compliance_result = (
                        "✅ التوافق محتمل حسب البيانات"
                        if is_compliant else
                        "❌ التوافق منخفض حسب البيانات"
                    )

                # === Format Message ===
                message = f"""
        📊 *فحص التوافق الشرعي للسهم {api_symbol}*

        💰 *النسب المالية:*
        • دخل الفوائد / إجمالي الإيرادات: {interest_ratio:.2f}% {'✅' if interest_ratio < 5 else '❌'}
        • إجمالي الدين / القيمة السوقية: {debt_ratio:.2f}% {'✅' if debt_ratio < 33 else '❌'}

        📝 *تفاصيل:*
        • إجمالي الإيرادات: {format_huge_numbers(total_revenue)}
        • دخل الفوائد: {format_huge_numbers(interest_income)}
        • إجمالي الدين: {format_huge_numbers(total_debt)}
        • القيمة السوقية: {format_huge_numbers(market_cap)}

        🎯 *الحالة النهائية:* {compliance_result}

        📝 *ملاحظات:*
        1️⃣ التحليل مبني على أحدث بيانات مالية سنوية متوفرة.  
        2️⃣ 🔔 هذه المعلومات لأغراض تعليمية واسترشادية فقط، ولا تُعد توصية شرعية أو فتوى.  
        3️⃣ ⚠️ تقع مسؤولية التحقق من شرعية السهم على المستخدم، والبوت غير مسؤول عن أي قرار استثماري يُتخذ بناءً على هذه البيانات.
        """

                # ✨ external-link button to Yaaqen + back button
                buttons = []

                if not is_saudi:  # 🚫 Yaqqen = US stocks only
                    yaaqen_url = f"https://yaaqen.com/stocks/{api_symbol}"
                    buttons.append([InlineKeyboardButton("🌐 عرض بيانات الشركة على موقع يقين", url=yaaqen_url)])

                buttons.append([InlineKeyboardButton("🔙 الرجوع للقائمة", callback_data='back_to_menu')])
                keyboard = InlineKeyboardMarkup(buttons)

                # 🆗 in-place edit with the new keyboard
                try:
                    query.edit_message_text(
                        text=message,
                        parse_mode='Markdown',
                        reply_markup=keyboard
                    )
                except BadRequest as e:
                    if 'Message is not modified' in str(e):
                        pass
                    else:
                        raise

            except Exception as e:
                logging.error(f"Shariah check error: {e}")
                query.answer()
                query.edit_message_text(
                    text=f"⚠️ تعذر إجراء فحص التوافق الشرعي للسهم {api_symbol}. يرجى المحاولة لاحقًا.",
                    parse_mode='Markdown',
                    reply_markup=get_main_keyboard()
                )
            return



        # =========== ⓯ الإحصائيات العامة (stats) ===========
        elif data == 'stats':
            chat_id = query.message.chat.id
            if not check_usage_quota_for_query(query, chat_id):
                return

            # ── Formatting helper ───────────────────────────────────────────────
            def format_value(val, kind=None):
                """
                kind:
                  - "huge"    → uses format_huge_numbers()
                  - "percent" → multiplies by 100 and appends '%'
                  - None      → safe_format()
                """
                try:
                    num = float(val)
                except (TypeError, ValueError):
                    return "غير متوفر"

                if kind == "huge":
                    return format_huge_numbers(num)
                if kind == "percent":
                    return safe_format(num * 100) + "%"
                return safe_format(num)

            # ── Load raw stats (DB first, then API fallback) ───────────────────────
            try:
                conn = get_db_conn()
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(
                        "SELECT * FROM stock_data WHERE symbol=%s ORDER BY updated_date DESC LIMIT 1",
                        (db_symbol,)
                    )
                    sd = cur.fetchone()
                put_db_conn(conn)

                if not sd:
                    raise ValueError("No stats in DB")

                name = get_arabic_name_from_db(api_symbol) or api_symbol
                raw = sd

            except Exception as db_err:
                logging.warning(f"Stats DB failed: {db_err}")
                prof = td_client.get_profile(symbol=api_symbol, **td_kwargs(is_saudi)).as_json()
                stat = td_client.get_statistics(symbol=api_symbol, **td_kwargs(is_saudi)).as_json()
                divs = td_client.get_dividends(symbol=api_symbol, **td_kwargs(is_saudi)).as_json()

                name = get_arabic_name_from_db(api_symbol) or api_symbol
                # flatten API response into same keys as DB
                raw = {
                    "marketCap": stat['statistics']['valuations_metrics'].get('market_capitalization', 0),
                    "trailingPE": stat['statistics']['valuations_metrics'].get('trailing_pe'),
                    "priceToBook": stat['statistics']['valuations_metrics'].get('price_to_book_mrq'),
                    "totalRevenue": stat['statistics']['financials']['income_statement'].get('revenue_ttm', 0),
                    "returnOnEquity": stat['statistics'].get('return_on_equity_ttm'),
                    "returnOnAssets": stat['statistics'].get('return_on_assets_ttm'),
                    "totalCash": stat['statistics']['financials']['balance_sheet'].get('total_cash_mrq', 0),
                    "totalDebt": stat['statistics']['financials']['balance_sheet'].get('total_debt_mrq', 0),
                    "currentRatio": stat['statistics']['financials']['balance_sheet'].get('current_ratio_mrq'),
                    "sharesOutstanding": stat['statistics']['stock_statistics'].get('shares_outstanding', 0),
                    # dividends pick first entry
                    **({} if not divs.get('dividends') else {
                        "dividendYield": divs['dividends'][0].get('trailing_annual_dividend_yield'),
                        "dividendContinuity": divs['dividends'][0].get('frequency'),
                        "exDividendDate": divs['dividends'][0].get('ex_date'),
                        "lastDividendValue": divs['dividends'][0].get('amount')
                    })
                }
                print(f"🔁 [API] stats for {api_symbol}")

            # ── Now format every field ──────────────────────────────────────────
            mcap = format_value(raw.get('marketCap'), "huge")
            so = format_value(raw.get('sharesOutstanding'), "huge")
            rev = format_value(raw.get('totalRevenue'), "huge")
            cash = format_value(raw.get('totalCash'), "huge")
            debt = format_value(raw.get('totalDebt'), "huge")

            tpe = format_value(raw.get('trailingPE'))
            p2b = format_value(raw.get('priceToBook'))
            cr = format_value(raw.get('currentRatio'))
            roe = format_value(raw.get('returnOnEquity'), "percent")
            roa = format_value(raw.get('returnOnAssets'), "percent")

            dy = format_value(raw.get('dividendYield'), "percent")
            freq = raw.get('dividendContinuity') or "غير متوفر"
            val = format_value(raw.get('lastDividendValue'))
            # ex-date: handle int timestamp or string
            ex_raw = raw.get('exDividendDate')
            try:
                ex = datetime.utcfromtimestamp(int(ex_raw)).strftime("%Y-%m-%d")
            except:
                ex = str(ex_raw) if ex_raw else "غير متوفر"

            # ─── Build the final text ─────────────────────────────────────
            new_text = FINANCIAL_TEMPLATE.format(
                name=name, symbol=api_symbol,
                mcap=mcap, so=so, rev=rev,
                cash=cash, debt=debt, cr=cr,
                tpe=tpe, p2b=p2b, roe=roe,
                roa=roa, dy=dy, freq=freq,
                val=val, ex=ex
            )

            try:
                return query.edit_message_text(
                    text=new_text,
                    parse_mode='Markdown',
                    reply_markup=get_main_keyboard()
                )
            except BadRequest as e:
                if "Message is not modified" in str(e):
                    return
                raise


        # =========== ⓰ مساعدة (learn_help) ===========
        elif data == 'learn_help':
            query.answer()

            try:
                return query.edit_message_text(
                    text=LEARN_TEMPLATE,
                    parse_mode='Markdown',
                    reply_markup=get_main_keyboard()
                )
            except BadRequest as e:
                if 'Message is not modified' in str(e):
                    return
                else:
                    raise

        # =========== ⓳ تحديث عام إن لزم ===========
        if message and query.message.text != message:
            return query.edit_message_text(
                text=message,
                parse_mode='Markdown',
                reply_markup=get_main_keyboard()
            )

    except Exception as e:
        logging.error(f"Callback handler error: {e}", exc_info=True)
        return query.edit_message_text(
            text=(
                f"⚠️ حدث خطأ أثناء معالجة طلبك للسهم "
                f"{context.user_data.get('api_symbol', '')}. حاول لاحقاً."
            ),
            parse_mode='Markdown',
            reply_markup=get_main_keyboard()
        )
