# 1. نظرة عامة ودليل القراءة

تحدد هذه الوثيقة كيف يتعاون وكلاء AegisTrace الرسميون السبعة: المسؤوليات، والتسليم بينهم، وحلقات التحكم، ومعالجة الفشل، ونقاط الموافقة البشرية، وعقود JSON الدقيقة التي يتبادلونها. نماذج Pydantic في القسم 4 وفي فصل كل وكيل هي **المصدر الوحيد للحقيقة**؛ ومنها يُصدَّر ملف `AegisTrace_Agent_JSON_Schemas.json`، وكل مثال JSON هنا جرى التحقق منه قبال تلك النماذج.

**ترتيب البناء ليس ترتيب التشغيل.** تُنفَّذ الوكلاء بالترتيب الوارد في خارطة الطريق، لكن المنسّق وقت التشغيل يجدولها حسب الاعتماديات لا حسب ترتيب التنفيذ.

**السيناريو المستخدم في كل الأمثلة.** واجهة متجر إلكتروني (ShopLite). المشتري A يملك الطلب 100، والمشتري B يملك الطلب 200. يرسل B الطلب `PATCH /api/v1/orders/100` فتعيد الواجهة 403 ومع ذلك يتغير `shipping_address` للطلب. وتنتقل المعرّفات نفسها عبر الوكلاء السبعة.

# 2. المعمارية والتواصل

## 2.1 الوكلاء السبعة

![الوكلاء السبعة](../diagrams/d02_agents.svg)

## 2.2 نموذج التواصل

لا يستدعي الوكلاء بعضهم مباشرة. المنسّق هو الموجّه الوحيد: يرسل طلباً مُتحقَّقاً منه ويستلم استجابة مُتحقَّقاً منها ويحفظهما في `agent_messages` ثم يقرر ما يعمل بعد ذلك. وهذا يجمع إنفاذ النطاق وإعادة المحاولة وتسجيل التدقيق في مكان واحد.

![التواصل بنمط المحور والأذرع](../diagrams/d04c_comm.svg)

تحمل كل رسالة الغلاف المشترك (المعرّفات و`schema_version` و`created_at`). والصورة المحفوظة للرسالة هي صف في `agent_messages`:

```json
{
  "id": "msg_0192f450",
  "scan_id": "scn_0192f1c9",
  "task_id": "tsk_0192f306",
  "correlation_id": "cor_0192f230",
  "from_agent": "orchestrator",
  "to_agent": "verification",
  "message_type": "request",
  "schema_version": "1.0.0",
  "payload": { "...": "the VerificationRequest JSON" },
  "created_at": "2026-11-17T09:32:10Z"
}
```

# 3. سير العمل والاعتماديات وحلقات التحكم

## 3.1 التسلسل الكامل

![تسلسل الوكلاء](../diagrams/d05_sequence.svg)

## 3.2 اعتماديات المهام

![رسم اعتماديات المهام](../diagrams/d06_taskdeps.svg)

## 3.3 التوازي والحلقات (الشروط الدقيقة)

| النمط | الشرط | الحد |
|---|---|---|
| استطلاع متوازٍ | نجح التحقق من النطاق؛ ويحتاج الاستطلاع إلى النطاق ومواصفات API فقط | يبدأ Code Intelligence وRecon معاً (`parallel_group=g1`) |
| طلب سياق شيفرة من وكيل البحث | فرضية تشير إلى مسار أو رمز أو تدفق غير موجود في الخريطة الأمنية | طلبان لكل فرضية |
| عودة التحقق إلى الاختبار الديناميكي | الحكم سيكون `unconfirmed` لنقص الدليل والخطة تسمح بمتغيرات إضافية | جولتان إضافيتان |
| الإصلاح يستوضح من Code Intelligence | السبب الجذري في شيفرة خارج الملفات المرسومة | استيضاحان |
| توقف المنسّق | نطاق غير صالح أو العزل غير متاح أو بيانات اعتماد مفقودة أو `ScopeViolation` | فوري ويُسجَّل في التدقيق |
| إعادة عمل الإصلاح | فشل الاختبارات أو بقاء الاستغلال أو طلب المراجع تغييرات | 3 محاولات إصلاح |

## 3.4 انتقالات الحالة

![حالات المهمة](../diagrams/d07_states.svg)

## 3.5 الفشل وإعادة المحاولة

![الفشل وإعادة المحاولة](../diagrams/d08_retry.svg)

## 3.6 نقاط الموافقة البشرية

| # | نقطة الموافقة | المحفّز | من يقرر |
|---|---|---|---|
| 1 | إقرار التصريح | قبل أي اختبار نشط | مالك التقييم (يُسجَّل في `engagements.attested_by`) |
| 2 | اعتماد خطة الاختبار | فقط عند `environment=staging_approved` | المراجع |
| 3 | اعتماد الإصلاح | أعاد الإصلاح `patch_ready_for_review` | المراجع (جدول `approvals`). ويتولى إنسان أي دمج |

![الإصلاح والموافقة](../diagrams/d17_approval.svg)

## 3.7 ماذا يسلّم كل وكيل للتالي

| من | إلى | المُسلَّم |
|---|---|---|
| المنسّق | Code Intelligence وRecon | المهمة والنطاق والمستودع ومواصفات API |
| Code Intelligence | Vulnerability Research | المسارات والآليات والنماذج ومرجع الرسم والثوابت المرشحة |
| Recon | Vulnerability Research | نقاط النهاية والتقنيات ومرجع سطح الهجوم ومراجع الاستخبارات (غير موثوقة) |
| Vulnerability Research | Dynamic Testing | الفرضيات وخطط الاختبار مع فحوص الحالة |
| Dynamic Testing | Verification | الحالات المنفذة وفروق الحالة ومعرّفات الأدلة |
| Verification | Remediation | معرّف النتيجة والحكم والخطورة والأدلة الداعمة |
| Remediation | المراجع البشري | الإصلاح ونتائج الاختبارات وأدلة الإعادة وطلب الموافقة |

# 4. اتفاقيات العقود

## 4.1 المعرّفات

`project_id` (`prj_`)، `engagement_id` (`eng_`)، `scan_id` (`scn_`)، `task_id` (`tsk_`)، `agent_run_id` (`run_`)، `finding_id` (`fnd_`)، `evidence_id` (`evd_`)، `correlation_id` (`cor_`). الصيغة: بادئة ثم شرطة سفلية ثم 8 خانات سداسية عشرية على الأقل (يُقترح اشتقاقها من UUIDv7). والسلاسل نفسها هي المفاتيح الأساسية في قاعدة البيانات.

## 4.2 القواعد

- يتبع `schema_version` الترقيم الدلالي. الإصدارات الفرعية تضيف حقولاً اختيارية فقط؛ والتغيير الكاسر يرفع الإصدار الرئيسي ويعمل الإصداران جنباً إلى جنب أثناء الترحيل. لا شيء يُتجاهل بصمت: النماذج تستخدم `extra="forbid"`.
- الطوابع الزمنية بصيغة ISO 8601 بالتوقيت العالمي وتنتهي بـ `Z`.
- قيم الحالة قوائم مغلقة؛ القيم المجهولة تُرفض.
- لا تظهر الأسرار في العقود؛ بيانات الاعتماد مراجع (`cred_*`) لا تُحلّ إلا داخل العزل.
- الاستجابة التي حالتها غير `succeeded` تحمل كائن `error` وقد يكون `output` فارغاً.
- عند فشل التحقق من المخطط يُمنح الوكيل محاولة إصلاح واحدة تتضمن رسالة التحقق؛ وفشل الثانية يجعل المهمة `failed`.

## 4.3 النماذج الأساسية المشتركة

**`ErrorInfo`**

| الحقل | النوع | إلزامي | القيود | المعنى |
|---|---|---|---|---|
| `code` | `str` | yes | - | رمز خطأ ثابت مقروء آلياً |
| `message` | `str` | yes | - | رسالة خطأ مقروءة |
| `retryable` | `bool` | yes | - | هل يجوز للمنسّق إعادة المحاولة |
| `details` | `dict or null` | no | - | سياق خطأ مهيكل اختياري |


**`Metrics`**

| الحقل | النوع | إلزامي | القيود | المعنى |
|---|---|---|---|---|
| `duration_ms` | `int` | yes | `ge=0` | الزمن الفعلي للتشغيل |
| `llm_calls` | `int` | yes | `ge=0` | عدد استدعاءات النموذج |
| `input_tokens` | `int` | yes | `ge=0` | رموز المطالبة المستهلكة |
| `output_tokens` | `int` | yes | `ge=0` | رموز الإكمال المنتجة |


**`Envelope`**

| الحقل | النوع | إلزامي | القيود | المعنى |
|---|---|---|---|---|
| `schema_version` | `str` | yes | `pattern=^\d+\.\d+\.\d+$` | إصدار العقد بالترقيم الدلالي |
| `correlation_id` | `str` | yes | `pattern=^cor_[0-9a-f]{8,}$` | يتتبع تقييماً واحداً عبر الوكلاء والسجلات |
| `project_id` | `str` | yes | `pattern=^prj_[0-9a-f]{8,}$` | المشروع الأعلى |
| `engagement_id` | `str` | yes | `pattern=^eng_[0-9a-f]{8,}$` | التقييم المصرّح به ونطاقه |
| `scan_id` | `str` | yes | `pattern=^scn_[0-9a-f]{8,}$` | تنفيذ واحد لسير العمل |
| `task_id` | `str` | yes | `pattern=^tsk_[0-9a-f]{8,}$` | وحدة عمل واحدة للوكيل |
| `agent_run_id` | `str` | yes | `pattern=^run_[0-9a-f]{8,}$` | استدعاء واحد للوكيل؛ كل إعادة محاولة لها معرّف جديد |
| `created_at` | `str` | yes | `pattern=^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$` | طابع زمني ISO 8601 بالتوقيت العالمي |


**`ResponseEnvelope`**

| الحقل | النوع | إلزامي | القيود | المعنى |
|---|---|---|---|---|
| `schema_version` | `str` | yes | `pattern=^\d+\.\d+\.\d+$` | إصدار العقد بالترقيم الدلالي |
| `correlation_id` | `str` | yes | `pattern=^cor_[0-9a-f]{8,}$` | يتتبع تقييماً واحداً عبر الوكلاء والسجلات |
| `project_id` | `str` | yes | `pattern=^prj_[0-9a-f]{8,}$` | المشروع الأعلى |
| `engagement_id` | `str` | yes | `pattern=^eng_[0-9a-f]{8,}$` | التقييم المصرّح به ونطاقه |
| `scan_id` | `str` | yes | `pattern=^scn_[0-9a-f]{8,}$` | تنفيذ واحد لسير العمل |
| `task_id` | `str` | yes | `pattern=^tsk_[0-9a-f]{8,}$` | وحدة عمل واحدة للوكيل |
| `agent_run_id` | `str` | yes | `pattern=^run_[0-9a-f]{8,}$` | استدعاء واحد للوكيل؛ كل إعادة محاولة لها معرّف جديد |
| `created_at` | `str` | yes | `pattern=^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$` | طابع زمني ISO 8601 بالتوقيت العالمي |
| `status` | `enum TaskStatus` | yes | - | حالة المهمة (قائمة مغلقة) |
| `warnings` | `list[str]` | no | - | مشكلات غير قاتلة ظهرت أثناء التشغيل |
| `error` | `ErrorInfo or null` | no | - | كائن الخطأ عندما لا تكون الحالة succeeded |
| `metrics` | `Metrics` | yes | - | استهلاك الموارد في التشغيل |

```python
class ErrorInfo(Strict):
    code: str = Field(description="Stable machine-readable error code, e.g. SCOPE_VIOLATION")
    message: str
    retryable: bool
    details: Optional[dict] = None

class Metrics(Strict):
    duration_ms: int = Field(ge=0)
    llm_calls: int = Field(ge=0)
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)

class Envelope(Strict):
    schema_version: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    correlation_id: str = Field(pattern=r"^cor_[0-9a-f]{8,}$")
    project_id: str = Field(pattern=r"^prj_[0-9a-f]{8,}$")
    engagement_id: str = Field(pattern=r"^eng_[0-9a-f]{8,}$")
    scan_id: str = Field(pattern=r"^scn_[0-9a-f]{8,}$")
    task_id: str = Field(pattern=r"^tsk_[0-9a-f]{8,}$")
    agent_run_id: str = Field(pattern=r"^run_[0-9a-f]{8,}$")
    created_at: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$", description="ISO 8601 UTC")

class ResponseEnvelope(Envelope):
    status: TaskStatus
    warnings: list[str] = []
    error: Optional[ErrorInfo] = None
    metrics: Metrics
```

## 4.4 صيغة استجابة الخطأ

مهمة محجوبة بسبب انتهاك النطاق:

```json
{
  "schema_version": "1.0.0",
  "correlation_id": "cor_0192f230",
  "project_id": "prj_0192f1a0",
  "engagement_id": "eng_0192f1b4",
  "scan_id": "scn_0192f1c9",
  "task_id": "tsk_0192f305",
  "agent_run_id": "run_0192f409",
  "created_at": "2026-11-17T09:32:07Z",
  "agent": "dynamic_testing",
  "status": "blocked",
  "warnings": [],
  "output": null,
  "error": {
    "code": "SCOPE_VIOLATION",
    "message": "Request to host other-site.example blocked by the scope gate",
    "retryable": false,
    "details": {
      "host": "other-site.example",
      "rule": "host_not_in_allowed_hosts"
    }
  },
  "metrics": {
    "duration_ms": 120,
    "llm_calls": 0,
    "input_tokens": 0,
    "output_tokens": 0
  }
}
```

## 4.5 صيغة السجل المهيكل

كائن JSON واحد في كل سطر يحمل المعرّفات دائماً ليمكن تتبع تقييم كامل عبر `correlation_id`:

```json
{"ts":"2026-11-17T09:32:05Z","level":"INFO","correlation_id":"cor_0192f230","scan_id":"scn_0192f1c9","task_id":"tsk_0192f305","agent_run_id":"run_0192f405","agent":"dynamic_testing","event":"http_request_sent","identity_id":"id_buyer_b","method":"PATCH","path":"/api/v1/orders/100","status_code":403,"duration_ms":41,"scope_gate":"allowed"}
```

# 5. الوكيل 1 - المنسّق (Orchestrator)

## 5.1 الغرض

يحوّل طلب التقييم إلى خطة مُتحقَّق منها ومرتبة بالاعتماديات، ويُبقي سير العمل كله داخل النطاق المصرّح به.

## 5.2 المسؤوليات

- التحقق من بيان النطاق وإقرار التصريح
- فحص المدخلات المطلوبة (المستودع وبيانات الاعتماد وتعليمات التشغيل)
- بناء المراحل وإسناد المهام مع الاعتماديات
- تتبع حالات المهام وإعادة المحاولة والمهل
- التوقف عند نقاط الموافقة البشرية المحددة
- جمع مخرجات الوكلاء وتوحيدها
- الإيقاف الفوري عند أي انتهاك للنطاق

## 5.3 سير العمل الداخلي

1. استلام الطلب وإسناد correlation_id
2. تشغيل فحوص النطاق الخمسة؛ أي فشل يضبط workflow_status=blocked
3. اختيار المراحل من requested_operations وassessment_mode
4. إنشاء المهام مع depends_on ووسم المراحل المستقلة بمجموعة توازٍ واحدة
5. إرسال المهام الجاهزة واستهلاك الاستجابات وتطبيق قواعد الإعادة والحلقات
6. إصدار طلبات الموافقة والانتظار ثم تشغيل خدمة التقارير الحتمية

