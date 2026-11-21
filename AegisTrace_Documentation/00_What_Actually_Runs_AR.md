# AegisTrace — ما الذي يعمل فعلًا في المستودع

التاريخ: 2026-11-21. هذا الملف يصف الكود الذي يبدأ بأمر `python3 backend/run.py`. ملفات PDF الأقدم والمقاطع الطويلة في `12_Quality_Assurance/source_markdown/` تصف تصميمًا مستهدفًا. عند الاختلاف، هذا الملف يتبع المصدر.

## التشغيل

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r backend/requirements.txt
cp .env.example .env
python3 backend/run.py
```

الواجهة على `http://127.0.0.1:8000`. توثيق الـ API التفاعلي على `http://127.0.0.1:8000/docs`.

المتغيرات الاختيارية: `GROQ_API_KEY` و`GROQ_MODEL` و`TAVILY_API_KEY`. لقطات قاعدة بيانات الاختبار تبحث عن `AEGIS_SANDBOX_DB`. إذا لم يُضبط هذا المتغير يتخطى الفحص الاختبار الحي.

## ما يدخل العملية

| الجزء | المكان | الواقع |
|---|---|---|
| واجهة HTTP | `backend/app.py` | FastAPI، الإصدار في الكود `2.0.0`، والملفات الثابتة من `frontend/` |
| تشغيل الفحص | `backend/pipeline.py` | `ScanExecutionManager.run_pipeline` |
| قاعدة البيانات | `memory and database/database.py` | SQLite. المخطط في `memory and database/schema.sql` (30 جدولًا). الاتصال الافتراضي ذاكرة مؤقتة `:memory:` |
| الواجهة | `frontend/` | JavaScript عادي وموجّه بالمسار بعد `#`. ثماني عشرة شاشة من `landing` إلى `supporting` |
| الوكلاء | `agents/` | سبع وحدات. وحدات الوكلاء تستورد CrewAI |
| تحليل الشيفرة | `tools/code_intel_tools.py` | Tree-sitter لبايثون، ووحدة `ast`، وNetworkX |
| المهارات | `backend/bughunter_router.py` | يقرأ `SKILL.md` من القرص ويربط فئة الفحص باسم المهارة |
| البحث الخارجي | `backend/integration_service.py` | Tavily عند وجود المفتاح فقط. غياب المفتاح تخطٍ، لا قائمة ثغرات مخترعة |
| أدوات HTTP | `tools/dynamic_testing_tools.py` | HTTPX وبوابة نطاق وتطبيق Flask داخل العملية في `dummy_web/` |

غير موجود في عملية التشغيل: Next.js وReact وTypeScript وPostgreSQL وpgvector وصندوق Docker يبدأ مع الفحص ودمج Git تلقائي.

## الوكلاء السبعة وما يستدعيه الفحص

الوحدات موجودة، ونقاط الدخول هي `run_orchestration` و`run_code_intelligence` و`run_recon` و`run_vulnerability_research` و`run_dynamic_testing` و`run_verification` و`run_remediation`.

`run_pipeline` يستدعي المنسّق وتحليل الشيفرة والاستطلاع، كل واحد داخل `try`. الفشل يُسجَّل والفحص يكمل. بحث الثغرات يُستورد باسم `run_vuln_research` وهذا الاسم غير معرّف في الوحدة، فالمرحلة تسجّل تحذيرًا ولا تشغّل `run_vulnerability_research`.

لا يستدعي الاختبار الديناميكي ولا التحقق ولا الإصلاح:

- الاختبار الديناميكي يكتب سطر سجل فقط. بدون `AEGIS_SANDBOX_DB` يقول إن الفحص تُرك. ومع وجود المتغير يكتب سطرًا آخر ولا ينشئ `DynamicTestingAgent`.
- التحقق لا يستدعي `VerificationAgent`. ينسخ `potential_risk_areas` من تحليل المستودع إلى قواميس في الذاكرة، ويثبت الثقة على `0.92` ورقم السطر على `17`. الحالة النصية `confirmed` إذا وُجد أي ثابت أمني، وإلا `needs_verification`. لا تُكتب في عمود `findings.verdict`.
- الإصلاح ينشئ الكائن `RemediationAgent` إذا وُجدت تلك القواميس ولا يستدعي `run_remediation`. قائمة الرقع تبقى فارغة.

الفحص المكتمل إذن مرور ثابت مع توجيه مهارات وسجلات. ليس إعادة إنتاج لاستغلال، ولا فرق حالة قاعدة بيانات، ولا رقعة مختبرة.

