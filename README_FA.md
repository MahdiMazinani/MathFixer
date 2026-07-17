# MathFixer

## دستیار هوشمند اصلاح فرمول‌ها و اسناد علمی

**MathFixer خطاهای فرمول‌های ریاضی در Word و LaTeX را اصلاح می‌کند، دلیل هر تغییر را نشان می‌دهد، پایان‌نامه فارسی را بررسی می‌کند و خروجی PDF یا LaTeX می‌سازد.** این ابزار برای دانشجو و پژوهشگر طراحی شده است، نه فقط برنامه‌نویسان.

[دانلود آخرین نسخه ویندوز](https://github.com/MahdiMazinani/MathFixer/releases/latest) · [نقشه راه](docs/ROADMAP.md) · [English README](README.md)

![نمای رابط MathFixer](assets/app-preview.svg)

## قبل و بعد از اصلاح

![نمونه اصلاح فرمول](assets/before-after.svg)

برای هر تغییر، یک گزارش HTML خوانا ساخته می‌شود:

| قبل | بعد | دلیل |
|---|---|---|
| `\frac12` | `\frac{1}{2}` | آرگومان‌های کسر آکولاد نداشتند |
| `frac12` | `\frac{1}{2}` | بک‌اسلش و آکولادهای دستور وجود نداشتند |

## اجرای آسان در ویندوز؛ بدون برنامه‌نویسی

1. وارد صفحه [آخرین نسخه](https://github.com/MahdiMazinani/MathFixer/releases/latest) شوید.
2. فایل `MathFixer-Windows-Portable.zip` را دانلود و Extract کنید.
3. روی `MathFixer.exe` دوبار کلیک کنید.
4. فایل `.docx`، `.docm` یا `.tex` را داخل برنامه بکشید و «شروع اصلاح» را بزنید.

Python و Pandoc داخل نسخه قابل‌حمل قرار دارند و فایل اصلی هرگز بازنویسی نمی‌شود.

## امکانات اصلی

- اصلاح جداکننده‌ها، کسرها، براکت‌ها و تعدادی از محیط‌های خراب LaTeX؛
- تبدیل فرمول‌های LaTeX و UnicodeMath داخل Word به فرمول واقعی Office Math؛
- پشتیبانی صحیح از فرمول‌های نمایشی و فرمول‌های داخل متن؛
- بررسی فایل `.tex` از نظر package، citation، آکولاد، فونت فارسی و مشکلات bidi؛
- گزارش حرفه‌ای قبل/بعد به‌صورت HTML و گزارش فنی JSON؛
- ساخت PDF و تبدیل اختیاری Word به LaTeX؛
- رابط فارسی/انگلیسی، پوسته روشن/تیره، Drag & Drop و پردازش گروهی؛
- تحلیل اختیاری AI با کلید API خود کاربر؛ این قابلیت پیش‌فرض خاموش است.

MathFixer متن علمی را خودسرانه بازنویسی نمی‌کند، منبع جعلی نمی‌سازد، ماکرو اجرا نمی‌کند و فرمول تصویری را بدون بازبینی OCR نمی‌کند.

## مزیت ویژه پایان‌نامه فارسی

حالت فارسی مشکلات رایج `xepersian`، تنظیم فونت فارسی و لاتین، محیط‌های دوجهته، citationهای مفقود و گردش‌کار XeLaTeX را بررسی می‌کند. حالت‌های سازگاری برای قالبی که خود کاربر از دانشگاه شریف، تهران، امیرکبیر، تبریز یا آزاد فراهم می‌کند وجود دارد. این حالت‌ها قالب رسمی یا مورد تأیید دانشگاه‌ها نیستند.

## امنیت و حریم خصوصی

- فایل Word ورودی غیرقابل‌اعتماد در نظر گرفته می‌شود و ZIP/XML آن محدود و بررسی می‌شود.
- DTD، external entity و دسترسی شبکه XML غیرفعال است.
- برای PDF کردن DOCM فقط Word با غیرفعال‌سازی اجباری VBA پذیرفته می‌شود.
- بخش‌های تغییرنکرده Word بایت‌به‌بایت حفظ می‌شوند.
- تحلیل AI فقط با انتخاب کاربر انجام می‌شود؛ متن برای API ارسال می‌شود اما کلید در برنامه ذخیره نمی‌شود.

برای اسناد محرمانه، AI را فقط در صورت سازگاری با سیاست داده خود فعال کنید.

## نصب توسعه‌دهندگان

کاربر عادی ویندوز به این بخش نیاز ندارد.

```bash
git clone https://github.com/MahdiMazinani/MathFixer.git
cd MathFixer
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[gui,dev]"
mathfixer doctor
mathfixer-gui
```

## خط فرمان

```bash
mathfixer scan thesis.docx --mode balanced --json scan.json
mathfixer scan thesis.tex --json latex-scan.json
mathfixer convert thesis.docx --pdf --report
mathfixer convert thesis.tex --pdf --report
mathfixer word-to-latex thesis.docx thesis.tex
```

نسخه‌بندی و قابلیت‌های آینده در [ROADMAP](docs/ROADMAP.md) ثبت شده‌اند.