## 5.4 الأدوات المطلوبة

- مدقق النطاق (شيفرة حتمية)
- طابور المهام ومخزن الحالة (PostgreSQL)
- مسجّل التدقيق

## 5.5 قواعد التحقق

- credential_refs تحوي هويتين على الأقل (الاختبار المزدوج يحتاجهما)
- البيئة sandbox أو staging_approved؛ ويُرفض الإنتاج
- scope_manifest_id يشير إلى بيان valid=true
- كل معرّف في depends_on موجود والرسم بلا دورات
- الخطة لا تحوي إلا الوكلاء الرسميين السبعة

## 5.6 حالات الخطأ

| الرمز | قابل للإعادة | متى |
|---|---|---|
| `SCOPE_INVALID` | لا | فشل أحد فحوص النطاق |
| `MISSING_INPUT` | لا | بيانات اعتماد أو مستودع مطلوب مفقود |
| `PLAN_CYCLE` | لا | رسم الاعتماديات فيه دورة |
| `LLM_UNAVAILABLE` | نعم | مهلة المزوّد أو حد المعدل |

## 5.7 سياسة إعادة المحاولة

الأخطاء العابرة: حتى 3 محاولات مع تراجع أُسّي وتشويش. أخطاء النطاق الحتمية لا تُعاد.

## 5.8 مثال JSON للطلب

```json
{
  "schema_version": "1.0.0",
  "correlation_id": "cor_0192f230",
  "project_id": "prj_0192f1a0",
  "engagement_id": "eng_0192f1b4",
  "scan_id": "scn_0192f1c9",
  "task_id": "tsk_0192f301",
  "agent_run_id": "run_0192f401",
  "created_at": "2026-11-17T09:30:00Z",
  "agent": "orchestrator",
  "input": {
    "project": {
      "name": "ShopLite",
      "language": "python",
      "framework_hint": "fastapi"
    },
    "target": {
      "base_url": "http://shoplite-app:8000",
      "environment": "sandbox"
    },
    "repository": {
      "source_type": "github",
      "url": "https://github.com/example-org/shoplite-api",
      "ref": "main"
    },
    "scope_manifest_id": "scm_0192f1b9",
    "assessment_mode": "full",
    "credential_refs": [
      {
        "ref": "cred_buyer_a",
        "role": "customer"
      },
      {
        "ref": "cred_buyer_b",
        "role": "customer"
      },
      {
        "ref": "cred_admin",
        "role": "admin"
      }
    ],
    "requested_operations": [
      "code_analysis",
      "recon",
      "dynamic_testing",
      "remediation"
    ]
  }
}
```

## 5.9 مثال JSON للاستجابة

```json
{
  "schema_version": "1.0.0",
  "correlation_id": "cor_0192f230",
  "project_id": "prj_0192f1a0",
  "engagement_id": "eng_0192f1b4",
  "scan_id": "scn_0192f1c9",
  "task_id": "tsk_0192f301",
  "agent_run_id": "run_0192f401",
  "created_at": "2026-11-17T09:30:04Z",
  "agent": "orchestrator",
  "status": "succeeded",
  "warnings": [],
  "error": null,
  "metrics": {
    "duration_ms": 3900,
    "llm_calls": 1,
    "input_tokens": 2100,
    "output_tokens": 640
  },
  "output": {
    "scope_validation": {
      "valid": true,
      "checks": [
        {
          "name": "manifest_well_formed",
          "passed": true,
          "detail": "scm_0192f1b9 parsed, 1 allowed host"
        },
        {
          "name": "host_in_scope",
          "passed": true,
          "detail": "shoplite-app matches allowed_hosts"
        },
        {
          "name": "no_third_party_wildcards",
          "passed": true,
          "detail": "no wildcard entries"
        },
        {
          "name": "environment_not_production",
          "passed": true,
          "detail": "environment=sandbox"
        },
        {
          "name": "authorization_attested",
          "passed": true,
          "detail": "attested by user usr_0192f19e at 2026-11-17T09:12:00Z"
        }
      ]
    },
    "stages": [
      {
        "name": "code_analysis",
        "agent": "code_intelligence",
        "depends_on": [],
        "parallel_group": "g1"
      },
      {
        "name": "recon",
        "agent": "recon",
        "depends_on": [],
        "parallel_group": "g1"
      },
      {
        "name": "research",
        "agent": "vulnerability_research",
        "depends_on": [
          "code_analysis",
          "recon"
        ]
      },
      {
        "name": "dynamic_testing",
        "agent": "dynamic_testing",
        "depends_on": [
          "research"
        ]
      },
      {
        "name": "verification",
        "agent": "verification",
        "depends_on": [
          "dynamic_testing"
        ]
      },
      {
        "name": "remediation",
        "agent": "remediation",
        "depends_on": [
          "verification"
        ],
        "requires_approval": true
      }
    ],
    "task_assignments": [
      {
        "task_id": "tsk_0192f302",
        "agent": "code_intelligence",
        "stage": "code_analysis",
        "depends_on": []
      },
      {
        "task_id": "tsk_0192f303",
        "agent": "recon",
        "stage": "recon",
        "depends_on": []
      },
      {
        "task_id": "tsk_0192f304",
        "agent": "vulnerability_research",
        "stage": "research",
        "depends_on": [
          "tsk_0192f302",
          "tsk_0192f303"
        ]
      },
      {
        "task_id": "tsk_0192f305",
        "agent": "dynamic_testing",
        "stage": "dynamic_testing",
        "depends_on": [
          "tsk_0192f304"
        ]
      },
      {
        "task_id": "tsk_0192f306",
        "agent": "verification",
        "stage": "verification",
        "depends_on": [
          "tsk_0192f305"
        ]
      },
      {
        "task_id": "tsk_0192f307",
        "agent": "remediation",
        "stage": "remediation",
        "depends_on": [
          "tsk_0192f306"
        ]
      }
    ],
    "workflow_status": "planned"
  }
}
```

## 5.10 مخطط Pydantic

```python
class ProjectInfo(Strict):
    name: str; language: Literal["python"]; framework_hint: Optional[str] = None

class TargetInfo(Strict):
    base_url: str; environment: Literal["sandbox", "staging_approved"]

class RepositoryRef(Strict):
    source_type: Literal["github", "zip"]; url: str; ref: str

class CredentialRef(Strict):
    ref: str = Field(pattern=r"^cred_[a-z0-9_]+$"); role: str

class OrchestratorInput(Strict):
    project: ProjectInfo; target: TargetInfo; repository: RepositoryRef
    scope_manifest_id: str = Field(pattern=r"^scm_[0-9a-f]{8,}$")
    assessment_mode: AssessmentMode
    credential_refs: list[CredentialRef] = Field(min_length=2)
    requested_operations: list[Literal["code_analysis", "recon", "dynamic_testing", "remediation"]]

class OrchestratorRequest(Envelope):
    agent: Literal["orchestrator"] = "orchestrator"; input: OrchestratorInput

class ScopeCheck(Strict):
    name: str; passed: bool; detail: str

class ScopeValidation(Strict):
    valid: bool; checks: list[ScopeCheck]

class Stage(Strict):
    name: str; agent: AgentName; depends_on: list[str]; parallel_group: Optional[str] = None
    requires_approval: bool = False

class TaskAssignment(Strict):
    task_id: str = Field(pattern=r"^tsk_[0-9a-f]{8,}$"); agent: AgentName; stage: str; depends_on: list[str]

class OrchestratorOutput(Strict):
    scope_validation: ScopeValidation; stages: list[Stage]
    task_assignments: list[TaskAssignment]
    workflow_status: Literal["planned", "running", "blocked", "completed", "failed"]

class OrchestratorResponse(ResponseEnvelope):
    agent: Literal["orchestrator"] = "orchestrator"; output: Optional[OrchestratorOutput] = None
```

## 5.11 مرجع الحقول (كل حقل)

**`ProjectInfo`**

| الحقل | النوع | إلزامي | القيود | المعنى |
|---|---|---|---|---|
| `name` | `str` | yes | - | اسم العنصر |
| `language` | `enum[python]` | yes | - | لغة التطبيق (python في النسخة الأولى) |
| `framework_hint` | `str or null` | no | - | إطار العمل الذي يقترحه المستخدم |

**`TargetInfo`**

| الحقل | النوع | إلزامي | القيود | المعنى |
|---|---|---|---|---|
| `base_url` | `str` | yes | - | العنوان الجذري للتطبيق قيد الاختبار |
| `environment` | `enum[sandbox, staging_approved]` | yes | - | sandbox أو staging_approved؛ ويُرفض الإنتاج |

**`RepositoryRef`**

| الحقل | النوع | إلزامي | القيود | المعنى |
|---|---|---|---|---|
| `source_type` | `enum[github, zip]` | yes | - | github أو zip؛ أو نوع مصدر الاستخبارات |
| `url` | `str` | yes | - | موقع المورد |
| `ref` | `str` | yes | - | معرّف مرجع بيانات الاعتماد |

**`CredentialRef`**

| الحقل | النوع | إلزامي | القيود | المعنى |
|---|---|---|---|---|
| `ref` | `str` | yes | `pattern=^cred_[a-z0-9_]+$` | معرّف مرجع بيانات الاعتماد |
| `role` | `str` | yes | - | دور الهوية أو بيانات الاعتماد |

**`OrchestratorInput`**

| الحقل | النوع | إلزامي | القيود | المعنى |
|---|---|---|---|---|
| `project` | `ProjectInfo` | yes | - | معلومات المشروع |
| `target` | `TargetInfo` | yes | - | التطبيق قيد الاختبار |
| `repository` | `RepositoryRef` | yes | - | مرجع المستودع |
| `scope_manifest_id` | `str` | yes | `pattern=^scm_[0-9a-f]{8,}$` | معرّف بيان النطاق المُتحقَّق منه |
| `assessment_mode` | `enum AssessmentMode` | yes | - | code_only أو dynamic_only أو full |
| `credential_refs` | `list[CredentialRef]` | yes | `min_length=2` | مراجع بيانات اعتماد الاختبار، اثنان على الأقل للاختبار المزدوج |
| `requested_operations` | `list[enum[code_analysis, recon, dynamic_testing, remediation]]` | yes | - | العمليات التي طلبها المستخدم |

**`OrchestratorRequest`**

| الحقل | النوع | إلزامي | القيود | المعنى |
|---|---|---|---|---|
| `schema_version` | `str` | yes | `pattern=^\d+\.\d+\.\d+$` | إصدار العقد بالترقيم الدلالي |
| `correlation_id` | `str` | yes | `pattern=^cor_[0-9a-f]{8,}$` | يتتبع تقييماً واحداً عبر الوكلاء والسجلات |
| `project_id` | `str` | yes | `pattern=^prj_[0-9a-f]{8,}$` | المشروع الأعلى |
| `engagement_id` | `str` | yes | `pattern=^eng_[0-9a-f]{8,}$` | التقييم المصرّح به ونطاقه |
| `scan_id` | `str` | yes | `pattern=^scn_[0-9a-f]{8,}$` | تنفيذ واحد لسير العمل |
| `task_id` | `str` | yes | `pattern=^tsk_[0-9a-f]{8,}$` | وحدة عمل واحدة للوكيل |
| `agent_run_id` | `str` | yes | `pattern=^run_[0-9a-f]{8,}$` | استدعاء واحد للوكيل؛ كل إعادة محاولة لها معرّف جديد |
| `created_at` | `str` | yes | `pattern=^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$` | طابع زمني ISO 8601 بالتوقيت العالمي |
| `agent` | `enum[orchestrator]` | no | - | اسم الوكيل الرسمي (قائمة مغلقة) |
| `input` | `OrchestratorInput` | yes | - | حمولة الطلب الخاصة بالوكيل |

**`ScopeCheck`**

| الحقل | النوع | إلزامي | القيود | المعنى |
|---|---|---|---|---|
| `name` | `str` | yes | - | اسم العنصر |
| `passed` | `bool` | yes | - | عدد الاختبارات الناجحة |
| `detail` | `str` | yes | - | شرح نتيجة الفحص |

**`ScopeValidation`**

| الحقل | النوع | إلزامي | القيود | المعنى |
|---|---|---|---|---|
| `valid` | `bool` | yes | - | صحيح إذا نجحت كل الفحوص |
| `checks` | `list[ScopeCheck]` | yes | - | فحوص التحقق الفردية من النطاق |

**`Stage`**

| الحقل | النوع | إلزامي | القيود | المعنى |
|---|---|---|---|---|
| `name` | `str` | yes | - | اسم العنصر |
| `agent` | `enum AgentName` | yes | - | اسم الوكيل الرسمي (قائمة مغلقة) |
| `depends_on` | `list[str]` | yes | - | المراحل أو معرّفات المهام التي يجب أن تنتهي أولاً |
| `parallel_group` | `str or null` | no | - | المراحل في المجموعة نفسها قد تعمل بالتوازي |
| `requires_approval` | `bool` | no | - | المرحلة تتطلب قراراً بشرياً |

**`TaskAssignment`**

| الحقل | النوع | إلزامي | القيود | المعنى |
|---|---|---|---|---|
| `task_id` | `str` | yes | `pattern=^tsk_[0-9a-f]{8,}$` | وحدة عمل واحدة للوكيل |
| `agent` | `enum AgentName` | yes | - | اسم الوكيل الرسمي (قائمة مغلقة) |
| `stage` | `str` | yes | - | اسم مرحلة سير العمل |
| `depends_on` | `list[str]` | yes | - | المراحل أو معرّفات المهام التي يجب أن تنتهي أولاً |

**`OrchestratorOutput`**

| الحقل | النوع | إلزامي | القيود | المعنى |
|---|---|---|---|---|
| `scope_validation` | `ScopeValidation` | yes | - | نتيجة التحقق من النطاق |
| `stages` | `list[Stage]` | yes | - | مراحل سير العمل المخططة |
| `task_assignments` | `list[TaskAssignment]` | yes | - | المهام المسندة للوكلاء مع اعتمادياتها |
| `workflow_status` | `enum[planned, running, blocked, completed, failed]` | yes | - | الحالة العامة لسير العمل |

**`OrchestratorResponse`**

| الحقل | النوع | إلزامي | القيود | المعنى |
|---|---|---|---|---|
| `schema_version` | `str` | yes | `pattern=^\d+\.\d+\.\d+$` | إصدار العقد بالترقيم الدلالي |
| `correlation_id` | `str` | yes | `pattern=^cor_[0-9a-f]{8,}$` | يتتبع تقييماً واحداً عبر الوكلاء والسجلات |
| `project_id` | `str` | yes | `pattern=^prj_[0-9a-f]{8,}$` | المشروع الأعلى |
| `engagement_id` | `str` | yes | `pattern=^eng_[0-9a-f]{8,}$` | التقييم المصرّح به ونطاقه |
| `scan_id` | `str` | yes | `pattern=^scn_[0-9a-f]{8,}$` | تنفيذ واحد لسير العمل |
| `task_id` | `str` | yes | `pattern=^tsk_[0-9a-f]{8,}$` | وحدة عمل واحدة للوكيل |
| `agent_run_id` | `str` | yes | `pattern=^run_[0-9a-f]{8,}$` | استدعاء واحد للوكيل؛ كل إعادة محاولة لها معرّف جديد |
| `created_at` | `str` | yes | `pattern=^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$` | طابع زمني ISO 8601 بالتوقيت العالمي |
| `status` | `enum TaskStatus` | yes | - | حالة المهمة (قائمة مغلقة) |
| `warnings` | `list[str]` | no | - | مشكلات غير قاتلة ظهرت أثناء التشغيل |
| `error` | `ErrorInfo or null` | no | - | كائن الخطأ عندما لا تكون الحالة succeeded |
| `metrics` | `Metrics` | yes | - | استهلاك الموارد في التشغيل |
| `agent` | `enum[orchestrator]` | no | - | اسم الوكيل الرسمي (قائمة مغلقة) |
| `output` | `OrchestratorOutput or null` | no | - | حمولة النتيجة الخاصة بالوكيل (null عند الفشل) |