## ما يُخزَّن

المسار يحاول، ويبتلع الخطأ إذا فشل:

1. المستخدم `usr_admin_001`. قيد SQLite هو `LIKE 'usr_%'` فقط، فالإدخال مقبول.
2. مشروع وارتباط ونطاق وفحص.
3. نقاط نهاية بمعرّفات `ep_{scan_id}_{index}`.
4. الثوابت الراجعة من تحليل الشيفرة.
5. الفرضيات بحالة `approved`. الجدول لا يقبل إلا `proposed` أو `testing` أو `confirmed` أو `unconfirmed` أو `rejected`، وفئات محدودة. الصف الذي لا يطابق يُسقطه `except` فارغ.

نتائج «المؤكدة» ترجع في قاموس الفحص وتبقى في `active_scans`. لا تُدرج في جدول `findings`.

`POST /api/v1/projects` يمرر `source_type='git'` بينما العمود يقبل `github` و`zip` فقط، فإدخال المستودع يفشل.

`GET /api/v1/stats/overview` يعد النتائج ذات `status = 'resolved'`. قيد الحالة في الجدول هو `open|patch_proposed|fixed|accepted_risk|wont_fix`. هذا العد يبقى صفرًا. درجة الأمان تستخدم `verdict = 'confirmed'` وهذا يطابق المخطط.

جداول الأدلة ولقطات الحالة وسجل التدقيق فيها محفزات تمنع `UPDATE` و`DELETE`. هذا الجزء حقيقي. أعمدة التضمين نص `TEXT` وليست نوع متجه، ولا توجد دالة استرجاع هجين في مخطط التشغيل.

## واجهات موجودة لكنها ليست قياسًا

- `GET /api/v1/benchmarks` يقرأ `evaluation_report.csv` لكل وكيل إن نجح التحليل. عند الفشل يرجع دقة واستدعاء وF1 بقيمة `1.0` و`total_evaluations: 0`. الملفات الموجودة فحوصات عقود صغيرة، ومعدل إعادة الإنتاج ونجاح الرقعة يُجبران على `1.0` دائمًا.
- `GET /api/v1/reports/{scan_id}` يرجع شهادة ثابتة: نتيجة واحدة، وصفر محلولة، و`Zero_False_Positives: true`، بلا قراءة لصف الفحص.

## العقود والمهارات والواجهة

نماذج المنسّق في `agents/orchestrator_agent/validation.py`. نسخة التوثيق في `10_Technical_Appendices/agent_contracts_pydantic.py` وملف JSON Schema في جذر الحزمة. المحقق يحمّل ملف JSON من جذر المستودع.

المهارات نص من `SKILL.md`. الموجّه لا ينفّذها كودًا ولا يجعلها وكيلًا ثامنًا. الترخيص في المستودع المستنسخ: MIT للشيفرة وCC BY 4.0 لنص المهارة.

مسارات الواجهة في `frontend/js/app.js`: `landing` و`auth` و`dashboard` و`projects` و`wizard` و`workspace` و`code_intel` و`surface` و`findings` و`finding_details` و`verification` و`remediation` و`approvals` و`reports` و`skills` و`benchmarks` و`settings` و`supporting`.

## ما الذي كانت الوثائق القديمة تخطئه

| الادعاء | الكود |
|---|---|
| الواجهة Next.js | `frontend/` جافاسكربت عادي |
| قاعدة التشغيل PostgreSQL مع pgvector | `AegisDatabase` ينفّذ ملف SQLite |
| الفحص يشغّل اختبارات بهويتين وإعادة ثلاثية ورقعة pytest | هذه المراحل أسطر سجل. الأصناف لا تُستدعى |
| النتيجة المؤكدة صف بحكم وشدة وبصمة دليل | النتائج قواميس بايثون. تقرير الـ API شهادة ثابتة |
| دقة 100٪ على المنصة | ملفات CSV فحوصات محلية، والـ API يملأ `1.0` عند فشل القراءة |
| الرسوم في `../diagrams/` | الملفات في `11_Architecture_Diagrams/` |

سكربت PostgreSQL باقٍ كمسودة ترحيل ومُعلَّم في رأس الملف. التطبيق لا يفتحه.

ملفات PDF الستة بُنيت من نص التصميم ولم تُعد توليدها هنا. الوصف الحالي هو هذا الملف ونسخته الإنجليزية `00_What_Actually_Runs.md`.
