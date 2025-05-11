# # text.py
# SUMMARY_TEMPLATE = (
#     "🗂️ *بطاقة السهم:* {name} ({symbol}){cache}\n\n"
#     "📅 *التاريخ:* {date}\n"
#     "🏦 *السوق:* {exchange}\n"
#     "💱 *العملة:* {currency}\n"
#     "⏰ *حالة السوق:* {status}\n\n"
#     "💵 *السعر الآن:* {price} ({dir_word} {pct_change}% {dir_emoji})\n"
#     "↕️ *التغير:* {change}\n"
#     "🔔 *الافتتاح:* {open_price}\n"
#     "⬆️ *أعلى اليوم:* {high}\n"
#     "⬇️ *أدنى اليوم:* {low}\n\n"
#     "📉 *نطاق 52 أسبوع:* {low52} – {high52}\n"
#     "🔄 *حجم التداول:* {volume}"
# )


# ── Arabic Labels (used in summary) ─────────────────────────────
LBL_SUMMARY       = "نبذة سريعة"
LBL_DATE_MARKET   = "سوق"
LBL_CURRENT_PRICE = "السعر الحالي"
LBL_CHANGE        = "التغير"
LBL_OPEN          = "افتتاح الجلسة"
LBL_HIGH_LOW      = "أعلى / أدنى اليوم"
LBL_RANGE_52W     = "نطاق 52 أسبوع"
LBL_VOLUME        = "حجم التداول"

SUMMARY_TEMPLATE = (
    "*{name}* _({symbol})_ - "
    "*" + LBL_SUMMARY + "*\n\n"
    "_{day} {date}_ – " + LBL_DATE_MARKET + " *{exchange}* ({status})\n\n"
    "💵 *" + LBL_CURRENT_PRICE + ":* {price} {direction_emoji} {direction_word} {pct_change}% ({change})\n"
    "🔔 *" + LBL_OPEN + ":* {open_price}\n"
    "⬆️⬇️ *" + LBL_HIGH_LOW + ":* {high} - {low}\n"
    "📉 *" + LBL_RANGE_52W + ":* {low52} – {high52}\n"
    "🔄 *" + LBL_VOLUME + ":* {volume}\u200C"
)

# ── Arabic Labels (for company profile) ─────────────────────
LBL_PROFILE       = "معلومات الشركة"
LBL_MAIN_EXCHANGE = "السوق الرئيسي"
LBL_SECTOR        = "القطاع"
LBL_INDUSTRY      = "الصناعة"
LBL_EMPLOYEES     = "الموظفين"
LBL_COUNTRY       = "الدولة"
LBL_WEBSITE       = "الموقع الإلكتروني"
LBL_ADDRESS       = "معلومات العنوان"
LBL_ADDRESS_LINE  = "العنوان"
LBL_CITY_ZIP      = "المدينة"
LBL_PHONE         = "الهاتف"
LBL_FAX           = "الفاكس"
LBL_DESCRIPTION   = "وصف الشركة"

# ── Profile Template ────────────────────────────────────────
PROFILE_TEMPLATE = (
    "*{name}* _({symbol})_ - *" + LBL_PROFILE + "*\n\n"
    "*" + LBL_MAIN_EXCHANGE + ":* {exchange}\n"
    "*" + LBL_SECTOR + ":* {sector}\n"
    "*" + LBL_INDUSTRY + ":* {industry}\n"
    "*" + LBL_EMPLOYEES + ":* {employees}\n"
    "*" + LBL_COUNTRY + ":* {country}\n"
    "*" + LBL_WEBSITE + ":* {website}\n"
    "*" + LBL_ADDRESS + ":*\n"
    "*" + LBL_ADDRESS_LINE + ":* {address}\n"
    "*" + LBL_CITY_ZIP + ":* {city}، الرمز البريدي: {zip_code}\n"
    "*" + LBL_PHONE + ":* {phone}\n"
    "*" + LBL_FAX + ":* {fax}\n\n"
    "📝 *" + LBL_DESCRIPTION + ":*\n"
    "{description}"
)

# ── Arabic Labels for Financial Stats ─────────────────────
LBL_STATS      = "بيانات مالية"
LBL_MCAP       = "القيمة السوقية"
LBL_SO         = "عدد الأسهم المصدرة"
LBL_REV        = "الإيرادات السنوية"
LBL_CASH       = "النقد المتاح"
LBL_DEBT       = "إجمالي الديون"
LBL_CR         = "نسبة السيولة الجارية"
LBL_PE         = "مكرر الأرباح (P/E)"
LBL_PB         = "مكرر القيمة الدفترية (P/B)"
LBL_ROE        = "العائد على حقوق المساهمين (ROE)"
LBL_ROA        = "العائد على الأصول (ROA)"
LBL_DY         = "العائد التوزيعي"
LBL_FREQ       = "الاستمرارية"
LBL_LAST_DIV   = "آخر توزيع"
LBL_EX_DIV     = "تاريخ الاستحقاق"