## 5.12 كيف يستهلك الوكيل التالي هذه المخرجات

استجابة المنسّق هي الخطة. كل task_assignment يصبح مهمة في الطابور؛ ويشترك Code Intelligence وRecon في المجموعة g1 ويبدآن معاً.

# 6. الوكيل 2 - ذكاء الشيفرة (Code Intelligence)

## 6.1 الغرض

يبني الخريطة الأمنية للمستودع: المسارات والمصادقة والتفويض ونماذج البيانات ورسم الشيفرة والثوابت الأمنية المرشحة.

## 6.2 المسؤوليات

- تحديد أطر العمل والبنية
- تحليل Python بـ Tree-sitter مع تحقق متقاطع بـ ast للمزخرفات والاستدعاءات
- استخراج المسارات والمتحكمات
- إيجاد آليات المصادقة والتفويض
- ربط نماذج ORM وعمليات قاعدة البيانات
- تحليل الاعتماديات
- بناء رسم الشيفرة (NetworkX ثم الحفظ في code_nodes وcode_edges)
- اقتراح ثوابت مرشحة مع درجة ثقة

## 6.3 سير العمل الداخلي

1. سحب المستودع عند الإصدار المثبّت
2. كشف إطار العمل ونقاط الدخول
3. تحليل الملفات وتسجيل غير القابلة للتحليل كتحذيرات
4. تشغيل مستخرجات مسارات الأطر (Flask وFastAPI وDjango)
5. ربط المسارات بالحراس (مصادقة/تفويض) وبقراءات وكتابات النماذج
6. اشتقاق الثوابت، مثل مسار يحمّل نموذجاً مملوكاً دون مقارنة حقل المالك
7. التحقق من المخطط وتخزين الرسم وإرجاع المراجع

## 6.4 الأدوات المطلوبة

- Tree-sitter (قواعد Python)
- وحدة ast
- مستخرجات مسارات الأطر
- NetworkX
- Semgrep (اختياري)

## 6.5 قواعد التحقق

- commit يطابق نمط hex وموجود في النسخة المسحوبة
- كل route_id فريد داخل الفحص
- كل عنصر في applies_to_route_ids يشير إلى مسار مُرجَع
- confidence ضمن [0, 1]
- code_graph_ref يشير إلى رسم مخزّن

## 6.6 حالات الخطأ

| الرمز | قابل للإعادة | متى |
|---|---|---|
| `REPO_UNREADABLE` | لا | النسخة المسحوبة مفقودة أو تالفة |
| `NO_ROUTES_FOUND` | لا | لم يُكتشف إطار عمل مدعوم |
| `PARSE_PARTIAL` | لا | بعض الملفات غير قابلة للتحليل (تحذير لا فشل) |
| `LLM_UNAVAILABLE` | نعم | مهلة المزوّد أو حد المعدل |

## 6.7 سياسة إعادة المحاولة

التحليل حتمي ولا يُعاد. خطوة استخراج الثوابت بمساعدة النموذج وحدها تُعاد حتى 3 مرات.

## 6.8 مثال JSON للطلب

```json
{
  "schema_version": "1.0.0",
  "correlation_id": "cor_0192f230",
  "project_id": "prj_0192f1a0",
  "engagement_id": "eng_0192f1b4",
  "scan_id": "scn_0192f1c9",
  "task_id": "tsk_0192f302",
  "agent_run_id": "run_0192f402",
  "created_at": "2026-11-17T09:30:10Z",
  "agent": "code_intelligence",
  "input": {
    "repository": {
      "path_ref": "workspace://scn_0192f1c9/repo",
      "commit": "a1b2c3d4e5f6"
    },
    "source_language": "python",
    "framework_hints": [
      "fastapi",
      "sqlalchemy"
    ],
    "scan_config": {
      "max_files": 2000,
      "include_globs": [
        "app/**/*.py"
      ],
      "enable_semgrep": false
    }
  }
}
```

## 6.9 مثال JSON للاستجابة

```json
{
  "schema_version": "1.0.0",
  "correlation_id": "cor_0192f230",
  "project_id": "prj_0192f1a0",
  "engagement_id": "eng_0192f1b4",
  "scan_id": "scn_0192f1c9",
  "task_id": "tsk_0192f302",
  "agent_run_id": "run_0192f402",
  "created_at": "2026-11-17T09:31:02Z",
  "agent": "code_intelligence",
  "status": "succeeded",
  "warnings": [
    "2 files skipped: syntax errors tolerated by tree-sitter but not resolvable"
  ],
  "error": null,
  "metrics": {
    "duration_ms": 51800,
    "llm_calls": 6,
    "input_tokens": 18400,
    "output_tokens": 3100
  },
  "output": {
    "repository_structure": {
      "files_analyzed": 86,
      "frameworks": [
        "fastapi",
        "sqlalchemy"
      ],
      "entry_points": [
        "app/main.py"
      ]
    },
    "routes": [
      {
        "route_id": "rte_patch_order",
        "method": "PATCH",
        "path": "/api/v1/orders/{order_id}",
        "handler": "update_order",
        "file": "app/routes/orders.py",
        "line": 58,
        "auth_required": true,
        "authz_checks": []
      },
      {
        "route_id": "rte_get_order",
        "method": "GET",
        "path": "/api/v1/orders/{order_id}",
        "handler": "get_order",
        "file": "app/routes/orders.py",
        "line": 31,
        "auth_required": true,
        "authz_checks": [
          "order.user_id == current_user.id"
        ]
      }
    ],
    "auth_mechanisms": [
      {
        "name": "get_current_user",
        "kind": "authentication",
        "location": "app/deps.py:14",
        "description": "Decodes bearer JWT and loads the user"
      }
    ],
    "db_models": [
      {
        "name": "Order",
        "table": "orders",
        "owner_field": "user_id",
        "file": "app/models.py"
      }
    ],
    "code_graph_ref": "graph://scn_0192f1c9/code",
    "candidate_invariants": [
      {
        "invariant_id": "inv_order_owner_only",
        "statement": "An order may be read or modified only by the user referenced in orders.user_id",
        "kind": "ownership",
        "applies_to_route_ids": [
          "rte_patch_order",
          "rte_get_order"
        ],
        "source": "code",
        "confidence": 0.86
      }
    ]
  }
}
```

## 6.10 مخطط Pydantic

```python
class RepoCheckout(Strict):
    path_ref: str; commit: str = Field(pattern=r"^[0-9a-f]{7,40}$")

class ScanConfig(Strict):
    max_files: int = Field(gt=0); include_globs: list[str]; enable_semgrep: bool

class CodeIntelInput(Strict):
    repository: RepoCheckout; source_language: Literal["python"]
    framework_hints: list[str]; scan_config: ScanConfig

class CodeIntelRequest(Envelope):
    agent: Literal["code_intelligence"] = "code_intelligence"; input: CodeIntelInput

class RepoStructure(Strict):
    files_analyzed: int; frameworks: list[str]; entry_points: list[str]

class Route(Strict):
    route_id: str = Field(pattern=r"^rte_[a-z0-9_]+$"); method: str; path: str; handler: str
    file: str; line: int; auth_required: bool; authz_checks: list[str]

class SecurityMechanism(Strict):
    name: str; kind: Literal["authentication", "authorization"]; location: str; description: str

class DbModel(Strict):
    name: str; table: str; owner_field: Optional[str] = None; file: str

class CandidateInvariant(Strict):
    invariant_id: str = Field(pattern=r"^inv_[a-z0-9_]+$"); statement: str
    kind: Literal["ownership", "role_restriction", "state_transition", "authentication_required"]
    applies_to_route_ids: list[str]; source: Literal["code", "declared_policy"]
    confidence: float = Field(ge=0, le=1)

class CodeIntelOutput(Strict):
    repository_structure: RepoStructure; routes: list[Route]
    auth_mechanisms: list[SecurityMechanism]; db_models: list[DbModel]
    code_graph_ref: str; candidate_invariants: list[CandidateInvariant]

class CodeIntelResponse(ResponseEnvelope):
    agent: Literal["code_intelligence"] = "code_intelligence"; output: Optional[CodeIntelOutput] = None
```

## 6.11 مرجع الحقول (كل حقل)

**`RepoCheckout`**

| الحقل | النوع | إلزامي | القيود | المعنى |
|---|---|---|---|---|
| `path_ref` | `str` | yes | - | موقع المستودع المسحوب في مساحة العمل |
| `commit` | `str` | yes | `pattern=^[0-9a-f]{7,40}$` | إصدار Git قيد التحليل |

**`ScanConfig`**

| الحقل | النوع | إلزامي | القيود | المعنى |
|---|---|---|---|---|
| `max_files` | `int` | yes | `gt=0` | حد أعلى للملفات المحلّلة |
| `include_globs` | `list[str]` | yes | - | أنماط الملفات المراد تحليلها |
| `enable_semgrep` | `bool` | yes | - | تشغيل Semgrep كمرحلة ساكنة اختيارية |

**`CodeIntelInput`**

| الحقل | النوع | إلزامي | القيود | المعنى |
|---|---|---|---|---|
| `repository` | `RepoCheckout` | yes | - | مرجع المستودع |
| `source_language` | `enum[python]` | yes | - | لغة المصدر (python) |
| `framework_hints` | `list[str]` | yes | - | أطر العمل ذات الأولوية عند التحليل |
| `scan_config` | `ScanConfig` | yes | - | حدود التحليل وخياراته |

**`CodeIntelRequest`**

| الحقل | النوع | إلزامي | القيود | المعنى |
|---|---|---|---|---|
| `schema_version` | `str` | yes | `pattern=^\d+\.\d+\.\d+$` | إصدار العقد بالترقيم الدلالي |
| `correlation_id` | `str` | yes | `pattern=^cor_[0-9a-f]{8,}$` | يتتبع تقييماً واحداً عبر الوكلاء والسجلات |
| `project_id` | `str` | yes | `pattern=^prj_[0-9a-f]{8,}$` | المشروع الأعلى |
| `engagement_id` | `str` | yes | `pattern=^eng_[0-9a-f]{8,}$` | التقييم المصرّح به ونطاقه |
| `scan_id` | `str` | yes | `pattern=^scn_[0-9a-f]{8,}$` | تنفيذ واحد لسير العمل |
| `task_id` | `str` | yes | `pattern=^tsk_[0-9a-f]{8,}$` | وحدة عمل واحدة للوكيل |
| `agent_run_id` | `str` | yes | `pattern=^run_[0-9a-f]{8,}$` | استدعاء واحد للوكيل؛ كل إعادة محاولة لها معرّف جديد |
| `created_at` | `str` | yes | `pattern=^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$` | طابع زمني ISO 8601 بالتوقيت العالمي |
| `agent` | `enum[code_intelligence]` | no | - | اسم الوكيل الرسمي (قائمة مغلقة) |
| `input` | `CodeIntelInput` | yes | - | حمولة الطلب الخاصة بالوكيل |

**`RepoStructure`**

| الحقل | النوع | إلزامي | القيود | المعنى |
|---|---|---|---|---|
| `files_analyzed` | `int` | yes | - | عدد الملفات المحلّلة |
| `frameworks` | `list[str]` | yes | - | أطر العمل المكتشفة |
| `entry_points` | `list[str]` | yes | - | وحدات دخول التطبيق |

**`Route`**

| الحقل | النوع | إلزامي | القيود | المعنى |
|---|---|---|---|---|
| `route_id` | `str` | yes | `pattern=^rte_[a-z0-9_]+$` | معرّف مسار |
| `method` | `str` | yes | - | طريقة HTTP، أو طريقة الاختبار في الخطة |
| `path` | `str` | yes | - | قالب مسار URL |
| `handler` | `str` | yes | - | الدالة التي تخدم المسار |
| `file` | `str` | yes | - | مسار ملف المصدر |
| `line` | `int` | yes | - | رقم السطر في الملف |
| `auth_required` | `bool` | yes | - | هل يتطلب المسار أو نقطة النهاية مصادقة |
| `authz_checks` | `list[str]` | yes | - | فحوص التفويض الموجودة في المعالج (فارغ يعني لا يوجد) |

**`SecurityMechanism`**

| الحقل | النوع | إلزامي | القيود | المعنى |
|---|---|---|---|---|
| `name` | `str` | yes | - | اسم العنصر |
| `kind` | `enum[authentication, authorization]` | yes | - | تصنيف العنصر (قائمة مغلقة) |
| `location` | `str` | yes | - | file:line موضع الآلية |
| `description` | `str` | yes | - | وصف مقروء |

**`DbModel`**

| الحقل | النوع | إلزامي | القيود | المعنى |
|---|---|---|---|---|
| `name` | `str` | yes | - | اسم العنصر |
| `table` | `str` | yes | - | اسم جدول قاعدة البيانات |
| `owner_field` | `str or null` | no | - | العمود الذي يخزّن المستخدم المالك |
| `file` | `str` | yes | - | مسار ملف المصدر |

**`CandidateInvariant`**

| الحقل | النوع | إلزامي | القيود | المعنى |
|---|---|---|---|---|
| `invariant_id` | `str` | yes | `pattern=^inv_[a-z0-9_]+$` | معرّف ثابت أمني |
| `statement` | `str` | yes | - | الثابت بلغة واضحة |
| `kind` | `enum[ownership, role_restriction, state_transition, authentication_required]` | yes | - | تصنيف العنصر (قائمة مغلقة) |
| `applies_to_route_ids` | `list[str]` | yes | - | المسارات التي يقيّدها الثابت |
| `source` | `enum[code, declared_policy]` | yes | - | مصدر اكتشاف العنصر أو اشتقاقه |
| `confidence` | `float` | yes | `ge=0, le=1` | درجة من 0 إلى 1 |

**`CodeIntelOutput`**

| الحقل | النوع | إلزامي | القيود | المعنى |
|---|---|---|---|---|
| `repository_structure` | `RepoStructure` | yes | - | ملخص المستودع المحلَّل |
| `routes` | `list[Route]` | yes | - | المسارات والمتحكمات المكتشفة |
| `auth_mechanisms` | `list[SecurityMechanism]` | yes | - | آليات المصادقة والتفويض المكتشفة |
| `db_models` | `list[DbModel]` | yes | - | نماذج ORM وجداولها |
| `code_graph_ref` | `str` | yes | - | مرجع رسم الشيفرة المخزّن |
| `candidate_invariants` | `list[CandidateInvariant]` | yes | - | ثوابت أمنية مقترحة من الشيفرة |

