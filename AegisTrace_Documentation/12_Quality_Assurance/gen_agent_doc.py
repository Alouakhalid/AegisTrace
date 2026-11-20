import json, inspect, re, pathlib
from enum import Enum
import schemas as S
from fields import F
from agents_prose import A
EX = pathlib.Path(__file__).parent/"examples"
ORDER = ["orchestrator","code_intelligence","recon","vulnerability_research","dynamic_testing","verification","remediation"]
SHARED = ["ErrorInfo","Metrics","Envelope","ResponseEnvelope"]

def tstr(a):
    if isinstance(a,type) and issubclass(a,Enum): return "enum "+a.__name__
    s=str(a).replace("typing.","").replace("schemas.","").replace("<class '","").replace("'>","")
    s=re.sub(r"Optional\[(.*)\]",r"\1 or null",s); s=s.replace(" | None"," or null").replace("Literal[","enum[")
    return s.replace("'","").replace("|","/")
def cons(f):
    out=[]
    for m in f.metadata:
        for k in ("pattern","ge","le","gt","lt","min_length"):
            v=getattr(m,k,None)
            if v is not None: out.append(f"{k}={v}".replace("|","/"))
    return ", ".join(out) or "-"
def model_table(name, lang):
    c=getattr(S,name); i=0 if lang=="en" else 1
    rows=[f"| `{n}` | `{tstr(f.annotation)}` | {'yes' if f.is_required() else 'no'} | {'`'+cons(f)+'`' if cons(f)!='-' else '-'} | {F[n][i]} |" for n,f in c.model_fields.items()]
    hdr = ("| Field | Type | Required | Constraints | Meaning |\n|---|---|---|---|---|" if lang=="en" else "| الحقل | النوع | إلزامي | القيود | المعنى |\n|---|---|---|---|---|")
    return f"**`{name}`**\n\n{hdr}\n"+"\n".join(rows)+"\n"

def err_rows(P,lang,i):
    yes,no=("yes","no") if lang=="en" else ("نعم","لا")
    return "\n".join(f"| `{x[0]}` | {yes if x[1] else no} | {x[2+i]} |" for x in P["errors"])
def src(names): return "```python\n"+"\n\n".join(inspect.getsource(getattr(S,n)).rstrip() for n in names)+"\n```\n"
def js(p): return "```json\n"+(EX/p).read_text().strip()+"\n```\n"

