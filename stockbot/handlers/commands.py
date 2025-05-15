# stockbot/handlers/commands.py
import logging
from datetime import date
from telegram import Update
from telegram.ext import CallbackContext
from stockbot.database.connection import get_db_conn, put_db_conn
from stockbot.database.queries import (
    SUBSCRIBER_SELECT,
    SUBSCRIBER_UPDATE_PROFILE,
    SUBSCRIBER_UPDATE_FREE,
    SUBSCRIBER_INSERT,
    FREE_DAILY_FEATURE_LIMIT
)
from stockbot.handlers.base import with_subscription_check
from stockbot.handlers.texts import (
    LEARN_TEMPLATE
)
from stockbot.templates.keyboards import get_main_keyboard
from stockbot.services.cashflow_etl import refresh_cashflow_test
from stockbot.services.income_etl  import refresh_income_test
from stockbot.services.balance_etl import refresh_balance_test
from stockbot.services.stockinfo_etl import refresh_stockinfo_test
from stockbot.services.dividends_etl import refresh_dividends_test
from stockbot.services.daily_closes_etl import refresh_daily_closes

@with_subscription_check
def start(update: Update, context: CallbackContext) -> None:
    user = update.effective_user
    chat_id = update.effective_chat.id
    today = date.today()

    conn = get_db_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(SUBSCRIBER_SELECT, (chat_id,))
            row = cur.fetchone()

            if row:
                # sub_type, expires_at, last_reset = row
                sub_type, expires_at, last_reset, usage_count, usage_limit = row

                if sub_type == 'premium' and expires_at and expires_at >= today:
                    cur.execute(
                        SUBSCRIBER_UPDATE_PROFILE,
                        (user.first_name, user.username, user.language_code, chat_id)
                    )
                    conn.commit()
                    update.message.reply_text(
                        f"👋 أهلاً فيك مرة ثانية! اشتراكك في الباقة المدفوعة صالح حتى {expires_at}."
                    )
                    return

                reset_usage = (last_reset is None) or (last_reset < today)

                cur.execute(
                    SUBSCRIBER_UPDATE_FREE,
                    (
                        user.first_name,
                        user.username,
                        user.language_code,
                        reset_usage,
                        reset_usage,
                        today,
                        chat_id,
                    )
                )
                conn.commit()

            else:
                usage_count, usage_limit = 0, FREE_DAILY_FEATURE_LIMIT
                cur.execute(
                    SUBSCRIBER_INSERT,
                    (
                        chat_id,
                        user.first_name,
                        user.username,
                        user.language_code,
                        today,
                    )
                )
                conn.commit()

    finally:
        put_db_conn(conn)

    update.message.reply_text(
        "👋 أهلاً بك في البوت!\n\n"
        "انت مسجل/تم تسجيلك في الباقة المجانية.\n\n"
        f"📊 تقدر تستخدم {usage_limit} (طلب/طلبات) من مميزات الباقة المجانية يومياً،\n"
        f"وقمت حتى الآن باستخدام {usage_count} طلبات حتى الآن اليوم."
    )

@with_subscription_check
def status(update: Update, context: CallbackContext) -> None:
    chat_id = update.effective_chat.id

    conn = get_db_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT subscription_type, usage_count, usage_limit, expires_at, is_active
                FROM subscribers
                WHERE chat_id = %s
                """,
                (chat_id,)
            )
            result = cur.fetchone()

            if not result:

                update.message.reply_text("❌ لم يتم تسجيلك بعد.\nيرجى إرسال الأمر /start للبدء في استخدام البوت.")
                return

            subscription_type, usage_count, usage_limit, expires_at, is_active = result

            if not is_active:
                update.message.reply_text("⚠️ اشتراكك غير مفعل حالياً.\nأرسل الأمر /start لإعادة تفعيل الوصول.")
                return

            if subscription_type == 'premium':
                exp_text = (
                    f"🗓️ تاريخ انتهاء الاشتراك: {expires_at.strftime('%Y-%m-%d')}"
                    if expires_at else "∞ بدون تاريخ انتهاء"
                )
                msg = (
                    "⭐ أنت مشترك في **الباقة المدفوعة**\n"
                    f"{exp_text}\n"
                    "✅ لديك صلاحية كاملة للوصول إلى جميع المميزات."
                )
            else:
                msg = (
                    "👤 أنت مسجل في **الباقة المجانية**\n"
                    f"📊 حد الاستخدام اليومي: {usage_count}/{usage_limit}\n"
                    "⚠️ اشترك في الباقة المدفوعة للاستفادة الكاملة بدون قيود."
                )

            update.message.reply_text(msg, parse_mode='Markdown')

    finally:
        put_db_conn(conn)

def grant_premium(update: Update, context: CallbackContext):
    if not context.args:
        update.message.reply_text("Usage: /grant_premium <chat_id>")
        return

    try:
        chat_id = int(context.args[0])
    except ValueError:
        update.message.reply_text("Invalid chat_id.")
        return

    conn = get_db_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE subscribers
                SET subscription_type = 'premium',
                    usage_limit = NULL,
                    usage_count = 0,
                    expires_at = CURRENT_DATE + INTERVAL '30 days'
                WHERE chat_id = %s
            """, (chat_id,))
            conn.commit()
    finally:
        put_db_conn(conn)

    update.message.reply_text(f"✅ تم ترقية المستخدم {chat_id} إلى الباقة المدفوعة لمدة 30 يومًا.")