**`CodeIntelResponse`**

| الحقل | النوع | إلزامي | القيود | المعنى |
|---|---|---|---|---|
| `schema_version` | `str` | yes | `pattern=^\d+\.\d+\.\d+$` | إصدار العقد بالترقيم الدلالي |
| `correlation_id` | `str` | yes | `pattern=^cor_[0-9a-f]{8,}$` | يتتبع تقييماً واحداً عبر الوكلاء والسجلات |
| `project_id` | `str` | yes | `pattern=^prj_[0-9a-f]{8,}$` | المشروع الأعلى |
| `engagement_id` | `str` | yes | `pattern=^eng_[0-9a-f]{8,}$` | التقييم المصرّح به ونطاقه |
| `scan_id` | `str` | yes | `pattern=^scn_[0-9a-f]{8,}$` | تنفيذ واحد لسير العمل |
| `task_id` | `str` | yes | `pattern=^tsk_[0-9a-f]{8,}$` | وحدة عمل واحدة للوكيل |
| `agent_run_id` | `str` | yes | `pattern=^run_[0-9a-f]{8,}$` | استدعاء واحد للوكيل؛ كل إعادة محاولة لها معرّف جديد |
| `created_at` | `str` | yes | `pattern=^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$` | طابع زمني ISO 8601 بالتوقيت العالمي |
| `status` | `enum TaskStatus` | yes | - | حالة المهمة (قائمة مغلقة) |
| `warnings` | `list[str]` | no | - | مشكلات غير قاتلة ظهرت أثناء التشغيل |
| `error` | `ErrorInfo or null` | no | - | كائن الخطأ عندما لا تكون الحالة succeeded |
| `metrics` | `Metrics` | yes | - | استهلاك الموارد في التشغيل |
| `agent` | `enum[code_intelligence]` | no | - | اسم الوكيل الرسمي (قائمة مغلقة) |
| `output` | `CodeIntelOutput or null` | no | - | حمولة النتيجة الخاصة بالوكيل (null عند الفشل) |

## 6.12 كيف يستهلك الوكيل التالي هذه المخرجات

يقرأ وكيل البحث المسارات التي authz_checks فيها فارغ ويطابقها مع candidate_invariants عبر applies_to_route_ids؛ وتُربط نقاط نهاية Recon بالمسارات حسب الطريقة والمسار.

# 7. الوكيل 3 - الاستطلاع (Recon)

## 7.1 الغرض

يكتشف سطح الهجوم المصرّح به ويثري نتائج التقنيات باستخبارات أمنية خارجية، ضمن النطاق حصراً.

## 7.2 المسؤوليات

- قراءة مواصفات OpenAPI وتطبيعها
- تعداد نقاط النهاية والعمليات داخل النطاق
- تحديد بصمات التقنيات من الترويسات ومسارات التوثيق والإعدادات
- الاستعلام من Tavily عن نشرات التقنيات المحددة (عند التفعيل)
- بناء خريطة سطح الهجوم
- حفظ المصدر والرابط ووقت الجلب لكل مرجع

## 7.3 سير العمل الداخلي

1. تحميل النطاق ومواصفات API
2. رفض أي نقطة خارج allowed_hosts أو داخل forbidden_paths
3. إنشاء سجلات Endpoint (المصدر openapi أو code_routes أو crawl)
4. تحديد بصمات التقنيات مع نص الدليل
5. تشغيل بحوث Tavily بحد أقصى max_queries مع إزالة التكرار ووسم trusted=false
6. إرجاع النقاط والتقنيات وattack_surface_ref وintel_refs

## 7.4 الأدوات المطلوبة

- HTTPX عبر بوابة النطاق
- محلل OpenAPI
- Tavily (غلاف langchain-tavily)
- Schemathesis (اختياري، لفحص المواصفات)

## 7.5 قواعد التحقق

- مضيف كل نقطة نهاية ضمن allowed_hosts
- لا يطابق أي مسار forbidden_paths
- intel_refs.trusted دائماً false
- retrieved_at بصيغة ISO 8601 UTC
- عدد البحوث لا يتجاوز max_queries

## 7.6 حالات الخطأ

| الرمز | قابل للإعادة | متى |
|---|---|---|
| `SPEC_INVALID` | لا | تعذّر تحليل ملف OpenAPI |
| `SCOPE_VIOLATION` | لا | محاولة استطلاع استهدفت مضيفاً خارج النطاق |
| `RESEARCH_UNAVAILABLE` | نعم | مهلة Tavily أو حد المعدل؛ يستمر الاستطلاع دون استخبارات |
| `LLM_UNAVAILABLE` | نعم | مهلة المزوّد أو حد المعدل |

## 7.7 سياسة إعادة المحاولة

فشل Tavily يُعاد حتى 3 مرات مع تراجع ثم يتحول إلى تحذير؛ ولا يفشل Recon بسبب غياب مرجع استخبارات.

## 7.8 مثال JSON للطلب

```json
{
  "schema_version": "1.0.0",
  "correlation_id": "cor_0192f230",
  "project_id": "prj_0192f1a0",
  "engagement_id": "eng_0192f1b4",
  "scan_id": "scn_0192f1c9",
  "task_id": "tsk_0192f303",
  "agent_run_id": "run_0192f403",
  "created_at": "2026-11-17T09:30:10Z",
  "agent": "recon",
  "input": {
    "scope": {
      "allowed_hosts": [
        "shoplite-app"
      ],
      "allowed_methods": [
        "GET",
        "POST",
        "PATCH",
        "DELETE"
      ],
      "forbidden_paths": [
        "/admin/danger/*"
      ]
    },
    "api_spec_ref": "workspace://scn_0192f1c9/openapi.json",
    "technology_hints": [
      "fastapi",
      "postgresql"
    ],
    "research": {
      "enabled": true,
      "max_queries": 3,
      "search_depth": "basic"
    }
  }
}
```

## 7.9 مثال JSON للاستجابة

```json
{
  "schema_version": "1.0.0",
  "correlation_id": "cor_0192f230",
  "project_id": "prj_0192f1a0",
  "engagement_id": "eng_0192f1b4",
  "scan_id": "scn_0192f1c9",
  "task_id": "tsk_0192f303",
  "agent_run_id": "run_0192f403",
  "created_at": "2026-11-17T09:30:51Z",
  "agent": "recon",
  "status": "succeeded",
  "warnings": [],
  "error": null,
  "metrics": {
    "duration_ms": 41000,
    "llm_calls": 3,
    "input_tokens": 6200,
    "output_tokens": 1500
  },
  "output": {
    "endpoints": [
      {
        "endpoint_id": "ep_patch_order",
        "method": "PATCH",
        "path": "/api/v1/orders/{order_id}",
        "path_params": [
          "order_id"
        ],
        "auth_required": true,
        "source": "openapi"
      },
      {
        "endpoint_id": "ep_get_order",
        "method": "GET",
        "path": "/api/v1/orders/{order_id}",
        "path_params": [
          "order_id"
        ],
        "auth_required": true,
        "source": "openapi"
      }
    ],
    "technologies": [
      {
        "name": "FastAPI",
        "version": null,
        "confidence": 0.9,
        "evidence": "OpenAPI document generator metadata and /docs route"
      },
      {
        "name": "PostgreSQL",
        "version": null,
        "confidence": 0.7,
        "evidence": "docker-compose service image name"
      }
    ],
    "attack_surface_ref": "graph://scn_0192f1c9/attack_surface",
    "intel_refs": [
      {
        "ref_id": "ref_0192f2b1",
        "title": "API1:2023 Broken Object Level Authorization",
        "url": "https://owasp.org/API-Security/editions/2023/en/0xa1-broken-object-level-authorization/",
        "retrieved_at": "2026-11-17T09:30:40Z",
        "source_type": "owasp",
        "relevance": 0.9,
        "trusted": false
      }
    ]
  }
}
```

## 7.10 مخطط Pydantic

```python
class ScopeSummary(Strict):
    allowed_hosts: list[str]; allowed_methods: list[str]; forbidden_paths: list[str]

class ResearchConfig(Strict):
    enabled: bool; max_queries: int = Field(ge=0); search_depth: Literal["basic", "advanced"]

class ReconInput(Strict):
    scope: ScopeSummary; api_spec_ref: Optional[str] = None
    technology_hints: list[str]; research: ResearchConfig

class ReconRequest(Envelope):
    agent: Literal["recon"] = "recon"; input: ReconInput

class Endpoint(Strict):
    endpoint_id: str = Field(pattern=r"^ep_[a-z0-9_]+$"); method: str; path: str
    path_params: list[str]; auth_required: Optional[bool] = None
    source: Literal["openapi", "code_routes", "crawl"]

class Technology(Strict):
    name: str; version: Optional[str] = None; confidence: float = Field(ge=0, le=1); evidence: str

class IntelRef(Strict):
    ref_id: str; title: str; url: str; retrieved_at: str; source_type: Literal["vendor", "nvd", "owasp", "other"]
    relevance: float = Field(ge=0, le=1); trusted: Literal[False] = False

class ReconOutput(Strict):
    endpoints: list[Endpoint]; technologies: list[Technology]; attack_surface_ref: str
    intel_refs: list[IntelRef]

class ReconResponse(ResponseEnvelope):
    agent: Literal["recon"] = "recon"; output: Optional[ReconOutput] = None
```

## 7.11 مرجع الحقول (كل حقل)

**`ScopeSummary`**

| الحقل | النوع | إلزامي | القيود | المعنى |
|---|---|---|---|---|
| `allowed_hosts` | `list[str]` | yes | - | المضيفون المسموح بالاتصال بهم |
| `allowed_methods` | `list[str]` | yes | - | طرق HTTP المسموحة في النطاق |
| `forbidden_paths` | `list[str]` | yes | - | المسارات التي يحظر اختبارها |

**`ResearchConfig`**

| الحقل | النوع | إلزامي | القيود | المعنى |
|---|---|---|---|---|
| `enabled` | `bool` | yes | - | هل البحث الخارجي مسموح |
| `max_queries` | `int` | yes | `ge=0` | حد أعلى للبحوث الخارجية |
| `search_depth` | `enum[basic, advanced]` | yes | - | عمق Tavily: basic برصيد واحد وadvanced برصيدين |

**`ReconInput`**

| الحقل | النوع | إلزامي | القيود | المعنى |
|---|---|---|---|---|
| `scope` | `ScopeSummary` | yes | - | ملخص النطاق المصرّح به |
| `api_spec_ref` | `str or null` | no | - | مرجع ملف OpenAPI في مساحة العمل |
| `technology_hints` | `list[str]` | yes | - | تقنيات يقترحها المستخدم |
| `research` | `ResearchConfig` | yes | - | إعدادات البحث الخارجي |

**`ReconRequest`**

| الحقل | النوع | إلزامي | القيود | المعنى |
|---|---|---|---|---|
| `schema_version` | `str` | yes | `pattern=^\d+\.\d+\.\d+$` | إصدار العقد بالترقيم الدلالي |
| `correlation_id` | `str` | yes | `pattern=^cor_[0-9a-f]{8,}$` | يتتبع تقييماً واحداً عبر الوكلاء والسجلات |
| `project_id` | `str` | yes | `pattern=^prj_[0-9a-f]{8,}$` | المشروع الأعلى |
| `engagement_id` | `str` | yes | `pattern=^eng_[0-9a-f]{8,}$` | التقييم المصرّح به ونطاقه |
| `scan_id` | `str` | yes | `pattern=^scn_[0-9a-f]{8,}$` | تنفيذ واحد لسير العمل |
| `task_id` | `str` | yes | `pattern=^tsk_[0-9a-f]{8,}$` | وحدة عمل واحدة للوكيل |
| `agent_run_id` | `str` | yes | `pattern=^run_[0-9a-f]{8,}$` | استدعاء واحد للوكيل؛ كل إعادة محاولة لها معرّف جديد |
| `created_at` | `str` | yes | `pattern=^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$` | طابع زمني ISO 8601 بالتوقيت العالمي |
| `agent` | `enum[recon]` | no | - | اسم الوكيل الرسمي (قائمة مغلقة) |
| `input` | `ReconInput` | yes | - | حمولة الطلب الخاصة بالوكيل |

**`Endpoint`**

| الحقل | النوع | إلزامي | القيود | المعنى |
|---|---|---|---|---|
| `endpoint_id` | `str` | yes | `pattern=^ep_[a-z0-9_]+$` | معرّف نقطة نهاية |
| `method` | `str` | yes | - | طريقة HTTP، أو طريقة الاختبار في الخطة |
| `path` | `str` | yes | - | قالب مسار URL |
| `path_params` | `list[str]` | yes | - | أسماء معاملات المسار |
| `auth_required` | `bool or null` | no | - | هل يتطلب المسار أو نقطة النهاية مصادقة |
| `source` | `enum[openapi, code_routes, crawl]` | yes | - | مصدر اكتشاف العنصر أو اشتقاقه |

**`Technology`**

| الحقل | النوع | إلزامي | القيود | المعنى |
|---|---|---|---|---|
| `name` | `str` | yes | - | اسم العنصر |
| `version` | `str or null` | no | - | نص الإصدار أو null إذا كان مجهولاً |
| `confidence` | `float` | yes | `ge=0, le=1` | درجة من 0 إلى 1 |
| `evidence` | `str` | yes | - | سبب استنتاج هذه التقنية |

**`IntelRef`**

| الحقل | النوع | إلزامي | القيود | المعنى |
|---|---|---|---|---|
| `ref_id` | `str` | yes | - | معرّف مرجع الاستخبارات |
| `title` | `str` | yes | - | عنوان موجز |
| `url` | `str` | yes | - | موقع المورد |
| `retrieved_at` | `str` | yes | - | وقت جلب المرجع |
| `source_type` | `enum[vendor, nvd, owasp, other]` | yes | - | github أو zip؛ أو نوع مصدر الاستخبارات |
| `relevance` | `float` | yes | `ge=0, le=1` | درجة الصلة من 0 إلى 1 |
| `trusted` | `enum[False]` | no | - | دائماً false: النص الخارجي غير موثوق |

**`ReconOutput`**

| الحقل | النوع | إلزامي | القيود | المعنى |
|---|---|---|---|---|
| `endpoints` | `list[Endpoint]` | yes | - | نقاط النهاية المصرّح بها المكتشفة |
| `technologies` | `list[Technology]` | yes | - | التقنيات والبصمات المكتشفة |
| `attack_surface_ref` | `str` | yes | - | مرجع رسم خريطة سطح الهجوم |
| `intel_refs` | `list[IntelRef]` | yes | - | مراجع استخبارات خارجية (غير موثوقة) |

**`ReconResponse`**