T = {
"en":dict(
 h_overview="Overview and Reading Guide", h_arch="Architecture and Communication", h_flow="Workflow, Dependencies and Control Loops",
 h_conv="Contract Conventions", h_exec="Complete Execution Example", h_ref="References",
 purpose="Purpose",resp="Responsibilities",flow="Internal workflow",tools="Required tools",io_in="Input contract",io_out="Output contract",
 valid="Validation rules",errs="Error cases",retry="Retry policy",req="Example request JSON",res="Example response JSON",pyd="Pydantic schema",
 fld="Field reference (every field)",cons="How the next agent consumes this output",
 err_hdr="| Code | Retryable | When |\n|---|---|---|",
 intro=("This document specifies how the seven official AegisTrace agents cooperate: responsibilities, hand-offs, control loops, failure handling, human approval checkpoints and the exact JSON contracts they exchange. The Pydantic models in Section 4 and in each agent chapter are the **single source of truth**; the JSON Schemas file `AegisTrace_Agent_JSON_Schemas.json` is exported from them, and every example JSON in this document was validated against those models.\n\n"
        "**Build order is not runtime order.** Agents are implemented in the order given in the Implementation Roadmap, but at runtime the Orchestrator schedules them by dependency, not by implementation order.\n\n"
        "**Scenario used in all examples.** An e-commerce API (ShopLite). Buyer A owns Order 100, buyer B owns Order 200. B sends `PATCH /api/v1/orders/100`; the API returns 403 yet the order's `shipping_address` changes. The same identifiers flow through all seven agents."),
 arch=("## 2.1 Seven agents\n\n![Seven agents](../diagrams/d02_agents.svg)\n\n"
       "## 2.2 Communication model\n\nAgents never call each other directly. The Orchestrator is the only router: it sends a validated request, receives a validated response, persists both in `agent_messages`, and decides what runs next. This keeps scope enforcement, retries and audit logging in one place.\n\n"
       "![Hub and spoke communication](../diagrams/d04c_comm.svg)\n\n"
       "Every message carries the shared envelope (ids, `schema_version`, `created_at`). The persisted form of a message is an `agent_messages` row:\n\n"
       "```json\n{\n  \"id\": \"msg_0192f450\",\n  \"scan_id\": \"scn_0192f1c9\",\n  \"task_id\": \"tsk_0192f306\",\n  \"correlation_id\": \"cor_0192f230\",\n  \"from_agent\": \"orchestrator\",\n  \"to_agent\": \"verification\",\n  \"message_type\": \"request\",\n  \"schema_version\": \"1.0.0\",\n  \"payload\": { \"...\": \"the VerificationRequest JSON\" },\n  \"created_at\": \"2026-11-17T09:32:10Z\"\n}\n```\n"),
 flow_md=("## 3.1 End-to-end sequence\n\n![Agent sequence](../diagrams/d05_sequence.svg)\n\n"
  "## 3.2 Task dependencies\n\n![Task dependency graph](../diagrams/d06_taskdeps.svg)\n\n"
  "## 3.3 Parallelism and loops (exact conditions)\n\n"
  "| Pattern | Condition | Bound |\n|---|---|---|\n"
  "| Parallel Recon | Scope validation passed; Recon needs only scope and API spec | Code Intelligence and Recon start together (`parallel_group=g1`) |\n"
  "| Research requests code context | A hypothesis references a route, symbol or flow missing from the Repository Security Map | 2 requests per hypothesis |\n"
  "| Verification returns to Dynamic Testing | verdict would be `unconfirmed` for lack of evidence and the plan allows more variants | 2 extra rounds |\n"
  "| Remediation asks Code Intelligence | Root cause lies in code outside mapped files | 2 clarifications |\n"
  "| Orchestrator halts | Scope invalid, sandbox unavailable, credentials missing, or `ScopeViolation` | Immediate and audit-logged |\n"
  "| Patch rework | Tests fail, exploit still reproduces, or reviewer requests changes | 3 patch attempts |\n\n"
  "## 3.4 State transitions\n\n![Task states](../diagrams/d07_states.svg)\n\n"
  "## 3.5 Failure and retry\n\n![Failure and retry](../diagrams/d08_retry.svg)\n\n"
  "## 3.6 Human approval checkpoints\n\n"
  "| # | Checkpoint | Trigger | Who decides |\n|---|---|---|---|\n"
  "| 1 | Authorization attestation | Before any active test | Engagement owner (recorded in `engagements.attested_by`) |\n"
  "| 2 | Test-plan approval | Only when `environment=staging_approved` | Reviewer |\n"
  "| 3 | Patch approval | Remediation returned `patch_ready_for_review` | Reviewer (`approvals` table). A human performs any merge |\n\n"
  "![Remediation and approval](../diagrams/d17_approval.svg)\n\n"
  "## 3.7 What each agent hands to the next\n\n"
  "| From | To | Handed over |\n|---|---|---|\n| Orchestrator | Code Intelligence, Recon | task, scope, repository, API spec |\n| Code Intelligence | Vulnerability Research | routes, mechanisms, models, graph ref, candidate invariants |\n| Recon | Vulnerability Research | endpoints, technologies, attack surface ref, intel refs (untrusted) |\n| Vulnerability Research | Dynamic Testing | hypotheses, test plans with state checks |\n| Dynamic Testing | Verification | executed cases, state diffs, evidence ids |\n| Verification | Remediation | finding id, verdict, severity, supporting evidence |\n| Remediation | Human reviewer | patch, test results, replay evidence, approval request |\n"),
 conv=("## 4.1 Identifiers\n\n`project_id` (`prj_`), `engagement_id` (`eng_`), `scan_id` (`scn_`), `task_id` (`tsk_`), `agent_run_id` (`run_`), `finding_id` (`fnd_`), `evidence_id` (`evd_`), `correlation_id` (`cor_`). Format: prefix, underscore, at least 8 hex characters (UUIDv7-derived recommended). The same strings are database primary keys.\n\n"
  "## 4.2 Rules\n\n- `schema_version` follows semantic versioning. Minor releases add optional fields only; a breaking change raises the major version and both versions run side by side during migration. Consumers ignore nothing silently: models use `extra=\"forbid\"`.\n- Timestamps are ISO 8601 UTC with a trailing `Z`.\n- Status values are closed enums; unknown values are rejected.\n- Secrets never appear in contracts; credentials are references (`cred_*`) resolved only inside the sandbox.\n- A response with `status` other than `succeeded` carries an `error` object and `output` may be null.\n- On a schema validation failure the agent gets one repair attempt that includes the validation message; a second failure marks the task `failed`.\n\n"
  "## 4.3 Shared base models\n\n"),
 err_title="## 4.4 Error response format\n\nA blocked task caused by a scope violation:\n\n",
 log_title="## 4.5 Structured log format\n\nOne JSON object per line, always carrying the ids so a whole assessment can be traced by `correlation_id`:\n\n```json\n{\"ts\":\"2026-11-17T09:32:05Z\",\"level\":\"INFO\",\"correlation_id\":\"cor_0192f230\",\"scan_id\":\"scn_0192f1c9\",\"task_id\":\"tsk_0192f305\",\"agent_run_id\":\"run_0192f405\",\"agent\":\"dynamic_testing\",\"event\":\"http_request_sent\",\"identity_id\":\"id_buyer_b\",\"method\":\"PATCH\",\"path\":\"/api/v1/orders/100\",\"status_code\":403,\"duration_ms\":41,\"scope_gate\":\"allowed\"}\n```\n",
 exec_md=("The table follows the validated example payloads (all timestamps UTC, 2026-11-17).\n\n"
  "| Time | Agent | Event |\n|---|---|---|\n"
  "| 09:30:00 | Orchestrator | Receives request; five scope checks pass; plan with 6 stages created |\n"
  "| 09:30:10 | Code Intelligence, Recon | Start in parallel (`g1`) |\n"
  "| 09:30:51 | Recon | 2 endpoints, 2 technologies, 1 OWASP reference (marked untrusted) |\n"
  "| 09:31:02 | Code Intelligence | 86 files; `PATCH /orders/{order_id}` has no authorization check; invariant `inv_order_owner_only` proposed (0.86) |\n"
  "| 09:31:30 | Vulnerability Research | Hypothesis `hyp_idor_patch_order` (priority 1) with a paired-identity plan; skill `hunt-idor` |\n"
  "| 09:32:05 | Dynamic Testing | Owner gets 200; non-owner gets 403; **state diff shows `shipping_address` changed** |\n"
  "| 09:32:50 | Verification | Reproduced 3 of 3; confidence 0.97; severity medium (integrity impact); finding `fnd_0192f200` confirmed |\n"
  "| 09:34:20 | Remediation | Root cause: write committed before the 403 is produced; patch on `fix/aegistrace-fnd-0192f200`; 42/42 unit, 18/18 integration, 120/120 regression pass; exploit no longer reproduces |\n"
  "| after | Human reviewer | Approves, rejects or requests changes. Only a human merges |\n\n"
  "All durations and token figures in the examples are **illustrative sample values**, not measurements."),
 refs="- Pydantic: https://docs.pydantic.dev/\n- JSON Schema 2020-12: https://json-schema.org/draft/2020-12/schema\n- CrewAI: https://docs.crewai.com/\n- LangChain: https://docs.langchain.com/\n- Groq: https://console.groq.com/docs\n- Tavily Search API: https://docs.tavily.com/documentation/api-reference/endpoint/search\n- Claude-BugHunter: https://github.com/elementalsouls/Claude-BugHunter\n"),
"ar":dict(
 h_overview="نظرة عامة ودليل القراءة", h_arch="المعمارية والتواصل", h_flow="سير العمل والاعتماديات وحلقات التحكم",
 h_conv="اتفاقيات العقود", h_exec="مثال تنفيذ كامل", h_ref="المراجع",
 purpose="الغرض",resp="المسؤوليات",flow="سير العمل الداخلي",tools="الأدوات المطلوبة",io_in="عقد المدخلات",io_out="عقد المخرجات",
 valid="قواعد التحقق",errs="حالات الخطأ",retry="سياسة إعادة المحاولة",req="مثال JSON للطلب",res="مثال JSON للاستجابة",pyd="مخطط Pydantic",
 fld="مرجع الحقول (كل حقل)",cons="كيف يستهلك الوكيل التالي هذه المخرجات",
 err_hdr="| الرمز | قابل للإعادة | متى |\n|---|---|---|",
 intro=("تحدد هذه الوثيقة كيف يتعاون وكلاء AegisTrace الرسميون السبعة: المسؤوليات، والتسليم بينهم، وحلقات التحكم، ومعالجة الفشل، ونقاط الموافقة البشرية، وعقود JSON الدقيقة التي يتبادلونها. نماذج Pydantic في القسم 4 وفي فصل كل وكيل هي **المصدر الوحيد للحقيقة**؛ ومنها يُصدَّر ملف `AegisTrace_Agent_JSON_Schemas.json`، وكل مثال JSON هنا جرى التحقق منه قبال تلك النماذج.\n\n"
        "**ترتيب البناء ليس ترتيب التشغيل.** تُنفَّذ الوكلاء بالترتيب الوارد في خارطة الطريق، لكن المنسّق وقت التشغيل يجدولها حسب الاعتماديات لا حسب ترتيب التنفيذ.\n\n"
        "**السيناريو المستخدم في كل الأمثلة.** واجهة متجر إلكتروني (ShopLite). المشتري A يملك الطلب 100، والمشتري B يملك الطلب 200. يرسل B الطلب `PATCH /api/v1/orders/100` فتعيد الواجهة 403 ومع ذلك يتغير `shipping_address` للطلب. وتنتقل المعرّفات نفسها عبر الوكلاء السبعة."),
 arch=("## 2.1 الوكلاء السبعة\n\n![الوكلاء السبعة](../diagrams/d02_agents.svg)\n\n"
       "## 2.2 نموذج التواصل\n\nلا يستدعي الوكلاء بعضهم مباشرة. المنسّق هو الموجّه الوحيد: يرسل طلباً مُتحقَّقاً منه ويستلم استجابة مُتحقَّقاً منها ويحفظهما في `agent_messages` ثم يقرر ما يعمل بعد ذلك. وهذا يجمع إنفاذ النطاق وإعادة المحاولة وتسجيل التدقيق في مكان واحد.\n\n"
       "![التواصل بنمط المحور والأذرع](../diagrams/d04c_comm.svg)\n\n"
       "تحمل كل رسالة الغلاف المشترك (المعرّفات و`schema_version` و`created_at`). والصورة المحفوظة للرسالة هي صف في `agent_messages`:\n\n"
       "```json\n{\n  \"id\": \"msg_0192f450\",\n  \"scan_id\": \"scn_0192f1c9\",\n  \"task_id\": \"tsk_0192f306\",\n  \"correlation_id\": \"cor_0192f230\",\n  \"from_agent\": \"orchestrator\",\n  \"to_agent\": \"verification\",\n  \"message_type\": \"request\",\n  \"schema_version\": \"1.0.0\",\n  \"payload\": { \"...\": \"the VerificationRequest JSON\" },\n  \"created_at\": \"2026-11-17T09:32:10Z\"\n}\n```\n"),
 flow_md=("## 3.1 التسلسل الكامل\n\n![تسلسل الوكلاء](../diagrams/d05_sequence.svg)\n\n"
  "## 3.2 اعتماديات المهام\n\n![رسم اعتماديات المهام](../diagrams/d06_taskdeps.svg)\n\n"
  "## 3.3 التوازي والحلقات (الشروط الدقيقة)\n\n"
  "| النمط | الشرط | الحد |\n|---|---|---|\n"
  "| استطلاع متوازٍ | نجح التحقق من النطاق؛ ويحتاج الاستطلاع إلى النطاق ومواصفات API فقط | يبدأ Code Intelligence وRecon معاً (`parallel_group=g1`) |\n"
  "| طلب سياق شيفرة من وكيل البحث | فرضية تشير إلى مسار أو رمز أو تدفق غير موجود في الخريطة الأمنية | طلبان لكل فرضية |\n"
  "| عودة التحقق إلى الاختبار الديناميكي | الحكم سيكون `unconfirmed` لنقص الدليل والخطة تسمح بمتغيرات إضافية | جولتان إضافيتان |\n"
  "| الإصلاح يستوضح من Code Intelligence | السبب الجذري في شيفرة خارج الملفات المرسومة | استيضاحان |\n"
  "| توقف المنسّق | نطاق غير صالح أو العزل غير متاح أو بيانات اعتماد مفقودة أو `ScopeViolation` | فوري ويُسجَّل في التدقيق |\n"
  "| إعادة عمل الإصلاح | فشل الاختبارات أو بقاء الاستغلال أو طلب المراجع تغييرات | 3 محاولات إصلاح |\n\n"
  "## 3.4 انتقالات الحالة\n\n![حالات المهمة](../diagrams/d07_states.svg)\n\n"
  "## 3.5 الفشل وإعادة المحاولة\n\n![الفشل وإعادة المحاولة](../diagrams/d08_retry.svg)\n\n"
  "## 3.6 نقاط الموافقة البشرية\n\n"
  "| # | نقطة الموافقة | المحفّز | من يقرر |\n|---|---|---|---|\n"
  "| 1 | إقرار التصريح | قبل أي اختبار نشط | مالك التقييم (يُسجَّل في `engagements.attested_by`) |\n"
  "| 2 | اعتماد خطة الاختبار | فقط عند `environment=staging_approved` | المراجع |\n"
  "| 3 | اعتماد الإصلاح | أعاد الإصلاح `patch_ready_for_review` | المراجع (جدول `approvals`). ويتولى إنسان أي دمج |\n\n"
  "![الإصلاح والموافقة](../diagrams/d17_approval.svg)\n\n"
  "## 3.7 ماذا يسلّم كل وكيل للتالي\n\n"
  "| من | إلى | المُسلَّم |\n|---|---|---|\n| المنسّق | Code Intelligence وRecon | المهمة والنطاق والمستودع ومواصفات API |\n| Code Intelligence | Vulnerability Research | المسارات والآليات والنماذج ومرجع الرسم والثوابت المرشحة |\n| Recon | Vulnerability Research | نقاط النهاية والتقنيات ومرجع سطح الهجوم ومراجع الاستخبارات (غير موثوقة) |\n| Vulnerability Research | Dynamic Testing | الفرضيات وخطط الاختبار مع فحوص الحالة |\n| Dynamic Testing | Verification | الحالات المنفذة وفروق الحالة ومعرّفات الأدلة |\n| Verification | Remediation | معرّف النتيجة والحكم والخطورة والأدلة الداعمة |\n| Remediation | المراجع البشري | الإصلاح ونتائج الاختبارات وأدلة الإعادة وطلب الموافقة |\n"),
 conv=("## 4.1 المعرّفات\n\n`project_id` (`prj_`)، `engagement_id` (`eng_`)، `scan_id` (`scn_`)، `task_id` (`tsk_`)، `agent_run_id` (`run_`)، `finding_id` (`fnd_`)، `evidence_id` (`evd_`)، `correlation_id` (`cor_`). الصيغة: بادئة ثم شرطة سفلية ثم 8 خانات سداسية عشرية على الأقل (يُقترح اشتقاقها من UUIDv7). والسلاسل نفسها هي المفاتيح الأساسية في قاعدة البيانات.\n\n"
  "## 4.2 القواعد\n\n- يتبع `schema_version` الترقيم الدلالي. الإصدارات الفرعية تضيف حقولاً اختيارية فقط؛ والتغيير الكاسر يرفع الإصدار الرئيسي ويعمل الإصداران جنباً إلى جنب أثناء الترحيل. لا شيء يُتجاهل بصمت: النماذج تستخدم `extra=\"forbid\"`.\n- الطوابع الزمنية بصيغة ISO 8601 بالتوقيت العالمي وتنتهي بـ `Z`.\n- قيم الحالة قوائم مغلقة؛ القيم المجهولة تُرفض.\n- لا تظهر الأسرار في العقود؛ بيانات الاعتماد مراجع (`cred_*`) لا تُحلّ إلا داخل العزل.\n- الاستجابة التي حالتها غير `succeeded` تحمل كائن `error` وقد يكون `output` فارغاً.\n- عند فشل التحقق من المخطط يُمنح الوكيل محاولة إصلاح واحدة تتضمن رسالة التحقق؛ وفشل الثانية يجعل المهمة `failed`.\n\n"
  "## 4.3 النماذج الأساسية المشتركة\n\n"),
 err_title="## 4.4 صيغة استجابة الخطأ\n\nمهمة محجوبة بسبب انتهاك النطاق:\n\n",
 log_title="## 4.5 صيغة السجل المهيكل\n\nكائن JSON واحد في كل سطر يحمل المعرّفات دائماً ليمكن تتبع تقييم كامل عبر `correlation_id`:\n\n```json\n{\"ts\":\"2026-11-17T09:32:05Z\",\"level\":\"INFO\",\"correlation_id\":\"cor_0192f230\",\"scan_id\":\"scn_0192f1c9\",\"task_id\":\"tsk_0192f305\",\"agent_run_id\":\"run_0192f405\",\"agent\":\"dynamic_testing\",\"event\":\"http_request_sent\",\"identity_id\":\"id_buyer_b\",\"method\":\"PATCH\",\"path\":\"/api/v1/orders/100\",\"status_code\":403,\"duration_ms\":41,\"scope_gate\":\"allowed\"}\n```\n",
 exec_md=("يتبع الجدول حمولات الأمثلة المُتحقَّق منها (كل الأوقات بالتوقيت العالمي، 2026-11-17).\n\n"
  "| الوقت | الوكيل | الحدث |\n|---|---|---|\n"
  "| 09:30:00 | المنسّق | يستلم الطلب؛ تنجح فحوص النطاق الخمسة؛ تُنشأ خطة من 6 مراحل |\n"
  "| 09:30:10 | Code Intelligence وRecon | يبدآن بالتوازي (`g1`) |\n"
  "| 09:30:51 | Recon | نقطتا نهاية وتقنيتان ومرجع OWASP واحد (موسوم غير موثوق) |\n"
  "| 09:31:02 | Code Intelligence | 86 ملفاً؛ المسار `PATCH /orders/{order_id}` بلا فحص تفويض؛ يقترح الثابت `inv_order_owner_only` (0.86) |\n"
  "| 09:31:30 | Vulnerability Research | الفرضية `hyp_idor_patch_order` (أولوية 1) مع خطة هويات مزدوجة؛ المهارة `hunt-idor` |\n"
  "| 09:32:05 | Dynamic Testing | المالك يحصل على 200 وغير المالك على 403؛ **فرق الحالة يُظهر تغيّر `shipping_address`** |\n"
  "| 09:32:50 | Verification | أُعيد الإنتاج 3 من 3؛ الثقة 0.97؛ الخطورة medium (أثر على السلامة)؛ النتيجة `fnd_0192f200` مؤكدة |\n"
  "| 09:34:20 | Remediation | السبب الجذري: تُثبَّت الكتابة قبل إنتاج 403؛ إصلاح على `fix/aegistrace-fnd-0192f200`؛ نجاح 42/42 وحدة و18/18 تكامل و120/120 انحدار؛ ولم يعد الاستغلال يتكرر |\n"
  "| لاحقاً | المراجع البشري | يوافق أو يرفض أو يطلب تغييرات. وحده الإنسان يدمج |\n\n"
  "كل الأزمنة وأعداد الرموز في الأمثلة **قيم توضيحية** وليست قياسات."),
 refs="- Pydantic: https://docs.pydantic.dev/\n- JSON Schema 2020-12: https://json-schema.org/draft/2020-12/schema\n- CrewAI: https://docs.crewai.com/\n- LangChain: https://docs.langchain.com/\n- Groq: https://console.groq.com/docs\n- Tavily Search API: https://docs.tavily.com/documentation/api-reference/endpoint/search\n- Claude-BugHunter: https://github.com/elementalsouls/Claude-BugHunter\n"),
}