# ── Financial Stats Template ──────────────────────────────
FINANCIAL_TEMPLATE = (
    "*{name}* _({symbol})_ - *" + LBL_STATS + "*\n\n"
    "🔹 *" + LBL_MCAP + ":* {mcap}\n"
    "🔹 *" + LBL_SO + ":* {so}\n"
    "🔹 *" + LBL_REV + ":* {rev}\n"
    "🔹 *" + LBL_CASH + ":* {cash}\n"
    "🔹 *" + LBL_DEBT + ":* {debt}\n"
    "🔹 *" + LBL_CR + ":* {cr}\n\n"
    "📈 *مؤشرات التقييم:*\n"
    "– *" + LBL_PE + ":* {tpe}\n"
    "– *" + LBL_PB + ":* {p2b}\n\n"
    "💼 *كفاءة الإدارة:*\n"
    "– *" + LBL_ROE + ":* {roe}\n"
    "– *" + LBL_ROA + ":* {roa}\n\n"
    "💰 *توزيعات الأرباح:*\n"
    "– *" + LBL_DY + ":* {dy}\n"
    "– *" + LBL_FREQ + ":* {freq}\n"
    "– *" + LBL_LAST_DIV + ":* {val}\n"
    "– *" + LBL_EX_DIV + ":* {ex}\u200C"
)

# Arabic labels for income statement metrics
LBL_INCOME        = "قائمة الدخل لعام"
LBL_REV           = "الإيرادات"
LBL_GROSS_PROFIT  = "إجمالي الربح"
LBL_GROSS_MARGIN  = "هامش إجمالي"
LBL_OP_INCOME     = "الدخل التشغيلي"
LBL_OP_MARGIN     = "هامش التشغيل"
LBL_NET_INCOME    = "صافي الربح"
LBL_NET_MARGIN    = "هامش صافي"
LBL_EBITDA        = "ابيتدا (EBITDA)"
LBL_EBITDA_MARGIN = "هامش EBITDA"
LBL_EPS           = "ربحية السهم (EPS)"
LBL_REV_GROWTH    = "نمو الإيرادات"

INCOME_TEMPLATE = (
    "*{name}* _({symbol})_ - *" + LBL_INCOME + "* ({year}) 📅\n\n"
    "🔹 *" + LBL_REV + ":* {revenue}\n"
    "🔹 *" + LBL_GROSS_PROFIT + ":* {gross_profit} ({gross_margin}%)\n"
    "🔹 *" + LBL_OP_INCOME + ":* {op_income} ({op_margin}%)\n"
    "🔹 *" + LBL_NET_INCOME + ":* {net_income} ({net_margin}%)\n"
    "🔹 *" + LBL_EBITDA + ":* {ebitda} ({ebitda_margin}%)\n"
    "🔹 *" + LBL_EPS + ":* {eps}\n"
    "🔹 *" + LBL_REV_GROWTH + ":* {rev_growth}\n\u200C"
)

# Arabic labels for balance sheet metrics
LBL_BALANCE             = "قائمة المركز المالي لعام"
LBL_TOTAL_ASSETS        = "إجمالي الأصول"
LBL_TOTAL_LIABILITIES   = "إجمالي الالتزامات"
LBL_EQUITY              = "حقوق المساهمين"
LBL_CURRENT_ASSETS      = "الأصول المتداولة"
LBL_CURRENT_LIABILITIES = "الالتزامات المتداولة"
LBL_WORKING_CAPITAL     = "رأس المال العامل"
LBL_DEBT_EQUITY_RATIO   = "نسبة الدين إلى حقوق الملكية"

# Balance sheet template
BALANCE_TEMPLATE = (
    "*{name}* _({symbol})_ - *" + LBL_BALANCE + "* ({year}) 📅\n\n"
    "🔹 *" + LBL_TOTAL_ASSETS + ":* {total_assets}\n"
    "🔹 *" + LBL_TOTAL_LIABILITIES + ":* {total_liabilities}\n"
    "🔹 *" + LBL_EQUITY + ":* {equity}\n"
    "🔹 *" + LBL_CURRENT_ASSETS + ":* {current_assets}\n"
    "🔹 *" + LBL_CURRENT_LIABILITIES + ":* {current_liabilities}\n"
    "🔹 *" + LBL_WORKING_CAPITAL + ":* {working_capital}\n"
    "🔹 *" + LBL_DEBT_EQUITY_RATIO + ":* {de_ratio}\n\u200C"

)