| الحقل | النوع | إلزامي | القيود | المعنى |
|---|---|---|---|---|
| `schema_version` | `str` | yes | `pattern=^\d+\.\d+\.\d+$` | إصدار العقد بالترقيم الدلالي |
| `correlation_id` | `str` | yes | `pattern=^cor_[0-9a-f]{8,}$` | يتتبع تقييماً واحداً عبر الوكلاء والسجلات |
| `project_id` | `str` | yes | `pattern=^prj_[0-9a-f]{8,}$` | المشروع الأعلى |
| `engagement_id` | `str` | yes | `pattern=^eng_[0-9a-f]{8,}$` | التقييم المصرّح به ونطاقه |
| `scan_id` | `str` | yes | `pattern=^scn_[0-9a-f]{8,}$` | تنفيذ واحد لسير العمل |
| `task_id` | `str` | yes | `pattern=^tsk_[0-9a-f]{8,}$` | وحدة عمل واحدة للوكيل |
| `agent_run_id` | `str` | yes | `pattern=^run_[0-9a-f]{8,}$` | استدعاء واحد للوكيل؛ كل إعادة محاولة لها معرّف جديد |
| `created_at` | `str` | yes | `pattern=^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$` | طابع زمني ISO 8601 بالتوقيت العالمي |
| `status` | `enum TaskStatus` | yes | - | حالة المهمة (قائمة مغلقة) |
| `warnings` | `list[str]` | no | - | مشكلات غير قاتلة ظهرت أثناء التشغيل |
| `error` | `ErrorInfo or null` | no | - | كائن الخطأ عندما لا تكون الحالة succeeded |
| `metrics` | `Metrics` | yes | - | استهلاك الموارد في التشغيل |
| `agent` | `enum[recon]` | no | - | اسم الوكيل الرسمي (قائمة مغلقة) |
| `output` | `ReconOutput or null` | no | - | حمولة النتيجة الخاصة بالوكيل (null عند الفشل) |

## 7.12 كيف يستهلك الوكيل التالي هذه المخرجات

يربط وكيل البحث نقاط النهاية بالمسارات والثوابت. وتُرفق intel_refs بالفرضيات كمراجع فقط لا كدليل.

# 8. الوكيل 4 - البحث عن الثغرات (Vulnerability Research)

## 8.1 الغرض

يحوّل الخرائط والثوابت إلى فرضيات مرتبة الأولوية وقابلة للاختبار وخطط اختبار مهيكلة، بإرشاد من مهارات Claude-BugHunter المسترجعة.

## 8.2 المسؤوليات

- ربط المسارات ونقاط النهاية والثوابت
- تحديد فئات الثغرات المنطبقة
- توليد فرضيات مع تعليل صريح
- اختيار المهارات عبر موجّه المهارات (1 إلى 3 لكل فرضية)
- اختيار طريقة الاختبار وفحوص الحالة
- ترتيب الأولويات وشرحها
- طلب سياق شيفرة إضافي عند غياب رمز

## 8.3 سير العمل الداخلي

1. مطابقة المسارات ذات authz_checks الفارغ مع ثوابت الملكية
2. إنشاء فرضية لكل عدم تطابق وتحديد الفئة من نوع الثابت
3. استرجاع المهارات (مثل hunt-idor) ضمن ميزانية الرموز
4. كتابة خطة اختبار: paired_identity عند وجود قاعدة ملكية
5. تحديد state_checks: الجدول والمفتاح والأعمدة للمقارنة
6. الترتيب حسب الأولوية 1 إلى 5 ثم التحقق والإرجاع

## 8.4 الأدوات المطلوبة

- موجّه المهارات ومحمّلها
- استعلام رسم الشيفرة
- Tavily (اختياري، مراجع فقط)

## 8.5 قواعد التحقق

- كل فرضية تشير إلى endpoint_id وinvariant_id موجودين
- الفئة إحدى الفئات الأربع للنسخة الأولى
- كل خطة اختبار تشير إلى فرضية موجودة
- خطط paired_identity تذكر هويتين على الأقل
- skill_refs أسماء موجودة في جدول skills

## 8.6 حالات الخطأ

| الرمز | قابل للإعادة | متى |
|---|---|---|
| `NO_HYPOTHESES` | لا | لا شيء للاختبار (نتيجة فارغة صحيحة مع تحذير) |
| `SKILL_NOT_FOUND` | لا | الموجّه أعاد مهارة غير معروفة |
| `CONTEXT_REQUEST_LIMIT` | لا | أكثر من طلبي سياق لفرضية |
| `LLM_UNAVAILABLE` | نعم | مهلة المزوّد أو حد المعدل |

## 8.7 سياسة إعادة المحاولة

إصلاح المخطط مرة واحدة ثم حتى 3 إعادات للأخطاء العابرة. وحلقات طلب السياق محدودة بمرتين لكل فرضية.

## 8.8 مثال JSON للطلب

```json
{
  "schema_version": "1.0.0",
  "correlation_id": "cor_0192f230",
  "project_id": "prj_0192f1a0",
  "engagement_id": "eng_0192f1b4",
  "scan_id": "scn_0192f1c9",
  "task_id": "tsk_0192f304",
  "agent_run_id": "run_0192f404",
  "created_at": "2026-11-17T09:31:10Z",
  "agent": "vulnerability_research",
  "input": {
    "code_intel_ref": "out://tsk_0192f302",
    "recon_ref": "out://tsk_0192f303",
    "invariant_ids": [
      "inv_order_owner_only"
    ],
    "skill_hits": [
      {
        "skill": "hunt-idor",
        "source_commit": "64410ed",
        "score": 0.91
      }
    ]
  }
}
```

## 8.9 مثال JSON للاستجابة

```json
{
  "schema_version": "1.0.0",
  "correlation_id": "cor_0192f230",
  "project_id": "prj_0192f1a0",
  "engagement_id": "eng_0192f1b4",
  "scan_id": "scn_0192f1c9",
  "task_id": "tsk_0192f304",
  "agent_run_id": "run_0192f404",
  "created_at": "2026-11-17T09:31:30Z",
  "agent": "vulnerability_research",
  "status": "succeeded",
  "warnings": [],
  "error": null,
  "metrics": {
    "duration_ms": 20100,
    "llm_calls": 2,
    "input_tokens": 9100,
    "output_tokens": 1800
  },
  "output": {
    "hypotheses": [
      {
        "hypothesis_id": "hyp_idor_patch_order",
        "category": "idor",
        "title": "Non-owner can modify another user's order via PATCH /orders/{order_id}",
        "rationale": "Route update_order requires authentication but its authz_checks list is empty, while invariant inv_order_owner_only states orders are owner-modifiable only.",
        "endpoint_id": "ep_patch_order",
        "invariant_id": "inv_order_owner_only",
        "priority": 1,
        "skill_refs": [
          "hunt-idor"
        ]
      }
    ],
    "test_plans": [
      {
        "test_plan_id": "tpl_idor_patch_order",
        "hypothesis_id": "hyp_idor_patch_order",
        "method": "paired_identity",
        "steps": [
          "Snapshot orders.id=100",
          "As buyer_a (owner) PATCH /api/v1/orders/100 with a baseline shipping_address",
          "Snapshot orders.id=100",
          "As buyer_b (non-owner) PATCH /api/v1/orders/100 with a distinct shipping_address",
          "Snapshot orders.id=100 and diff"
        ],
        "identities": [
          "id_buyer_a",
          "id_buyer_b"
        ],
        "expected_secure_behavior": "Request by non-owner is rejected and orders.id=100.shipping_address is unchanged",
        "state_checks": [
          {
            "table": "orders",
            "key": {
              "id": 100
            },
            "columns": [
              "shipping_address"
            ]
          }
        ]
      }
    ]
  }
}
```

## 8.10 مخطط Pydantic

```python
class SkillHit(Strict):
    skill: str; source_commit: str; score: float

class ResearchInput(Strict):
    code_intel_ref: str; recon_ref: str; invariant_ids: list[str]; skill_hits: list[SkillHit]

class ResearchRequest(Envelope):
    agent: Literal["vulnerability_research"] = "vulnerability_research"; input: ResearchInput

class StateCheck(Strict):
    table: str; key: dict; columns: list[str]

class Hypothesis(Strict):
    hypothesis_id: str = Field(pattern=r"^hyp_[a-z0-9_]+$"); category: VulnCategory; title: str
    rationale: str; endpoint_id: str; invariant_id: str; priority: int = Field(ge=1, le=5)
    skill_refs: list[str]

class TestPlan(Strict):
    test_plan_id: str = Field(pattern=r"^tpl_[a-z0-9_]+$"); hypothesis_id: str
    method: Literal["paired_identity", "single_identity", "workflow_sequence"]
    steps: list[str]; identities: list[str]; expected_secure_behavior: str
    state_checks: list[StateCheck]

class ResearchOutput(Strict):
    hypotheses: list[Hypothesis]; test_plans: list[TestPlan]

class ResearchResponse(ResponseEnvelope):
    agent: Literal["vulnerability_research"] = "vulnerability_research"; output: Optional[ResearchOutput] = None
```

## 8.11 مرجع الحقول (كل حقل)

**`SkillHit`**

| الحقل | النوع | إلزامي | القيود | المعنى |
|---|---|---|---|---|
| `skill` | `str` | yes | - | اسم مهارة Claude-BugHunter |
| `source_commit` | `str` | yes | - | إصدار مستودع المهارات المستخدم |
| `score` | `float` | yes | - | درجة الاسترجاع |

**`ResearchInput`**

| الحقل | النوع | إلزامي | القيود | المعنى |
|---|---|---|---|---|
| `code_intel_ref` | `str` | yes | - | مرجع مخرجات ذكاء الشيفرة |
| `recon_ref` | `str` | yes | - | مرجع مخرجات الاستطلاع |
| `invariant_ids` | `list[str]` | yes | - | الثوابت المراد بناء الفرضيات منها |
| `skill_hits` | `list[SkillHit]` | yes | - | المهارات المسترجعة لهذه المهمة |

**`ResearchRequest`**

| الحقل | النوع | إلزامي | القيود | المعنى |
|---|---|---|---|---|
| `schema_version` | `str` | yes | `pattern=^\d+\.\d+\.\d+$` | إصدار العقد بالترقيم الدلالي |
| `correlation_id` | `str` | yes | `pattern=^cor_[0-9a-f]{8,}$` | يتتبع تقييماً واحداً عبر الوكلاء والسجلات |
| `project_id` | `str` | yes | `pattern=^prj_[0-9a-f]{8,}$` | المشروع الأعلى |
| `engagement_id` | `str` | yes | `pattern=^eng_[0-9a-f]{8,}$` | التقييم المصرّح به ونطاقه |
| `scan_id` | `str` | yes | `pattern=^scn_[0-9a-f]{8,}$` | تنفيذ واحد لسير العمل |
| `task_id` | `str` | yes | `pattern=^tsk_[0-9a-f]{8,}$` | وحدة عمل واحدة للوكيل |
| `agent_run_id` | `str` | yes | `pattern=^run_[0-9a-f]{8,}$` | استدعاء واحد للوكيل؛ كل إعادة محاولة لها معرّف جديد |
| `created_at` | `str` | yes | `pattern=^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$` | طابع زمني ISO 8601 بالتوقيت العالمي |
| `agent` | `enum[vulnerability_research]` | no | - | اسم الوكيل الرسمي (قائمة مغلقة) |
| `input` | `ResearchInput` | yes | - | حمولة الطلب الخاصة بالوكيل |

**`StateCheck`**

| الحقل | النوع | إلزامي | القيود | المعنى |
|---|---|---|---|---|
| `table` | `str` | yes | - | اسم جدول قاعدة البيانات |
| `key` | `dict` | yes | - | قيم المفتاح الأساسي المحددة للصف |
| `columns` | `list[str]` | yes | - | الأعمدة المطلوب مقارنتها قبل وبعد |

**`Hypothesis`**

| الحقل | النوع | إلزامي | القيود | المعنى |
|---|---|---|---|---|
| `hypothesis_id` | `str` | yes | `pattern=^hyp_[a-z0-9_]+$` | معرّف فرضية |
| `category` | `enum VulnCategory` | yes | - | فئة الثغرة (قائمة مغلقة للفئات الأربع) |
| `title` | `str` | yes | - | عنوان موجز |
| `rationale` | `str` | yes | - | سبب انطباق الفرضية أو الخطورة |
| `endpoint_id` | `str` | yes | - | معرّف نقطة نهاية |
| `invariant_id` | `str` | yes | - | معرّف ثابت أمني |
| `priority` | `int` | yes | `ge=1, le=5` | من 1 (الأعلى) إلى 5 (الأدنى) |
| `skill_refs` | `list[str]` | yes | - | المهارات التي استند إليها الافتراض |

**`TestPlan`**

| الحقل | النوع | إلزامي | القيود | المعنى |
|---|---|---|---|---|
| `test_plan_id` | `str` | yes | `pattern=^tpl_[a-z0-9_]+$` | معرّف خطة اختبار |
| `hypothesis_id` | `str` | yes | - | معرّف فرضية |
| `method` | `enum[paired_identity, single_identity, workflow_sequence]` | yes | - | طريقة HTTP، أو طريقة الاختبار في الخطة |
| `steps` | `list[str]` | yes | - | خطوات الاختبار مرتبة |
| `identities` | `list[str]` | yes | - | هويات الاختبار المشاركة |
| `expected_secure_behavior` | `str` | yes | - | ما يجب أن يفعله التنفيذ الصحيح |
| `state_checks` | `list[StateCheck]` | yes | - | صفوف وأعمدة قاعدة البيانات للّقطة والمقارنة |

**`ResearchOutput`**

| الحقل | النوع | إلزامي | القيود | المعنى |
|---|---|---|---|---|
| `hypotheses` | `list[Hypothesis]` | yes | - | فرضيات ثغرات قابلة للاختبار |
| `test_plans` | `list[TestPlan]` | yes | - | خطط اختبار مهيكلة |

**`ResearchResponse`**

| الحقل | النوع | إلزامي | القيود | المعنى |
|---|---|---|---|---|
| `schema_version` | `str` | yes | `pattern=^\d+\.\d+\.\d+$` | إصدار العقد بالترقيم الدلالي |
| `correlation_id` | `str` | yes | `pattern=^cor_[0-9a-f]{8,}$` | يتتبع تقييماً واحداً عبر الوكلاء والسجلات |
| `project_id` | `str` | yes | `pattern=^prj_[0-9a-f]{8,}$` | المشروع الأعلى |
| `engagement_id` | `str` | yes | `pattern=^eng_[0-9a-f]{8,}$` | التقييم المصرّح به ونطاقه |
| `scan_id` | `str` | yes | `pattern=^scn_[0-9a-f]{8,}$` | تنفيذ واحد لسير العمل |
| `task_id` | `str` | yes | `pattern=^tsk_[0-9a-f]{8,}$` | وحدة عمل واحدة للوكيل |
| `agent_run_id` | `str` | yes | `pattern=^run_[0-9a-f]{8,}$` | استدعاء واحد للوكيل؛ كل إعادة محاولة لها معرّف جديد |
| `created_at` | `str` | yes | `pattern=^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$` | طابع زمني ISO 8601 بالتوقيت العالمي |
| `status` | `enum TaskStatus` | yes | - | حالة المهمة (قائمة مغلقة) |
| `warnings` | `list[str]` | no | - | مشكلات غير قاتلة ظهرت أثناء التشغيل |
| `error` | `ErrorInfo or null` | no | - | كائن الخطأ عندما لا تكون الحالة succeeded |
| `metrics` | `Metrics` | yes | - | استهلاك الموارد في التشغيل |
| `agent` | `enum[vulnerability_research]` | no | - | اسم الوكيل الرسمي (قائمة مغلقة) |
| `output` | `ResearchOutput or null` | no | - | حمولة النتيجة الخاصة بالوكيل (null عند الفشل) |

## 8.12 كيف يستهلك الوكيل التالي هذه المخرجات