def build(lang):
    t=T[lang]; i=0 if lang=="en" else 1; o=[]
    o.append(f"# 1. {t['h_overview']}\n\n{t['intro']}\n")
    o.append(f"# 2. {t['h_arch']}\n\n{t['arch']}")
    o.append(f"# 3. {t['h_flow']}\n\n{t['flow_md']}")
    o.append(f"# 4. {t['h_conv']}\n\n{t['conv']}"+"\n\n".join(model_table(n,lang) for n in SHARED)+"\n"+src(SHARED)+"\n"+t['err_title']+js("error_example.json")+"\n"+t['log_title'])
    for k,a in enumerate(ORDER):
        P=A[a]; n=5+k
        e=[f"# {n}. {P['title'][i]}\n",f"## {n}.1 {t['purpose']}\n\n{P['purpose'][i]}\n",
           f"## {n}.2 {t['resp']}\n\n"+"\n".join("- "+x for x in P['resp'][i])+"\n",
           f"## {n}.3 {t['flow']}\n\n"+"\n".join(f"{j}. {x}" for j,x in enumerate(P['flow'][i],1))+"\n",
           f"## {n}.4 {t['tools']}\n\n"+"\n".join("- "+x for x in P['tools'][i])+"\n",
           f"## {n}.5 {t['valid']}\n\n"+"\n".join("- "+x for x in P['valid'][i])+"\n",
           f"## {n}.6 {t['errs']}\n\n{t['err_hdr']}\n"+err_rows(P,lang,i)+"\n",
           f"## {n}.7 {t['retry']}\n\n{P['retry'][i]}\n",
           f"## {n}.8 {t['req']}\n\n"+js(f"{a}_request.json"),
           f"## {n}.9 {t['res']}\n\n"+js(f"{a}_response.json"),
           f"## {n}.10 {t['pyd']}\n\n"+src(P['models']),
           f"## {n}.11 {t['fld']}\n\n"+"\n".join(model_table(m,lang) for m in P['models']),
           f"## {n}.12 {t['cons']}\n\n{P['consume'][i]}\n"]
        o.append("\n".join(e))
    o.append(f"# 12. {t['h_exec']}\n\n{t['exec_md']}\n")
    o.append(f"# 13. {t['h_ref']}\n\n{t['refs']}")
    return "\n".join(o)
for lang in ("en","ar"):
    pathlib.Path(f"../content/agents_{lang}.md").write_text(build(lang),encoding="utf-8")
    print(lang, len(build(lang)))