def help_command(update, context):
    update.message.reply_text(
        text=LEARN_TEMPLATE,
        parse_mode='Markdown',
        reply_markup=get_main_keyboard()
    )



def refresh_cf_db(update: Update, context: CallbackContext) -> None:
    update.message.reply_text("🔄 جاري تحديث بيانات التدفقات النقدية... الرجاء الانتظار.")
    try:
        count = refresh_cashflow_test()
        if count:
            update.message.reply_text(f"✅ تم إدراج/تحديث {count} صف في الجدول بنجاح.")
        else:
            update.message.reply_text("⚠️ لم تُرجع أي بيانات للتدفقات النقدية.")
    except Exception as e:
        logging.exception("refresh_cf_db failed")
        update.message.reply_text(f"❌ حدث خطأ أثناء التحديث: {e}")

def refresh_is_db(update: Update, context: CallbackContext) -> None:
    update.message.reply_text("🔄 جاري تحديث القوائم المالية... الرجاء الانتظار.")
    try:
        count = refresh_income_test()
        if count:
            update.message.reply_text(f"✅ تم إدراج/تحديث {count} صف في جدول القوائم المالية بنجاح.")
        else:
            update.message.reply_text("⚠️ لم تُرجع أي بيانات للقوائم المالية.")
    except Exception as e:
        logging.exception("refresh_is_db failed")
        update.message.reply_text(f"❌ حدث خطأ أثناء التحديث: {e}")


def refresh_bs_db(update: Update, context: CallbackContext) -> None:
    """
    /refresh_bs_db — fetch & upsert balance_sheets on demand.
    """
    update.message.reply_text("🔄 جاري تحديث القوائم المالية (الميزانيات)... الرجاء الانتظار.")
    try:
        count = refresh_balance_test()
        if count:
            update.message.reply_text(f"✅ تم إدراج/تحديث {count} صف في جدول الميزانيات بنجاح.")
        else:
            update.message.reply_text("⚠️ لم تُرجع أي بيانات للميزانيات.")
    except Exception as e:
        logging.exception("refresh_bs_db failed")
        update.message.reply_text(f"❌ حدث خطأ أثناء التحديث: {e}")

def refresh_stockinfo_db(update: Update, context: CallbackContext) -> None:
    """
    /refresh_stock_info — fetch & upsert stock_info on demand.
    """
    update.message.reply_text("🔄 جاري تحديث بيانات الأسهم... الرجاء الانتظار.")
    try:
        count = refresh_stockinfo_test()
        if count:
            update.message.reply_text(
                f"✅ تم إدراج/تحديث {count} سجلاً في جدول بيانات الأسهم بنجاح."
            )
        else:
            update.message.reply_text("⚠️ لم تُرجع أي بيانات للتحديث.")
    except Exception as e:
        logging.exception("refresh_stockinfo_db failed")
        update.message.reply_text(f"❌ حدث خطأ أثناء التحديث: {e}")


def refresh_dividends_db(update: Update, context: CallbackContext) -> None:
    """
    /refresh_dividends — fetch & upsert dividends on demand.
    """
    update.message.reply_text("🔄 جاري تحديث توزيعات الأرباح... الرجاء الانتظار.")
    try:
        count = refresh_dividends_test()
        if count:
            update.message.reply_text(
                f"✅ تم إدراج/تحديث {count} صفًا في جدول التوزيعات بنجاح."
            )
        else:
            update.message.reply_text("⚠️ لم تُرجع أي توزيعات للتحديث.")
    except Exception as e:
        logging.exception("refresh_dividends_db failed")
        update.message.reply_text(f"❌ حدث خطأ أثناء التحديث: {e}")

def refresh_daily_closes_db(update: Update, context: CallbackContext) -> None:
    """
    /refresh_daily_closes — fetch & upsert daily closes on demand.
    """
    update.message.reply_text("🔄 جاري تحديث أسعار الإغلاق اليومية... الرجاء الانتظار.")
    try:
        count = refresh_daily_closes()
        if count:
            update.message.reply_text(
                f"✅ تم إدراج/تحديث {count} صفًا في جدول الإغلاق اليومي بنجاح."
            )
        else:
            update.message.reply_text("⚠️ لم يُرجع أي بيانات للإغلاق اليومي للتحديث.")
    except Exception as e:
        logging.exception("refresh_daily_closes_db failed")
        update.message.reply_text(f"❌ حدث خطأ أثناء التحديث: {e}")