يستلم الاختبار الديناميكي خطة اختبار واحدة مع نقطة نهايتها وهوياتها. وتحدد state_checks الصفوف المراد التقاطها؛ ويحكم التحقق لاحقاً بناءً على expected_secure_behavior.

# 9. الوكيل 5 - الاختبار الديناميكي (Dynamic Testing)

## 9.1 الغرض

ينفّذ خطة اختبار معتمدة داخل العزل بعدة هويات ويلتقط الطلبات والاستجابات وتغيّرات حالة قاعدة البيانات كأدلة.

## 9.2 المسؤوليات

- تحويل مراجع بيانات الاعتماد إلى رموز داخل العزل فقط
- تنفيذ اختبارات الهويات المزدوجة وتسلسلات الأعمال
- التقاط لقطات صفوف قاعدة البيانات قبل وبعد
- تشغيل محرك فرق الحالة
- التقاط أدلة الطلب/الاستجابة بعد الإخفاء
- الالتزام بـ max_requests وبوابة النطاق

## 9.3 سير العمل الداخلي

1. تشغيل العزل sbx_* أو الاتصال به والتأكد من سلامته
2. التقاط الصفوف المذكورة في state_checks (phase=before)
3. تنفيذ كل خطوة بالهوية المحددة عبر أداة HTTP المقيّدة بالنطاق
4. التقاط لقطة ثانية (phase=after) حول الطلب المشتبه
5. حساب الفروق لكل عمود وتخزين الدليل مع SHA-256
6. مقارنة نتائج الهويات والإرجاع

## 9.4 الأدوات المطلوبة

- عميل HTTPX المقيّد بالنطاق
- متحكم العزل (Docker)
- مساعد لقطات قاعدة البيانات
- محرك فرق الحالة
- Playwright (مؤجَّل؛ لمسارات الواجهة فقط)

## 9.5 قواعد التحقق

- كل طلب صادر يمر ببوابة النطاق (المضيف والمسار والطريقة والمعدل)
- يُنقَّح محتوى الدليل قبل التخزين (انظر evidence-hygiene)
- evidence_id موجود لكل تبادل وفرق
- معرّفات اللقطات موجودة عند snapshot_enabled=true
- الطلبات لا تتجاوز max_requests

## 9.6 حالات الخطأ

| الرمز | قابل للإعادة | متى |
|---|---|---|
| `SCOPE_VIOLATION` | لا | حُجب الطلب ببوابة النطاق؛ تصبح المهمة blocked |
| `SANDBOX_UNHEALTHY` | نعم | فشل فحص سلامة التطبيق |
| `REQUEST_BUDGET_EXCEEDED` | لا | بلوغ max_requests |
| `SNAPSHOT_FAILED` | نعم | تعذّر أخذ لقطة قاعدة البيانات |

## 9.7 سياسة إعادة المحاولة

فشل العزل واللقطات يُعاد حتى 3 مرات بعد إعادة ضبط العزل. ولا يُعاد طلب اختبار منفرد تلقائياً لأن إعادته قد تغيّر الحالة.

## 9.8 مثال JSON للطلب

```json
{
  "schema_version": "1.0.0",
  "correlation_id": "cor_0192f230",
  "project_id": "prj_0192f1a0",
  "engagement_id": "eng_0192f1b4",
  "scan_id": "scn_0192f1c9",
  "task_id": "tsk_0192f305",
  "agent_run_id": "run_0192f405",
  "created_at": "2026-11-17T09:31:35Z",
  "agent": "dynamic_testing",
  "input": {
    "test_plan": {
      "test_plan_id": "tpl_idor_patch_order",
      "hypothesis_id": "hyp_idor_patch_order",
      "method": "paired_identity",
      "steps": [
        "Snapshot orders.id=100",
        "As buyer_a (owner) PATCH /api/v1/orders/100 with a baseline shipping_address",
        "Snapshot orders.id=100",
        "As buyer_b (non-owner) PATCH /api/v1/orders/100 with a distinct shipping_address",
        "Snapshot orders.id=100 and diff"
      ],
      "identities": [
        "id_buyer_a",
        "id_buyer_b"
      ],
      "expected_secure_behavior": "Request by non-owner is rejected and orders.id=100.shipping_address is unchanged",
      "state_checks": [
        {
          "table": "orders",
          "key": {
            "id": 100
          },
          "columns": [
            "shipping_address"
          ]
        }
      ]
    },
    "endpoint": {
      "endpoint_id": "ep_patch_order",
      "method": "PATCH",
      "path": "/api/v1/orders/{order_id}",
      "path_params": [
        "order_id"
      ],
      "auth_required": true,
      "source": "openapi"
    },
    "identities": [
      {
        "identity_id": "id_buyer_a",
        "role": "customer",
        "credential_ref": "cred_buyer_a",
        "owns": {
          "order_id": 100
        }
      },
      {
        "identity_id": "id_buyer_b",
        "role": "customer",
        "credential_ref": "cred_buyer_b",
        "owns": {
          "order_id": 200
        }
      }
    ],
    "sandbox": {
      "sandbox_id": "sbx_0192f2f0",
      "base_url": "http://shoplite-app:8000",
      "snapshot_enabled": true,
      "max_requests": 200
    },
    "invariant_id": "inv_order_owner_only"
  }
}
```

## 9.9 مثال JSON للاستجابة

```json
{
  "schema_version": "1.0.0",
  "correlation_id": "cor_0192f230",
  "project_id": "prj_0192f1a0",
  "engagement_id": "eng_0192f1b4",
  "scan_id": "scn_0192f1c9",
  "task_id": "tsk_0192f305",
  "agent_run_id": "run_0192f405",
  "created_at": "2026-11-17T09:32:05Z",
  "agent": "dynamic_testing",
  "status": "succeeded",
  "warnings": [],
  "error": null,
  "metrics": {
    "duration_ms": 29800,
    "llm_calls": 0,
    "input_tokens": 0,
    "output_tokens": 0
  },
  "output": {
    "executed_cases": [
      {
        "case_id": "case_01",
        "identity_id": "id_buyer_a",
        "exchange": {
          "method": "PATCH",
          "url": "http://shoplite-app:8000/api/v1/orders/100",
          "status_code": 200,
          "response_excerpt": "{\"id\":100,\"status\":\"updated\"}",
          "evidence_id": "evd_0192f21a"
        }
      },
      {
        "case_id": "case_02",
        "identity_id": "id_buyer_b",
        "exchange": {
          "method": "PATCH",
          "url": "http://shoplite-app:8000/api/v1/orders/100",
          "status_code": 403,
          "response_excerpt": "{\"detail\":\"Forbidden\"}",
          "evidence_id": "evd_0192f21b"
        }
      }
    ],
    "identity_comparison": "Owner received 200; non-owner received 403 (response-level control appears to hold)",
    "state_diffs": [
      {
        "table": "orders",
        "key": {
          "id": 100
        },
        "column": "shipping_address",
        "before": "12 Nile St, Alexandria",
        "after": "99 Test Ave, Cairo",
        "snapshot_before_id": "snp_0192f2c1",
        "snapshot_after_id": "snp_0192f2c2",
        "evidence_id": "evd_0192f21c"
      }
    ],
    "execution_status": "completed",
    "log_ref": "log://tsk_0192f305"
  }
}
```

## 9.10 مخطط Pydantic

```python
class Identity(Strict):
    identity_id: str; role: str; credential_ref: str = Field(pattern=r"^cred_[a-z0-9_]+$"); owns: dict

class SandboxConfig(Strict):
    sandbox_id: str = Field(pattern=r"^sbx_[0-9a-f]{8,}$"); base_url: str
    snapshot_enabled: bool; max_requests: int = Field(gt=0)

class DynamicInput(Strict):
    test_plan: TestPlan; endpoint: Endpoint; identities: list[Identity]
    sandbox: SandboxConfig; invariant_id: str

class DynamicRequest(Envelope):
    agent: Literal["dynamic_testing"] = "dynamic_testing"; input: DynamicInput

class HttpExchange(Strict):
    method: str; url: str; status_code: int; response_excerpt: str; evidence_id: str = Field(pattern=r"^evd_[0-9a-f]{8,}$")

class ExecutedCase(Strict):
    case_id: str; identity_id: str; exchange: HttpExchange

class StateDiff(Strict):
    table: str; key: dict; column: str; before: object; after: object
    snapshot_before_id: str; snapshot_after_id: str; evidence_id: str

class DynamicOutput(Strict):
    executed_cases: list[ExecutedCase]; identity_comparison: str
    state_diffs: list[StateDiff]; execution_status: Literal["completed", "partial", "aborted"]
    log_ref: str

class DynamicResponse(ResponseEnvelope):
    agent: Literal["dynamic_testing"] = "dynamic_testing"; output: Optional[DynamicOutput] = None
```

## 9.11 مرجع الحقول (كل حقل)

**`Identity`**

| الحقل | النوع | إلزامي | القيود | المعنى |
|---|---|---|---|---|
| `identity_id` | `str` | yes | - | معرّف هوية الاختبار |
| `role` | `str` | yes | - | دور الهوية أو بيانات الاعتماد |
| `credential_ref` | `str` | yes | `pattern=^cred_[a-z0-9_]+$` | مرجع مبهم لبيانات اعتماد؛ لا تنتقل الأسرار في العقود |
| `owns` | `dict` | yes | - | الموارد التي تملكها الهوية |

**`SandboxConfig`**

| الحقل | النوع | إلزامي | القيود | المعنى |
|---|---|---|---|---|
| `sandbox_id` | `str` | yes | `pattern=^sbx_[0-9a-f]{8,}$` | معرّف نسخة العزل |
| `base_url` | `str` | yes | - | العنوان الجذري للتطبيق قيد الاختبار |
| `snapshot_enabled` | `bool` | yes | - | لقطات قاعدة البيانات متاحة |
| `max_requests` | `int` | yes | `gt=0` | ميزانية الطلبات داخل العزل |

**`DynamicInput`**

| الحقل | النوع | إلزامي | القيود | المعنى |
|---|---|---|---|---|
| `test_plan` | `TestPlan` | yes | - | الخطة المعتمدة للتنفيذ |
| `endpoint` | `Endpoint` | yes | - | نقطة النهاية قيد الاختبار |
| `identities` | `list[Identity]` | yes | - | هويات الاختبار المشاركة |
| `sandbox` | `SandboxConfig` | yes | - | إعدادات البيئة المعزولة |
| `invariant_id` | `str` | yes | - | معرّف ثابت أمني |

**`DynamicRequest`**

| الحقل | النوع | إلزامي | القيود | المعنى |
|---|---|---|---|---|
| `schema_version` | `str` | yes | `pattern=^\d+\.\d+\.\d+$` | إصدار العقد بالترقيم الدلالي |
| `correlation_id` | `str` | yes | `pattern=^cor_[0-9a-f]{8,}$` | يتتبع تقييماً واحداً عبر الوكلاء والسجلات |
| `project_id` | `str` | yes | `pattern=^prj_[0-9a-f]{8,}$` | المشروع الأعلى |
| `engagement_id` | `str` | yes | `pattern=^eng_[0-9a-f]{8,}$` | التقييم المصرّح به ونطاقه |
| `scan_id` | `str` | yes | `pattern=^scn_[0-9a-f]{8,}$` | تنفيذ واحد لسير العمل |
| `task_id` | `str` | yes | `pattern=^tsk_[0-9a-f]{8,}$` | وحدة عمل واحدة للوكيل |
| `agent_run_id` | `str` | yes | `pattern=^run_[0-9a-f]{8,}$` | استدعاء واحد للوكيل؛ كل إعادة محاولة لها معرّف جديد |
| `created_at` | `str` | yes | `pattern=^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$` | طابع زمني ISO 8601 بالتوقيت العالمي |
| `agent` | `enum[dynamic_testing]` | no | - | اسم الوكيل الرسمي (قائمة مغلقة) |
| `input` | `DynamicInput` | yes | - | حمولة الطلب الخاصة بالوكيل |

**`HttpExchange`**

| الحقل | النوع | إلزامي | القيود | المعنى |
|---|---|---|---|---|
| `method` | `str` | yes | - | طريقة HTTP، أو طريقة الاختبار في الخطة |
| `url` | `str` | yes | - | موقع المورد |
| `status_code` | `int` | yes | - | رمز حالة HTTP المستلم |
| `response_excerpt` | `str` | yes | - | مقتطف منقّح من متن الاستجابة |
| `evidence_id` | `str` | yes | `pattern=^evd_[0-9a-f]{8,}$` | معرّف سجل دليل غير قابل للتعديل |

**`ExecutedCase`**

| الحقل | النوع | إلزامي | القيود | المعنى |
|---|---|---|---|---|
| `case_id` | `str` | yes | - | معرّف حالة اختبار منفّذة |
| `identity_id` | `str` | yes | - | معرّف هوية الاختبار |
| `exchange` | `HttpExchange` | yes | - | ملخص طلب/استجابة HTTP الملتقط |

**`StateDiff`**

| الحقل | النوع | إلزامي | القيود | المعنى |
|---|---|---|---|---|
| `table` | `str` | yes | - | اسم جدول قاعدة البيانات |
| `key` | `dict` | yes | - | قيم المفتاح الأساسي المحددة للصف |
| `column` | `str` | yes | - | عمود قاعدة البيانات الذي تغيّر |
| `before` | `object` | yes | - | قيمة العمود قبل الطلب |
| `after` | `object` | yes | - | قيمة العمود بعد الطلب |
| `snapshot_before_id` | `str` | yes | - | اللقطة المأخوذة قبل الطلب |
| `snapshot_after_id` | `str` | yes | - | اللقطة المأخوذة بعد الطلب |
| `evidence_id` | `str` | yes | - | معرّف سجل دليل غير قابل للتعديل |

**`DynamicOutput`**

| الحقل | النوع | إلزامي | القيود | المعنى |
|---|---|---|---|---|
| `executed_cases` | `list[ExecutedCase]` | yes | - | حالات الاختبار التي نُفّذت فعلاً |
| `identity_comparison` | `str` | yes | - | مقارنة سردية لنتائج الهويات |
| `state_diffs` | `list[StateDiff]` | yes | - | فروق قاعدة البيانات الملاحظة |
| `execution_status` | `enum[completed, partial, aborted]` | yes | - | completed أو partial أو aborted |
| `log_ref` | `str` | yes | - | مرجع سجلات التنفيذ |

**`DynamicResponse`**

| الحقل | النوع | إلزامي | القيود | المعنى |
|---|---|---|---|---|
| `schema_version` | `str` | yes | `pattern=^\d+\.\d+\.\d+$` | إصدار العقد بالترقيم الدلالي |
| `correlation_id` | `str` | yes | `pattern=^cor_[0-9a-f]{8,}$` | يتتبع تقييماً واحداً عبر الوكلاء والسجلات |
| `project_id` | `str` | yes | `pattern=^prj_[0-9a-f]{8,}$` | المشروع الأعلى |
| `engagement_id` | `str` | yes | `pattern=^eng_[0-9a-f]{8,}$` | التقييم المصرّح به ونطاقه |
| `scan_id` | `str` | yes | `pattern=^scn_[0-9a-f]{8,}$` | تنفيذ واحد لسير العمل |
| `task_id` | `str` | yes | `pattern=^tsk_[0-9a-f]{8,}$` | وحدة عمل واحدة للوكيل |
| `agent_run_id` | `str` | yes | `pattern=^run_[0-9a-f]{8,}$` | استدعاء واحد للوكيل؛ كل إعادة محاولة لها معرّف جديد |
| `created_at` | `str` | yes | `pattern=^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$` | طابع زمني ISO 8601 بالتوقيت العالمي |
| `status` | `enum TaskStatus` | yes | - | حالة المهمة (قائمة مغلقة) |
| `warnings` | `list[str]` | no | - | مشكلات غير قاتلة ظهرت أثناء التشغيل |
| `error` | `ErrorInfo or null` | no | - | كائن الخطأ عندما لا تكون الحالة succeeded |
| `metrics` | `Metrics` | yes | - | استهلاك الموارد في التشغيل |
| `agent` | `enum[dynamic_testing]` | no | - | اسم الوكيل الرسمي (قائمة مغلقة) |
| `output` | `DynamicOutput or null` | no | - | حمولة النتيجة الخاصة بالوكيل (null عند الفشل) |