LBL_INTRO = "مقدمة سريعة"
TEXT_INTRO = (
    "مرحباً 👋! هذا البوت يعطيك ملخّصات وتحليلات مالية للشركات السعودية والأمريكية بشكل سهل وسريع. "
    "كل البيانات للتثقيف فقط وما تُعتبر توصية استثمار."
)

LBL_HOW_TO_START = "كيف أبدأ؟"
TEXT_HOW_TO_START = (
    "أكتب اسم الشركة أو رمزها (مثال: *AAPL* أو *أرامكو*).\n\n"
    "اختَر الخدمة من الأزرار الظاهرة:\n\n"
    "🔹 *ملخّص:* السعر الحالي والتغيّر اللحظي.\n"
    "🔹 *بيانات مالية:* مؤشرات العائد على السهم، الربحية، المديونية… إلخ.\n"
    "🔹 *القوائم المالية:* قائمة الدخل، الميزانية العمومية، التدفقات النقدية.\n"
    "🔹 *توزيعات الأرباح:* سجل التوزيعات وتواريخ الاستحقاق.\n"
    "🔹 *البيانات التاريخية:* الشموع السعرية حتى ٥ سنوات.\n"
    "🔹 *التحقّق الشرعي:* نسبة الأنشطة الشرعية حسب معايير الهيئة."
)

LBL_COMMANDS = "أوامر مختصرة داخل المحادثة"
TEXT_COMMANDS = (
    "🟢 */start* – بدء المحادثة مع البوت.\n"
    "📊 */status* – معرفة حالة الاشتراك.\n"
    "🔑 */activate* – إدخال كود التفعيل للحصول على المميزات المدفوعة.\n"
)

LBL_FAQ = "أسئلة متكررة"
FAQ_DATA_SOURCE = "❓ *من أين يتم جلب البيانات؟* جميع البيانات المستخدمة في هذا البوت مستخدمة من مصادر عالمية مثل موقع ياهو! فاينانس\n\n"
FAQ_MISSING_YEARS = "❓ *ليش أحياناً بعض السنوات مفقودة؟* الشركة لم تفصح أو التاريخ أقدم من قاعدة البيانات.\n\n"
FAQ_USAGE_LIMIT ="❓ *ما هو حد الاستهلاك اليومي؟* المستخدم المجاني له ٥ طلبات يومياً فقط، والمشترك يحصل على طلبات غير محدودة.\n\n"
FAQ_ACCURACY = "❓ *هل البيانات دقيقة؟* لا ليست دقيقة بنسبة 100٪، لكن تُعتبر دقتها عالية ويُفضّل دائماً التأكد من المصادر الرسمية الموثوقة.\n"
TEXT_FAQ = FAQ_DATA_SOURCE + FAQ_MISSING_YEARS + FAQ_USAGE_LIMIT + FAQ_ACCURACY

LBL_UPGRADE = "الترقية إلى الاشتراك المدفوع"
TEXT_UPGRADE = (
    "💳 لفتح جميع المميزات المتقدمة، اتبع الخطوات التالية:\n\n"
    "1️⃣ زيارة الموقع الإلكتروني: [https://salla.sa/dynamo-bot/]\n"
    "2️⃣ الاشتراك في المنتج المناسب لك\n"
    "3️⃣ ستحصل على مفتاح التفعيل فور إتمام العملية\n"
    "4️⃣ اضغط على زر */activate* داخل البوت\n"
    "5️⃣ أدخل المفتاح الذي حصلت عليه\n"
    "6️⃣ سيتم تفعيل اشتراكك مباشرة\n\n"
)

LBL_DISCLAIMER = "إخلاء المسؤولية"
TEXT_DISCLAIMER = (
    "⚠️ *تنبيه مهم:*\n"
    "المعلومات المعروضة في هذا البوت هي لأغراض تعليمية وتثقيفية فقط، "
    "ولا تُعد بأي حال من الأحوال توصية مالية أو استثمارية أو قانونية. "
    "يرجى دائماً تحري الدقة والرجوع إلى مصادر رسمية أو مستشار مالي معتمد قبل اتخاذ أي قرار."
)


LEARN_TEMPLATE = (
    "*١) " + LBL_INTRO + "*\n"
    + TEXT_INTRO + "\n\n"
    "*٢) " + LBL_HOW_TO_START + "*\n"
    + TEXT_HOW_TO_START + "\n\n"
    "*٣) " + LBL_COMMANDS + "*\n"
    + TEXT_COMMANDS + "\n\n"
    "*٤) " + LBL_FAQ + "*\n"
    + TEXT_FAQ + "\n\n"
    "*٥) " + LBL_UPGRADE + "*\n"
    + TEXT_UPGRADE + "\n\n"
    "*٦) " + LBL_DISCLAIMER + "*\n"
    + TEXT_DISCLAIMER + "\n\u200C"
)
