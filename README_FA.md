# MathFixer

## اصلاح فرمول واقعی، عیب‌یابی پروژه LaTeX و اعتبارسنجی سند علمی

**MathFixer فرمول‌های نوشته‌شده در Word و پروژه‌های LaTeX را پیدا می‌کند، فقط خطاهای نحوی مطمئن را اصلاح می‌کند، فرمول‌های Word را به Office Math واقعی تبدیل می‌کند، خروجی را اعتبارسنجی می‌کند و برای هر تصمیم گزارش قبل/بعد می‌سازد.** مخاطب آن دانشجو، پژوهشگر، نویسنده پایان‌نامه، ویراستار علمی و واحد پشتیبانی دانشگاه است؛ نه فقط برنامه‌نویس.

[دانلود آخرین نسخه ویندوز](https://github.com/MahdiMazinani/MathFixer/releases/latest) · [English README](README.md) · [امنیت](SECURITY.md) · [معماری](docs/ARCHITECTURE.md)

![رابط دسکتاپ MathFixer](assets/app-preview.svg)

## کار اصلی برنامه در یک تصویر

سمت چپ چیزی است که معمولاً داخل مقاله یا پایان‌نامه دیده می‌شود: LaTeX خام، جداکننده خراب یا UnicodeMath که مثل متن عادی در Word مانده است. سمت راست نتیجه مورد انتظار است: فرمول واقعی ریاضی در همان سند، بدون جابه‌جایی متن، جدول، تصویر، استایل و Reference.

![تبدیل چند فرمول علمی سنگین توسط MathFixer](assets/before-after.svg)

MathFixer بازنویس عمومی متن نیست. وظیفه اصلی آن **اصلاح فرمول و سند علمی همراه با مدرک تغییرات** است.

## برای هر فایل از کدام مسیر استفاده کنیم؟

| ورودی شما | مسیر مناسب | خروجی اصلی |
|---|---|---|
| فایل Word دارای LaTeX یا UnicodeMath | دکمهٔ یک‌مرحله‌ای «اسکن و اصلاح فایل‌ها» | Word با چیدمان حفظ‌شده و فرمول Office Math |
| یک فایل `.tex` | دکمهٔ یک‌مرحله‌ای «اسکن و اصلاح فایل‌ها» | کپی TEX اصلاح‌شده و گزارش |
| پایان‌نامه LaTeX چندفایلی | حالت «اصلاح کل پروژه» | کپی پروژه همراه با اصلاح فایل‌های include‌شده |
| تبدیل پروژه Word به LaTeX | Project conversion | فایل TEX و پوشه استخراج‌شده `media/` |
| تبدیل پروژه LaTeX به Word | Project conversion | DOCX با استفاده از تصاویر پروژه |
| PDF قبل و بعد | مقایسه PDFها | تصویر اختلاف هر صفحه و گزارش عددی |
| ارسال گزارش برای استاد/ویراستار | Review bundle | فایل آفلاین `.mfxreview`؛ بدون متن منبع در حالت پیش‌فرض |

## نصب در ویندوز بدون Python

### نسخه قابل‌حمل

1. وارد صفحه [آخرین Release](https://github.com/MahdiMazinani/MathFixer/releases/latest) شوید.
2. فایل `MathFixer-Windows-Portable.zip` را دانلود کنید.
3. ZIP را کامل Extract کنید.
4. روی `MathFixer.exe` دوبار کلیک کنید.

Python و Pandoc داخل این بسته قرار دارند. برنامه را مستقیم از داخل ZIP اجرا نکنید.

### نسخه نصب‌شونده

اگر Release شامل `MathFixer-Setup.exe` بود، آن را دانلود و نصب کنید. Installer فقط زمانی امضای Authenticode دارد که مالک پروژه certificate امضای کد را تنظیم کرده باشد. در نسخه بدون امضا ممکن است SmartScreen هشدار دهد؛ قبل از اجرا checksum و منبع دانلود را بررسی کنید.

### بررسی سالم بودن دانلود

هر Release فایل `SHA256SUMS.txt` دارد:

```powershell
Get-FileHash .\MathFixer-Windows-Portable.zip -Algorithm SHA256
Get-Content .\SHA256SUMS.txt
```

هش فایل دانلودشده باید دقیقاً با مقدار نوشته‌شده برای همان نام فایل برابر باشد.

## آموزش کامل رابط گرافیکی

### مرحله ۱: افزودن فایل

فایل `.docx`، `.docm` یا `.tex` را داخل کادر بزرگ برنامه بکشید، یا «افزودن فایل» را بزنید. با «افزودن پوشه» می‌توانید چند سند را یکجا وارد صف کنید. صف می‌تواند هم‌زمان فایل Word و LaTeX داشته باشد.

فایل اصلی هیچ‌وقت به‌عنوان خروجی بازنویسی نمی‌شود. برنامه پسوندی مانند `_mathfixed` اضافه می‌کند یا برای پروژه LaTeX یک پوشه هم‌سطح می‌سازد.

### مرحله ۲: انتخاب حالت تشخیص

- **متعادل — پیشنهادشده:** LaTeX صحیح، جداکننده خراب، UnicodeMath و خطوطی که واضحاً معادله‌اند.
- **ایمن:** فقط ناحیه‌هایی با delimiter صریح؛ مناسب وقتی متن علمی نمادهای زیادی دارد.
- **پیشرفته:** معادلات plain-text قوی را هم بررسی می‌کند؛ حتماً نتیجه را بازبینی کنید.

اسکن به‌تنهایی هیچ فایلی را تغییر نمی‌دهد.

### مرحله ۳: انتخاب خروجی‌ها

- **گزارش HTML و JSON:** برای سند مهم همیشه روشن باشد.
- **حالت اتمیک:** اگر حتی یک فرمول Word با اطمینان تبدیل نشد، خروجی ناقص منتشر نمی‌شود. برنامه پس از خطا موارد تشخیص‌داده‌شده را خودکار برای «بازبینی انتخاب‌شده» آماده می‌کند؛ مورد اشتباه را غیرفعال یا اصلاح و دوباره تلاش کنید.
- **ساخت PDF:** اختیاری است. در GUI،‏ Word و LibreOffice هرکدام حداکثر ۴۵ ثانیه فرصت دارند. شکست PDF مانع ذخیره خروجی معتبر Word نمی‌شود و به‌صورت هشدار نمایش داده می‌شود.
- **تبدیل Word به LaTeX:** در کنار Word اصلاح‌شده خروجی TEX می‌سازد.
- **تحلیل AI:** گزینهٔ «خاموش — پیشنهادشده» هیچ ارتباط شبکه‌ای ایجاد نمی‌کند. فقط پس از انتخاب صریح provider، متن TEX ارسال می‌شود و انتظار می‌تواند حداکثر ۹۰ ثانیه باشد.
- **اصلاح کل پروژه LaTeX:** فایل‌های `\input`، `\include` و `\subfile` امن را دنبال می‌کند و کپی کل پروژه را اصلاح می‌کند.
- **جایگزینی خروجی:** اجازه بازنویسی خروجی موجود؛ روی فایل اصلی اثری ندارد.

برای سند عادی، حالت پایان‌نامه را روی «خاموش — بدون قالب دانشگاهی» نگه دارید. فقط وقتی فایل `.cls` یا `.sty` دانشگاه را دارید profile همان دانشگاه را انتخاب کنید. نام دانشگاه در برنامه به معنی قالب رسمی یا تأیید دانشگاه نیست.

### مرحله ۴: اسکن و اصلاح با یک دکمه

یک‌بار «اسکن و اصلاح فایل‌ها» را بزنید. برنامه تشخیص، اصلاح، اعتبارسنجی و ساخت خروجی را پشت سر هم انجام می‌دهد. در حالت پیش‌فرض Word فقط یک‌بار اسکن می‌شود. اگر AI را برای TEX فعال کرده باشید، ابتدا diagnostics هوش مصنوعی اجرا می‌شود و مرحلهٔ انتظار همراه با سقف زمانی روی نوار وضعیت نمایش داده می‌شود.

برای فایل Word، مرحلهٔ جاری مستقیماً در ردیف سند دیده می‌شود: باز کردن، اسکن فرمول، تبدیل با Pandoc، اعمال امن تغییرات، نوشتن یا اعتبارسنجی. هر batch در Pandoc حداکثر ۳۰ ثانیه و کل مرحلهٔ تبدیل فرمول حداکثر ۴۵ ثانیه فرصت دارد. در timeout، درخت پردازش متوقف می‌شود و انتظار برای batchهای بعدی تکرار نمی‌شود. اگر هیچ فرمولی پیدا نشود، Pandoc اصلاً اجرا نمی‌شود.

اگر «جایگزینی فایل‌های خروجی موجود» خاموش باشد، وجود خروجی قبلی دیگر باعث ناموفق‌شدن تبدیل نمی‌شود. MathFixer فایل قبلی را دست‌نخورده نگه می‌دارد و خودکار نام آزاد بعدی، مانند `article_mathfixed_2.docx`، را انتخاب می‌کند. نام‌های همراه PDF،‏ TEX و گزارش نیز با هم بررسی می‌شوند تا هیچ خروجی قبلی بازنویسی نشود.

پس از پایان، داشبورد تعداد مشکلات، اصلاح‌های انجام‌شده، هشدارها و خروجی‌ها را نشان می‌دهد. روی ردیف دوبار کلیک کنید یا «بازبینی انتخاب‌شده» را بزنید.

برای فرمول‌های Word می‌توانید:

- false positive را غیرفعال کنید؛
- فرمول نرمال‌شده را قبل از تبدیل ویرایش کنید؛
- نوع تشخیص، میزان اطمینان و دلیل repair را ببینید.

برای پروژه LaTeX می‌توانید ببینید:

- متن قبل و بعد؛
- نام دقیق فایل و شماره خط؛
- citation، reference و package مفقود؛
- خطای compile log و محل آن در فایل include‌شده؛
- مشکل فونت، bidi، XeLaTeX، قالب و plugin.

Word فقط بعد از اعتبارسنجی preservation منتشر می‌شود. پروژه LaTeX ابتدا در یک پوشه جدا کپی می‌شود و بعد فایل‌های include‌شده در همان کپی اصلاح می‌شوند.

### مرحله ۵: کنترل گزارش

«گزارش تغییرات» را باز کنید. گزارش HTML شامل این موارد است:

- فرمول قبل و بعد؛
- دلیل هر اصلاح؛
- بخش Word، پاراگراف، فایل TEX و شماره خط؛
- کد، شدت، پیام و راه‌حل هر diagnostic؛
- تعداد موارد پیدا‌شده، تبدیل‌شده و ردشده.

برای پایان‌نامه یا مقاله مهم، فقط بعد از خواندن گزارش خروجی را تحویل دهید.

## MathFixer با Word چه می‌کند؟

برنامه document اصلی، header، footer، footnote، endnote و بخش‌های پشتیبانی‌شده Word را اسکن می‌کند. هر فرمول به‌صورت fragment جدا توسط Pandoc به OMML تبدیل می‌شود. Pandoc کل فایل Word را از نو نمی‌سازد.

اعتبارسنجی خروجی کنترل می‌کند که:

- فایل‌های داخلی بسته Word بی‌دلیل کم یا زیاد نشده باشند؛
- بخش‌های تغییرنکرده بایت‌به‌بایت ثابت مانده باشند؛
- متن عادی اطراف فرمول جابه‌جا نشده باشد؛
- جدول، drawing، relationship و section سالم باشند؛
- تعداد Math objectهای جدید با تعداد تبدیل موفق برابر باشد.

فرمول نمایشی به `m:oMathPara` و فرمول داخل متن به Office Math inline تبدیل می‌شود.

## تحلیل پروژه LaTeX چندفایلی

وقتی main TEX را باز می‌کنید، MathFixer یک index محدود و امن می‌سازد. فقط includeهای نسبی که داخل ریشه پروژه باشند خوانده می‌شوند. مسیر absolute یا `../` خارج از پروژه به‌عنوان خطا گزارش می‌شود و خوانده نمی‌شود.

بررسی‌های پروژه‌ای:

- فایل include‌شده مفقود یا ناامن؛
- citation در همه BibTeXهای declareشده؛
- reference مفقود و label تکراری در همه فایل‌ها؛
- محل دقیق هر repair در فایل و خط؛
- package مفقود، آکولاد نامتعادل و محیط table خراب؛
- تشخیص فایل فعال در log تو‌در‌توی TeX؛
- مشکلات xepersian، فونت و bidi؛
- الزامات template adapter کاربر؛
- diagnosticهای pluginهای Python.

حداکثر تعداد فایل و حجم کل source محدود است تا include graph خراب یا مخرب باعث پردازش بی‌نهایت نشود.

## حالت پایان‌نامه فارسی

این حالت موارد رایج زیر را بررسی می‌کند:

- گردش‌کار XeLaTeX؛
- تنظیم `xepersian`؛
- فونت فارسی و لاتین؛
- محیط‌های راست‌به‌چپ و چپ‌به‌راست؛
- citation و reference مفقود؛
- حضور class/style قالبی که کاربر فراهم کرده است.

profile سازگاری برای شریف، تهران، امیرکبیر، تبریز و آزاد وجود دارد. MathFixer قالب دارای حق نشر دانشگاه را توزیع نمی‌کند.

### ساخت adapter برای قالب خودتان

فایل [نمونه adapter](examples/template-adapter.example.json) را کپی و ویرایش کنید:

```json
{
  "name": "My University Thesis Template",
  "version": "1.0.0",
  "api_version": "2.0",
  "profile": "custom-university",
  "engine": "xelatex",
  "required_files": ["university-thesis.cls"],
  "required_commands": ["\\universitytitle", "\\supervisor"]
}
```

```bash
mathfixer scan thesis/main.tex --template-adapter adapter.json --json scan.json
mathfixer project-repair thesis/main.tex thesis-fixed --template-adapter adapter.json --report
```

Adapter داده‌محور است و امکان اجرای کد دلخواه ندارد.

## PDF و مقایسه بصری

برای Word، ابتدا Microsoft Word در ویندوز و سپس LibreOffice امتحان می‌شود. هر موتور در رابط گرافیکی سقف ۴۵ ثانیه دارد و در timeout همراه با child process متوقف می‌شود. اگر هر دو ناموفق باشند، DOCX اعتبارسنجی‌شده باقی می‌ماند و ردیف سند «تکمیل شد با هشدار» را نشان می‌دهد. تبدیل DOCM به PDF فقط با Word و غیرفعال‌سازی اجباری VBA مجاز است. تبدیل DOCM با LibreOffice عمداً رد می‌شود. PDF فایل TEX به XeLaTeX نیاز دارد.

برای مقایسه، «مقایسه PDFها» را بزنید، PDF اصلی و اصلاح‌شده و پوشه خروجی را انتخاب کنید. برنامه:

- همه صفحه‌ها را render می‌کند؛
- تعداد و ابعاد صفحه را مقایسه می‌کند؛
- نسبت اختلاف پیکسل را محاسبه می‌کند؛
- برای هر صفحه heatmap قرمز می‌سازد؛
- `visual-comparison.json` را ذخیره می‌کند.

```bash
mathfixer pdf-compare original.pdf repaired.pdf pdf-diff --dpi 120 --tolerance 0.002
```

این ابزار وجود تغییر بصری را نشان می‌دهد، نه درست‌بودن علمی آن را.

## تبدیل پروژه همراه با media

### Word به LaTeX

```bash
mathfixer project-convert thesis.docx thesis-latex
```

خروجی شامل TEX مستقل و پوشه `media/` است. خروجی ابتدا در staging ساخته و سپس اتمیک منتشر می‌شود. پوشه غیرخالی فقط با `--overwrite` جایگزین می‌شود.

### LaTeX به Word

```bash
mathfixer project-convert thesis/main.tex thesis.docx
mathfixer project-convert thesis/main.tex thesis.docx --reference-docx university-style.docx
```

ریشه پروژه به‌عنوان resource path در اختیار Pandoc قرار می‌گیرد تا تصاویر محلی پیدا شوند. DOCX قبل از انتشار اعتبارسنجی می‌شود.

هیچ تبدیل بین Word و LaTeX برای همه macroها، floatها، bibliography styleها و classهای سفارشی کاملاً lossless نیست. source اصلی را نگه دارید و خروجی را بازبینی کنید.

## هوش مصنوعی اختیاری و خصوصی

AI فقط توضیح و پیشنهاد می‌دهد و هیچ تغییری را خودکار اعمال نمی‌کند. انتخابگر GUI به‌صورت صریح روی «خاموش — پیشنهادشده» قرار دارد؛ در این حالت هیچ درخواست AI ساخته نمی‌شود و repair قطعی بدون اینترنت کار می‌کند. انتخاب OpenAI، provider سازگار یا Ollama فقط روی TEX اثر دارد و ممکن است تا timeout نودثانیه‌ای منتظر بماند.

### OpenAI

```powershell
$env:OPENAI_API_KEY="your-key"
$env:MATHFIXER_AI_MODEL="gpt-5-mini"
```

در GUI گزینه OpenAI را انتخاب کنید یا:

```bash
mathfixer scan thesis.tex --ai-provider openai
```

### endpoint خصوصی سازگار با OpenAI

```powershell
$env:MATHFIXER_AI_ENDPOINT="https://ai.example.edu/v1/chat/completions"
$env:MATHFIXER_AI_MODEL="institution-model"
$env:MATHFIXER_AI_API_KEY="private-key"
```

```bash
mathfixer scan thesis.tex --ai-provider openai-compatible
```

endpoint راه‌دور باید HTTPS باشد. HTTP فقط برای localhost یا IP خصوصی پذیرفته می‌شود.

### Ollama محلی

```powershell
$env:MATHFIXER_AI_ENDPOINT="http://127.0.0.1:11434/api/generate"
$env:MATHFIXER_AI_MODEL="qwen2.5-coder:7b"
```

```bash
mathfixer scan thesis.tex --ai-provider ollama
```

کلیدها در تنظیمات برنامه ذخیره نمی‌شوند و فقط از environment خوانده می‌شوند.

## همکاری اختیاری و آفلاین

MathFixer حساب cloud اجباری ندارد. از گزارش JSON یک بسته بازبینی آفلاین بسازید:

```bash
mathfixer review-bundle thesis.report.json review.mfxreview
```

source پیش‌فرض داخل بسته نیست. افزودن source نیازمند consent صریح است:

```bash
mathfixer review-bundle thesis.report.json review.mfxreview --include-source thesis.tex
```

API پایتون client اختیاری برای backend خصوصی کاربر نیز دارد؛ این repository ادعا نمی‌کند سرویس cloud عمومی MathFixer را میزبانی می‌کند.

## معنی فایل‌های خروجی

| فایل | کاربرد |
|---|---|
| `*_mathfixed.docx` | Word اعتبارسنجی‌شده با فرمول‌های native |
| `*_mathfixed.tex` | کپی TEX اصلاح‌شده |
| `*_mathfixed_project/` | کپی پروژه چندفایلی اصلاح‌شده |
| `*.report.html` | گزارش خوانای تغییرات و هشدارها |
| `*.report.json` | audit فنی قابل پردازش |
| `*.pdf` | PDF اختیاری و اعتبارسنجی‌شده |
| `page-###-diff.png` | تصویر اختلاف بصری صفحه |
| `visual-comparison.json` | اعداد مقایسه PDF |
| `*.mfxreview` | بسته قابل‌حمل بازبینی |

## امنیت و حریم خصوصی

- DOCX/DOCM یک ZIP غیرقابل‌اعتماد محسوب می‌شود.
- DTD، external entity و شبکه XML غیرفعال است.
- ZIP تکراری، رمزگذاری‌شده، بیش‌ازحد فشرده یا بزرگ رد می‌شود.
- include پروژه اجازه خروج از root را ندارد.
- VBA فایل DOCM توسط MathFixer اجرا نمی‌شود.
- AI و collaboration فقط با انتخاب صریح کاربر فعال می‌شوند.
- source بدون consent داخل review bundle قرار نمی‌گیرد.
- انتشار خروجی تا حد ممکن اتمیک است.

برای استقرار server حتماً [SECURITY.md](SECURITY.md) را بخوانید.

## محدودیت‌هایی که باید بدانید

MathFixer این کارها را انجام نمی‌دهد:

- OCR فرمولی که فقط تصویر است؛
- ساخت citation یا منبع علمی جعلی؛
- تضمین معنای علمی فرمول؛
- بازنویسی خودکار متن پایان‌نامه؛
- اجرای VBA یا کد دلخواه adapter؛
- توزیع قالب رسمی دانشگاه؛
- تضمین round-trip کامل همه قابلیت‌های Word/LaTeX؛
- ارائه cloud عمومی اجباری.

موارد مبهم باید توسط انسان بررسی شوند.

## رفع اشکال سریع

| مشکل | راه بررسی |
|---|---|
| Pandoc پیدا نشد | نسخه Portable را اجرا کنید یا Pandoc نصب و `mathfixer doctor` را اجرا کنید |
| هیچ فرمولی پیدا نشد | Balanced را امتحان کنید؛ Aggressive فقط با بازبینی |
| false positive زیاد است | Safe و delimiterهای صریح را انتخاب کنید |
| بار اول تبدیل ناموفق شد | روی «بازبینی انتخاب‌شده» بزنید؛ برنامه پس از خطا اسکن بازیابی را خودکار انجام می‌دهد. موارد اشتباه را غیرفعال یا اصلاح و دوباره اجرا کنید |
| روی مرحله Pandoc یا تبدیل فرمول مانده | نسخه 2.0.3 کل این مرحله را حداکثر پس از ۴۵ ثانیه متوقف می‌کند. اگر نسخه قدیمی بیشتر منتظر ماند، آن را ببندید، آخرین Release را نصب و دوباره امتحان کنید. فایل اصلی تغییر نکرده است |
| روی تبدیل نزدیک ۹۰٪ مانده | PDF در حال اجراست؛ هر موتور حداکثر ۴۵ ثانیه فرصت دارد. در شکست، Word معتبر با هشدار ذخیره می‌شود |
| PDF ساخته نشد | Word/LibreOffice برای DOCX یا XeLaTeX برای TEX را نصب کنید؛ خروجی Word را از «باز کردن خروجی» بردارید |
| DOCM PDF رد شد | روی Windows از Microsoft Word استفاده کنید |
| AI کار نمی‌کند | provider و environment variableها را بررسی کنید؛ repair عادی مستقل است |
| include ناامن است | فایل را داخل root پروژه ببرید و مسیر relative بدهید |
| citation اشتباه missing است | `.bib` صحیح را با `\bibliography` یا `\addbibresource` معرفی کنید |
| SmartScreen هشدار می‌دهد | SHA-256 را بررسی کنید؛ اعتماد عمومی به certificate نیاز دارد |
| خروجی وجود دارد یا هر تلاش دوباره ناموفق است | نسخه 2.0.4 یا جدیدتر را نصب کنید؛ با خاموش‌بودن replace، برنامه خروجی قبلی را نگه می‌دارد و خودکار خروجی شماره‌دار می‌سازد |

## نمونه‌های خط فرمان

```bash
mathfixer doctor

mathfixer scan thesis.docx --mode balanced --json word-scan.json
mathfixer scan thesis/main.tex --json latex-scan.json

mathfixer convert article.docx --report --pdf
mathfixer convert chapter.tex --report

mathfixer project-repair thesis/main.tex thesis-fixed --report --pdf

mathfixer project-convert thesis.docx thesis-latex
mathfixer project-convert thesis/main.tex thesis.docx --reference-docx style.docx

mathfixer pdf-compare before.pdf after.pdf pdf-diff

mathfixer plugins
mathfixer plugins --template-adapter adapter.json

mathfixer review-bundle thesis.report.json thesis-review.mfxreview
```

برای گزینه‌های هر دستور از `mathfixer <command> --help` استفاده کنید.

## API عمومی نسخه ۲

```python
from mathfixer import API_VERSION, DetectionMode, repair, scan
from mathfixer.features.pdf_compare import compare_pdfs
from mathfixer.features.project_conversion import word_to_latex_project

report = scan("thesis/main.tex", thesis_profile="generic")
for finding in report.findings:
    print(finding.file, finding.line, finding.code, finding.message)

repair(
    "article.docx",
    "article_mathfixed.docx",
    mode=DetectionMode.BALANCED,
)

word_to_latex_project("article.docx", "article-latex")
visual = compare_pdfs("before.pdf", "after.pdf", "pdf-diff")
print(API_VERSION, visual.passed, visual.changed_ratio)
```

## Plugin SDK نسخه ۲

pluginهای Python با entry point گروه `mathfixer.plugins` منتشر می‌شوند و فقط diagnostic برمی‌گردانند:

```python
from mathfixer.plugins import PluginContext, PluginDiagnostic

class MyPlugin:
    name = "my-lab-rules"
    version = "1.0.0"
    api_version = "2.0"

    def analyze(self, context: PluginContext) -> list[PluginDiagnostic]:
        return [
            PluginDiagnostic(
                code="LAB_POLICY",
                message="Example diagnostic",
                suggestion="Explain a verifiable action",
                file=context.main_file.name,
                plugin=self.name,
            )
        ]
```

SDK امکان نوشتن مستقیم source را به plugin نمی‌دهد. plugin خراب یا ناسازگار به finding جدا تبدیل می‌شود و برنامه را crash نمی‌کند.

## نصب برای توسعه‌دهنده

```bash
git clone https://github.com/MahdiMazinani/MathFixer.git
cd MathFixer
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
python -m pip install -e ".[gui,dev]"
mathfixer doctor
mathfixer-gui
```

اگر editable install انجام نداده‌اید، تست را با `PYTHONPATH=src` اجرا کنید.

```bash
ruff check .
python -m compileall -q src
python -m unittest discover -s tests -v
```

CI روی Windows و Linux و Python 3.10 تا 3.12 اجرا می‌شود و GUI smoke، CodeQL و build Release را هم دارد.

### ساخت نسخه ویندوز

```powershell
.\scripts\build_windows.ps1 -Python python
.\scripts\build_installer.ps1 -Version 2.0.0
```

برای امضا مسیر PFX و password را به `build_installer.ps1` بدهید. GitHub Actions از secretهای `MATHFIXER_CERTIFICATE_BASE64` و `MATHFIXER_CERTIFICATE_PASSWORD` استفاده می‌کند. بدون آن‌ها Installer صادقانه unsigned است.

## وضعیت نسخه‌ها

- **محدوده 1.3:** پروژه چندفایلی، محل دقیق log، template adapter، regression بصری PDF و integration نصب/امضا.
- **محدوده 2.0:** Plugin SDK و API پایدار، تبدیل دوطرفه پروژه با media، AI محلی/خصوصی و collaboration اختیاری.
- **اصلاح پایداری 2.0.3:** سقف قطعی Pandoc، حفظ workerهای GUI، نمایش مرحله پردازش و تست تبدیل با EXE نهایی.
- **اصلاح خروجی 2.0.4:** نام‌گذاری شماره‌دار بدون برخورد و نمایش مستقیم دلیل فارسی خطا.

جزئیات در [CHANGELOG.md](CHANGELOG.md) و [ROADMAP.md](docs/ROADMAP.md) ثبت شده است.

## مجوز

MathFixer تحت MIT منتشر می‌شود. Pandoc داخل بسته همچنان GPL-2.0-or-later است و توزیع‌کننده باید [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) را رعایت کند. قالب دانشگاه و plugin شخص ثالث مجوز مستقل خود را دارد.