## 9.12 كيف يستهلك الوكيل التالي هذه المخرجات

يعيد التحقق قراءة الأدلة بالمعرّف. والفكرة الأساسية في state_diffs: case_02 أعاد 403 ومع ذلك تغيّر orders.id=100.shipping_address.

# 10. الوكيل 6 - التحقق (Verification)

## 10.1 الغرض

يقرر ما إذا كانت الفرضية ثغرة حقيقية بإعادة إنتاجها والتحقق من الأدلة وفحص الثابت. نتائج البحث ليست دليلاً أبداً.

## 10.2 المسؤوليات

- إعادة تشغيل السيناريو reproduction_runs_requested مرة
- التحقق من سلامة الأدلة (SHA-256) واكتمالها
- التأكد من انتهاك الثابت فعلاً
- التحقق من تغيّر الحالة
- حساب قابلية إعادة الإنتاج والثقة
- تحديد الخطورة وفق المنهج الموثق
- إرجاع confirmed أو unconfirmed أو rejected

## 10.3 سير العمل الداخلي

1. تحميل الفرضية والثابت والأدلة والتحقق من التجزئة
2. تطبيق بوابات الفرز: قابل لإعادة الإنتاج، ضمن النطاق، أثر حقيقي، ليس سلوكاً متوقعاً
3. إعادة الإنتاج عبر تشغيلات الاختبار الديناميكي على حالة عزل جديدة
4. تقييم invariant_violated من فرق الحالة لا من رمز الحالة وحده
5. حساب الثقة = f(نسبة إعادة الإنتاج، اكتمال الأدلة، مصدر الثابت)
6. تحديد الخطورة (الأثر × الاحتمال؛ مع متجه CVSS v3.1 اختياري) وإنشاء النتيجة

## 10.4 الأدوات المطلوبة

- إعادة تشغيل الاختبار الديناميكي
- مخزن الأدلة مع فحص التجزئة
- مهارات: triage-validation وevidence-hygiene

## 10.5 قواعد التحقق

- verdict=confirmed يتطلب severity وinvariant_violated=true وreproduced>=1
- reproduced <= runs
- rejection_reasons غير فارغ عند verdict=rejected
- كل supporting_evidence_id موجود وتجزئته صحيحة
- نتائج Tavily لا تُقبل كدليل

## 10.6 حالات الخطأ

| الرمز | قابل للإعادة | متى |
|---|---|---|
| `EVIDENCE_HASH_MISMATCH` | لا | الدليل المخزّن لم يعد يطابق SHA-256 |
| `REPRODUCTION_ENV_FAILED` | نعم | تعذّر إعادة ضبط العزل لإعادة نظيفة |
| `INSUFFICIENT_EVIDENCE` | لا | ينتج verdict=unconfirmed وليس فشلاً |
| `LLM_UNAVAILABLE` | نعم | مهلة المزوّد أو حد المعدل |

## 10.7 سياسة إعادة المحاولة

النتائج غير المؤكدة قد تعود إلى الاختبار الديناميكي بحد أقصى جولتين إضافيتين؛ بعدها يبقى الحكم unconfirmed.

## 10.8 مثال JSON للطلب

```json
{
  "schema_version": "1.0.0",
  "correlation_id": "cor_0192f230",
  "project_id": "prj_0192f1a0",
  "engagement_id": "eng_0192f1b4",
  "scan_id": "scn_0192f1c9",
  "task_id": "tsk_0192f306",
  "agent_run_id": "run_0192f406",
  "created_at": "2026-11-17T09:32:10Z",
  "agent": "verification",
  "input": {
    "hypothesis": {
      "hypothesis_id": "hyp_idor_patch_order",
      "category": "idor",
      "title": "Non-owner can modify another user's order via PATCH /orders/{order_id}",
      "rationale": "Route update_order requires authentication but its authz_checks list is empty, while invariant inv_order_owner_only states orders are owner-modifiable only.",
      "endpoint_id": "ep_patch_order",
      "invariant_id": "inv_order_owner_only",
      "priority": 1,
      "skill_refs": [
        "hunt-idor"
      ]
    },
    "dynamic_result_ref": "out://tsk_0192f305",
    "evidence_ids": [
      "evd_0192f21a",
      "evd_0192f21b",
      "evd_0192f21c"
    ],
    "invariant_statement": "An order may be read or modified only by the user referenced in orders.user_id",
    "reproduction_runs_requested": 3
  }
}
```

## 10.9 مثال JSON للاستجابة

```json
{
  "schema_version": "1.0.0",
  "correlation_id": "cor_0192f230",
  "project_id": "prj_0192f1a0",
  "engagement_id": "eng_0192f1b4",
  "scan_id": "scn_0192f1c9",
  "task_id": "tsk_0192f306",
  "agent_run_id": "run_0192f406",
  "created_at": "2026-11-17T09:32:50Z",
  "agent": "verification",
  "status": "succeeded",
  "warnings": [],
  "error": null,
  "metrics": {
    "duration_ms": 40000,
    "llm_calls": 2,
    "input_tokens": 7400,
    "output_tokens": 1200
  },
  "output": {
    "finding_id": "fnd_0192f200",
    "verdict": "confirmed",
    "reproducibility": {
      "runs": 3,
      "reproduced": 3
    },
    "confidence": 0.97,
    "severity": {
      "level": "medium",
      "rationale": "Authenticated non-owner can alter another customer's order data (integrity impact, no confidentiality impact observed); low attack complexity",
      "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:N/I:H/A:N"
    },
    "invariant_violated": true,
    "supporting_evidence_ids": [
      "evd_0192f21b",
      "evd_0192f21c"
    ],
    "rejection_reasons": []
  }
}
```

## 10.10 مخطط Pydantic

```python
class VerificationInput(Strict):
    hypothesis: Hypothesis; dynamic_result_ref: str; evidence_ids: list[str]
    invariant_statement: str; reproduction_runs_requested: int = Field(ge=1, le=10)

class VerificationRequest(Envelope):
    agent: Literal["verification"] = "verification"; input: VerificationInput

class Reproducibility(Strict):
    runs: int; reproduced: int

class Severity(Strict):
    level: SeverityLevel; rationale: str; cvss_vector: Optional[str] = None

class VerificationOutput(Strict):
    finding_id: Optional[str] = Field(default=None, pattern=r"^fnd_[0-9a-f]{8,}$")
    verdict: Verdict; reproducibility: Reproducibility; confidence: float = Field(ge=0, le=1)
    severity: Optional[Severity] = None; invariant_violated: bool
    supporting_evidence_ids: list[str]; rejection_reasons: list[str] = []

class VerificationResponse(ResponseEnvelope):
    agent: Literal["verification"] = "verification"; output: Optional[VerificationOutput] = None
```

## 10.11 مرجع الحقول (كل حقل)

**`VerificationInput`**

| الحقل | النوع | إلزامي | القيود | المعنى |
|---|---|---|---|---|
| `hypothesis` | `Hypothesis` | yes | - | الفرضية قيد التحقق |
| `dynamic_result_ref` | `str` | yes | - | مرجع مخرجات الاختبار الديناميكي |
| `evidence_ids` | `list[str]` | yes | - | سجلات الأدلة الداعمة للطلب |
| `invariant_statement` | `str` | yes | - | القاعدة المراد فحصها بلغة واضحة |
| `reproduction_runs_requested` | `int` | yes | `ge=1, le=10` | عدد تشغيلات إعادة الإنتاج المطلوبة (1 إلى 10) |

**`VerificationRequest`**

| الحقل | النوع | إلزامي | القيود | المعنى |
|---|---|---|---|---|
| `schema_version` | `str` | yes | `pattern=^\d+\.\d+\.\d+$` | إصدار العقد بالترقيم الدلالي |
| `correlation_id` | `str` | yes | `pattern=^cor_[0-9a-f]{8,}$` | يتتبع تقييماً واحداً عبر الوكلاء والسجلات |
| `project_id` | `str` | yes | `pattern=^prj_[0-9a-f]{8,}$` | المشروع الأعلى |
| `engagement_id` | `str` | yes | `pattern=^eng_[0-9a-f]{8,}$` | التقييم المصرّح به ونطاقه |
| `scan_id` | `str` | yes | `pattern=^scn_[0-9a-f]{8,}$` | تنفيذ واحد لسير العمل |
| `task_id` | `str` | yes | `pattern=^tsk_[0-9a-f]{8,}$` | وحدة عمل واحدة للوكيل |
| `agent_run_id` | `str` | yes | `pattern=^run_[0-9a-f]{8,}$` | استدعاء واحد للوكيل؛ كل إعادة محاولة لها معرّف جديد |
| `created_at` | `str` | yes | `pattern=^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$` | طابع زمني ISO 8601 بالتوقيت العالمي |
| `agent` | `enum[verification]` | no | - | اسم الوكيل الرسمي (قائمة مغلقة) |
| `input` | `VerificationInput` | yes | - | حمولة الطلب الخاصة بالوكيل |

**`Reproducibility`**

| الحقل | النوع | إلزامي | القيود | المعنى |
|---|---|---|---|---|
| `runs` | `int` | yes | - | إجمالي تشغيلات إعادة الإنتاج |
| `reproduced` | `int` | yes | - | عدد التشغيلات التي أُعيد فيها السلوك |

**`Severity`**

| الحقل | النوع | إلزامي | القيود | المعنى |
|---|---|---|---|---|
| `level` | `enum SeverityLevel` | yes | - | مستوى الخطورة |
| `rationale` | `str` | yes | - | سبب انطباق الفرضية أو الخطورة |
| `cvss_vector` | `str or null` | no | - | متجه CVSS v3.1 اختياري يدعم الخطورة |

**`VerificationOutput`**

| الحقل | النوع | إلزامي | القيود | المعنى |
|---|---|---|---|---|
| `finding_id` | `str or null` | no | `pattern=^fnd_[0-9a-f]{8,}$` | معرّف النتيجة المتحقق منها |
| `verdict` | `enum Verdict` | yes | - | confirmed أو unconfirmed أو rejected |
| `reproducibility` | `Reproducibility` | yes | - | إحصاءات إعادة الإنتاج |
| `confidence` | `float` | yes | `ge=0, le=1` | درجة من 0 إلى 1 |
| `severity` | `Severity or null` | no | - | الخطورة مع التعليل |
| `invariant_violated` | `bool` | yes | - | صحيح إذا كسر السلوك الملاحظ الثابت |
| `supporting_evidence_ids` | `list[str]` | yes | - | الأدلة الداعمة للحكم |
| `rejection_reasons` | `list[str]` | no | - | أسباب رفض النتيجة |

**`VerificationResponse`**

| الحقل | النوع | إلزامي | القيود | المعنى |
|---|---|---|---|---|
| `schema_version` | `str` | yes | `pattern=^\d+\.\d+\.\d+$` | إصدار العقد بالترقيم الدلالي |
| `correlation_id` | `str` | yes | `pattern=^cor_[0-9a-f]{8,}$` | يتتبع تقييماً واحداً عبر الوكلاء والسجلات |
| `project_id` | `str` | yes | `pattern=^prj_[0-9a-f]{8,}$` | المشروع الأعلى |
| `engagement_id` | `str` | yes | `pattern=^eng_[0-9a-f]{8,}$` | التقييم المصرّح به ونطاقه |
| `scan_id` | `str` | yes | `pattern=^scn_[0-9a-f]{8,}$` | تنفيذ واحد لسير العمل |
| `task_id` | `str` | yes | `pattern=^tsk_[0-9a-f]{8,}$` | وحدة عمل واحدة للوكيل |
| `agent_run_id` | `str` | yes | `pattern=^run_[0-9a-f]{8,}$` | استدعاء واحد للوكيل؛ كل إعادة محاولة لها معرّف جديد |
| `created_at` | `str` | yes | `pattern=^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$` | طابع زمني ISO 8601 بالتوقيت العالمي |
| `status` | `enum TaskStatus` | yes | - | حالة المهمة (قائمة مغلقة) |
| `warnings` | `list[str]` | no | - | مشكلات غير قاتلة ظهرت أثناء التشغيل |
| `error` | `ErrorInfo or null` | no | - | كائن الخطأ عندما لا تكون الحالة succeeded |
| `metrics` | `Metrics` | yes | - | استهلاك الموارد في التشغيل |
| `agent` | `enum[verification]` | no | - | اسم الوكيل الرسمي (قائمة مغلقة) |
| `output` | `VerificationOutput or null` | no | - | حمولة النتيجة الخاصة بالوكيل (null عند الفشل) |

## 10.12 كيف يستهلك الوكيل التالي هذه المخرجات

لا يقبل الإصلاح إلا verdict=confirmed. ويقرأ finding_id والأدلة الداعمة ومعرّف خطة الاختبار الأصلية ليعيد السيناريو نفسه على النسخة المُصلحة.

# 11. الوكيل 7 - الإصلاح (Remediation)

## 11.1 الغرض

يحدد السبب الجذري ويكتب إصلاحاً على فرع معزول ويثبته بالاختبارات وإعادة تشغيل الاستغلال الأصلي ويطلب موافقة بشرية.

## 11.2 المسؤوليات

- تحليل السبب الجذري من الشيفرة والأدلة
- توليد أصغر إصلاح آمن
- تطبيقه على فرع معزول فقط
- تشغيل اختبارات الوحدة والتكامل والانحدار
- إعادة تشغيل سيناريو الثغرة الأصلي
- مقارنة السلوك قبل الإصلاح وبعده
- طلب الموافقة البشرية؛ ولا دمج ولا نشر إطلاقاً

## 11.3 سير العمل الداخلي

1. قراءة source_refs والأدلة؛ والاستيضاح من ذكاء الشيفرة عند نقص السياق (حد أقصى 2)
2. صياغة الإصلاح واختبار انحدار تفويض جديد
3. إنشاء الفرع fix/aegistrace-<finding> وتطبيق الإصلاح عليه
4. تشغيل مجموعات الاختبار؛ وعند الفشل إعادة حتى max_attempts
5. إعادة تشغيل خطة الاختبار الأصلية واشتراط vulnerability_still_reproducible=false
6. إرجاع الإصلاح وأعداد الاختبارات والإعادة مع requires_human_approval=true

## 11.4 الأدوات المطلوبة

- Git (فرع معزول فقط)
- مشغّل اختبارات العزل
- الإعادة عبر الاختبار الديناميكي
- Tavily (اختياري، إرشادات الإصلاح الرسمية فقط)

## 11.5 قواعد التحقق

- حكم النتيجة confirmed
- الإصلاح لا يستهدف الفرع الافتراضي أبداً
- requires_human_approval دائماً true
- remediation_status=patch_ready_for_review يتطلب failed=0 في كل المجموعات وvulnerability_still_reproducible=false
- changed_files داخل نسخة المستودع

## 11.6 حالات الخطأ

| الرمز | قابل للإعادة | متى |
|---|---|---|
| `FINDING_NOT_CONFIRMED` | لا | النتيجة المدخلة غير مؤكدة |
| `PATCH_TESTS_FAILED` | لا | فشلت الاختبارات بعد max_attempts |
| `EXPLOIT_STILL_REPRODUCES` | لا | الإعادة تُظهر بقاء الثغرة |
| `BRANCH_PROTECTED` | لا | محاولة كتابة خارج الفرع المعزول |

## 11.7 سياسة إعادة المحاولة

حتى 3 محاولات إصلاح، كل منها يستفيد من فشل السابقة. والأخطاء العابرة تحصل على 3 إعادات بتراجع داخل المحاولة.

## 11.8 مثال JSON للطلب

```json
{
  "schema_version": "1.0.0",
  "correlation_id": "cor_0192f230",
  "project_id": "prj_0192f1a0",
  "engagement_id": "eng_0192f1b4",
  "scan_id": "scn_0192f1c9",
  "task_id": "tsk_0192f307",
  "agent_run_id": "run_0192f407",
  "created_at": "2026-11-17T09:32:55Z",
  "agent": "remediation",
  "input": {
    "finding_id": "fnd_0192f200",
    "source_refs": [
      {
        "file": "app/routes/orders.py",
        "start_line": 58,
        "end_line": 79
      }
    ],
    "verification_evidence_ids": [
      "evd_0192f21b",
      "evd_0192f21c"
    ],
    "test_environment": {
      "sandbox_id": "sbx_0192f2f0",
      "base_url": "http://shoplite-app:8000",
      "snapshot_enabled": true,
      "max_requests": 200
    },
    "original_test_plan_id": "tpl_idor_patch_order",
    "max_attempts": 3
  }
}
```

## 11.9 مثال JSON للاستجابة

```json
{
  "schema_version": "1.0.0",
  "correlation_id": "cor_0192f230",
  "project_id": "prj_0192f1a0",
  "engagement_id": "eng_0192f1b4",
  "scan_id": "scn_0192f1c9",
  "task_id": "tsk_0192f307",
  "agent_run_id": "run_0192f407",
  "created_at": "2026-11-17T09:34:20Z",
  "agent": "remediation",
  "status": "succeeded",
  "warnings": [],
  "error": null,
  "metrics": {
    "duration_ms": 85000,
    "llm_calls": 5,
    "input_tokens": 26000,
    "output_tokens": 4200
  },
  "output": {
    "root_cause": {
      "summary": "update_order loads the order by id and applies changes without comparing order.user_id to the authenticated user; the 403 is produced by a later serialization step after the write is committed",
      "files": [
        "app/routes/orders.py"
      ]
    },
    "patch": {
      "patch_id": "pat_0192f500",
      "branch": "fix/aegistrace-fnd-0192f200",
      "diff_ref": "patches/pat_0192f500.diff",
      "changed_files": [
        "app/routes/orders.py",
        "tests/test_orders_authz.py"
      ]
    },
    "tests": {
      "unit": {
        "total": 42,
        "passed": 42,
        "failed": 0
      },
      "integration": {
        "total": 18,
        "passed": 18,
        "failed": 0
      },
      "regression": {
        "total": 120,
        "passed": 120,
        "failed": 0
      }
    },
    "replay": {
      "original_scenario_replayed": true,
      "vulnerability_still_reproducible": false,
      "evidence_id": "evd_0192f2a0"
    },
    "remediation_status": "patch_ready_for_review",
    "requires_human_approval": true
  }
}
```

## 11.10 مخطط Pydantic

```python
class SourceRef(Strict):
    file: str; start_line: int; end_line: int

class RemediationInput(Strict):
    finding_id: str = Field(pattern=r"^fnd_[0-9a-f]{8,}$"); source_refs: list[SourceRef]
    verification_evidence_ids: list[str]; test_environment: SandboxConfig
    original_test_plan_id: str; max_attempts: int = Field(ge=1, le=3)

class RemediationRequest(Envelope):
    agent: Literal["remediation"] = "remediation"; input: RemediationInput

class RootCause(Strict):
    summary: str; files: list[str]

class PatchInfo(Strict):
    patch_id: str = Field(pattern=r"^pat_[0-9a-f]{8,}$"); branch: str; diff_ref: str; changed_files: list[str]

class TestCounts(Strict):
    total: int; passed: int; failed: int

class RemediationTests(Strict):
    unit: TestCounts; integration: TestCounts; regression: TestCounts

class ReplayResult(Strict):
    original_scenario_replayed: bool; vulnerability_still_reproducible: bool; evidence_id: str

class RemediationOutput(Strict):
    root_cause: RootCause; patch: Optional[PatchInfo] = None; tests: RemediationTests
    replay: ReplayResult; remediation_status: RemediationStatus
    requires_human_approval: Literal[True] = True

class RemediationResponse(ResponseEnvelope):
    agent: Literal["remediation"] = "remediation"; output: Optional[RemediationOutput] = None
```

## 11.11 مرجع الحقول (كل حقل)

**`SourceRef`**

| الحقل | النوع | إلزامي | القيود | المعنى |
|---|---|---|---|---|
| `file` | `str` | yes | - | مسار ملف المصدر |
| `start_line` | `int` | yes | - | أول سطر في الشيفرة المشار إليها |
| `end_line` | `int` | yes | - | آخر سطر في الشيفرة المشار إليها |

**`RemediationInput`**

| الحقل | النوع | إلزامي | القيود | المعنى |
|---|---|---|---|---|
| `finding_id` | `str` | yes | `pattern=^fnd_[0-9a-f]{8,}$` | معرّف النتيجة المتحقق منها |
| `source_refs` | `list[SourceRef]` | yes | - | مواضع الشيفرة المتعلقة بالنتيجة |
| `verification_evidence_ids` | `list[str]` | yes | - | الأدلة التي أثبتت الثغرة |
| `test_environment` | `SandboxConfig` | yes | - | العزل المستخدم للتحقق من الإصلاح |
| `original_test_plan_id` | `str` | yes | - | خطة الاختبار التي أثبتت الثغرة أصلاً |
| `max_attempts` | `int` | yes | `ge=1, le=3` | أقصى محاولات إصلاح (1 إلى 3) |

**`RemediationRequest`**

| الحقل | النوع | إلزامي | القيود | المعنى |
|---|---|---|---|---|
| `schema_version` | `str` | yes | `pattern=^\d+\.\d+\.\d+$` | إصدار العقد بالترقيم الدلالي |
| `correlation_id` | `str` | yes | `pattern=^cor_[0-9a-f]{8,}$` | يتتبع تقييماً واحداً عبر الوكلاء والسجلات |
| `project_id` | `str` | yes | `pattern=^prj_[0-9a-f]{8,}$` | المشروع الأعلى |
| `engagement_id` | `str` | yes | `pattern=^eng_[0-9a-f]{8,}$` | التقييم المصرّح به ونطاقه |
| `scan_id` | `str` | yes | `pattern=^scn_[0-9a-f]{8,}$` | تنفيذ واحد لسير العمل |
| `task_id` | `str` | yes | `pattern=^tsk_[0-9a-f]{8,}$` | وحدة عمل واحدة للوكيل |
| `agent_run_id` | `str` | yes | `pattern=^run_[0-9a-f]{8,}$` | استدعاء واحد للوكيل؛ كل إعادة محاولة لها معرّف جديد |
| `created_at` | `str` | yes | `pattern=^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$` | طابع زمني ISO 8601 بالتوقيت العالمي |
| `agent` | `enum[remediation]` | no | - | اسم الوكيل الرسمي (قائمة مغلقة) |
| `input` | `RemediationInput` | yes | - | حمولة الطلب الخاصة بالوكيل |

**`RootCause`**

| الحقل | النوع | إلزامي | القيود | المعنى |
|---|---|---|---|---|
| `summary` | `str` | yes | - | شرح موجز |
| `files` | `list[str]` | yes | - | الملفات المشاركة في السبب الجذري |

**`PatchInfo`**

| الحقل | النوع | إلزامي | القيود | المعنى |
|---|---|---|---|---|
| `patch_id` | `str` | yes | `pattern=^pat_[0-9a-f]{8,}$` | معرّف الإصلاح |
| `branch` | `str` | yes | - | الفرع المعزول الذي يحوي الإصلاح |
| `diff_ref` | `str` | yes | - | مرجع الفرق الموحّد المخزّن |
| `changed_files` | `list[str]` | yes | - | الملفات التي عدّلها الإصلاح |

**`TestCounts`**

| الحقل | النوع | إلزامي | القيود | المعنى |
|---|---|---|---|---|
| `total` | `int` | yes | - | إجمالي الاختبارات |
| `passed` | `int` | yes | - | عدد الاختبارات الناجحة |
| `failed` | `int` | yes | - | عدد الاختبارات الفاشلة |

**`RemediationTests`**

| الحقل | النوع | إلزامي | القيود | المعنى |
|---|---|---|---|---|
| `unit` | `TestCounts` | yes | - | أعداد اختبارات الوحدة |
| `integration` | `TestCounts` | yes | - | أعداد اختبارات التكامل |
| `regression` | `TestCounts` | yes | - | أعداد اختبارات الانحدار |

**`ReplayResult`**

| الحقل | النوع | إلزامي | القيود | المعنى |
|---|---|---|---|---|
| `original_scenario_replayed` | `bool` | yes | - | أُعيد تشغيل سيناريو الاستغلال الأصلي على النسخة المُصلحة |
| `vulnerability_still_reproducible` | `bool` | yes | - | true تعني أن الإصلاح لم يعالج الثغرة |
| `evidence_id` | `str` | yes | - | معرّف سجل دليل غير قابل للتعديل |

**`RemediationOutput`**

| الحقل | النوع | إلزامي | القيود | المعنى |
|---|---|---|---|---|
| `root_cause` | `RootCause` | yes | - | شرح سبب وجود العيب |
| `patch` | `PatchInfo or null` | no | - | بيانات الإصلاح (null إذا لم يُنتج) |
| `tests` | `RemediationTests` | yes | - | نتائج اختبارات الوحدة والتكامل والانحدار |
| `replay` | `ReplayResult` | yes | - | نتيجة إعادة تشغيل الاستغلال الأصلي |
| `remediation_status` | `enum RemediationStatus` | yes | - | نتيجة محاولة الإصلاح |
| `requires_human_approval` | `enum[True]` | no | - | دائماً true؛ لا يوجد دمج تلقائي |

**`RemediationResponse`**

| الحقل | النوع | إلزامي | القيود | المعنى |
|---|---|---|---|---|
| `schema_version` | `str` | yes | `pattern=^\d+\.\d+\.\d+$` | إصدار العقد بالترقيم الدلالي |
| `correlation_id` | `str` | yes | `pattern=^cor_[0-9a-f]{8,}$` | يتتبع تقييماً واحداً عبر الوكلاء والسجلات |
| `project_id` | `str` | yes | `pattern=^prj_[0-9a-f]{8,}$` | المشروع الأعلى |
| `engagement_id` | `str` | yes | `pattern=^eng_[0-9a-f]{8,}$` | التقييم المصرّح به ونطاقه |
| `scan_id` | `str` | yes | `pattern=^scn_[0-9a-f]{8,}$` | تنفيذ واحد لسير العمل |
| `task_id` | `str` | yes | `pattern=^tsk_[0-9a-f]{8,}$` | وحدة عمل واحدة للوكيل |
| `agent_run_id` | `str` | yes | `pattern=^run_[0-9a-f]{8,}$` | استدعاء واحد للوكيل؛ كل إعادة محاولة لها معرّف جديد |
| `created_at` | `str` | yes | `pattern=^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$` | طابع زمني ISO 8601 بالتوقيت العالمي |
| `status` | `enum TaskStatus` | yes | - | حالة المهمة (قائمة مغلقة) |
| `warnings` | `list[str]` | no | - | مشكلات غير قاتلة ظهرت أثناء التشغيل |
| `error` | `ErrorInfo or null` | no | - | كائن الخطأ عندما لا تكون الحالة succeeded |
| `metrics` | `Metrics` | yes | - | استهلاك الموارد في التشغيل |
| `agent` | `enum[remediation]` | no | - | اسم الوكيل الرسمي (قائمة مغلقة) |
| `output` | `RemediationOutput or null` | no | - | حمولة النتيجة الخاصة بالوكيل (null عند الفشل) |

## 11.12 كيف يستهلك الوكيل التالي هذه المخرجات

ينشئ المنسّق سجل موافقة ويعرض الفرق وأعداد الاختبارات وأدلة الإعادة على مراجع بشري. وحده قرار المراجع يحرك الإصلاح؛ والدمج إجراء بشري.

# 12. مثال تنفيذ كامل

يتبع الجدول حمولات الأمثلة المُتحقَّق منها (كل الأوقات بالتوقيت العالمي، 2026-11-17).

| الوقت | الوكيل | الحدث |
|---|---|---|
| 09:30:00 | المنسّق | يستلم الطلب؛ تنجح فحوص النطاق الخمسة؛ تُنشأ خطة من 6 مراحل |
| 09:30:10 | Code Intelligence وRecon | يبدآن بالتوازي (`g1`) |
| 09:30:51 | Recon | نقطتا نهاية وتقنيتان ومرجع OWASP واحد (موسوم غير موثوق) |
| 09:31:02 | Code Intelligence | 86 ملفاً؛ المسار `PATCH /orders/{order_id}` بلا فحص تفويض؛ يقترح الثابت `inv_order_owner_only` (0.86) |
| 09:31:30 | Vulnerability Research | الفرضية `hyp_idor_patch_order` (أولوية 1) مع خطة هويات مزدوجة؛ المهارة `hunt-idor` |
| 09:32:05 | Dynamic Testing | المالك يحصل على 200 وغير المالك على 403؛ **فرق الحالة يُظهر تغيّر `shipping_address`** |
| 09:32:50 | Verification | أُعيد الإنتاج 3 من 3؛ الثقة 0.97؛ الخطورة medium (أثر على السلامة)؛ النتيجة `fnd_0192f200` مؤكدة |
| 09:34:20 | Remediation | السبب الجذري: تُثبَّت الكتابة قبل إنتاج 403؛ إصلاح على `fix/aegistrace-fnd-0192f200`؛ نجاح 42/42 وحدة و18/18 تكامل و120/120 انحدار؛ ولم يعد الاستغلال يتكرر |
| لاحقاً | المراجع البشري | يوافق أو يرفض أو يطلب تغييرات. وحده الإنسان يدمج |

كل الأزمنة وأعداد الرموز في الأمثلة **قيم توضيحية** وليست قياسات.

# 13. المراجع

- Pydantic: https://docs.pydantic.dev/
- JSON Schema 2020-12: https://json-schema.org/draft/2020-12/schema
- CrewAI: https://docs.crewai.com/
- LangChain: https://docs.langchain.com/
- Groq: https://console.groq.com/docs
- Tavily Search API: https://docs.tavily.com/documentation/api-reference/endpoint/search
- Claude-BugHunter: https://github.com/elementalsouls/Claude-BugHunter
