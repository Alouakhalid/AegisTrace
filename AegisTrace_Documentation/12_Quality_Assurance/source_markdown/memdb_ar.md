# 1. نظرة عامة ومبادئ التصميم

تحدد هذه الوثيقة كيف يخزّن AegisTrace المعلومات ويتذكرها ويسترجعها: نموذج الذاكرة، وخط الاسترجاع، ومخطط PostgreSQL واستخدام pgvector، والاحتفاظ والأمان. وقد **نُفِّذ DDL في ملف `AegisTrace_Database_SQL_Appendix.sql` فعلياً على PostgreSQL 16 مع pgvector 0.6.0**، وجدول المرجع في القسم 5 مولَّد من ذلك المخطط الحي، فلا يمكن أن تنحرف الوثيقة عن الـ SQL.

| المبدأ | النتيجة |
|---|---|
| معرّفات نصية ببادئة تساوي معرّفات العقود | معرّف قاعدة البيانات ومعرّف JSON هما السلسلة نفسها؛ والنطاقات (`prj_id` و`fnd_id`...) ترفض البادئات الخاطئة |
| الأدلة غير قابلة للتعديل | `evidence` و`state_snapshots` و`audit_logs` ترفض UPDATE وDELETE بمُشغِّل |
| العلائقي أولاً | PostgreSQL هو سجل النظام؛ والمتجهات تساعد في الاسترجاع فقط |
| `jsonb` للحمولات المتغيرة فقط | بيانات النطاق وأجسام الطلبات ومدخلات/مخرجات المهام؛ وكل ما تحكمه قاعدة يكون عموداً |
| الأسرار لا تُخزَّن أبداً | المراجع فقط (`cred_*`)؛ والتنقيح يتم قبل كتابة الدليل |
| لا جدول بلا سبب | 30 جدولاً؛ كلٌّ مبرَّر في القسم 4 |

# 2. معمارية الذاكرة

![معمارية الذاكرة](../diagrams/d10_memory.svg)

## 2.1 فئات الذاكرة الخمس

| الفئة | ما تحويه | مكان التخزين | الاستمرار / الانتهاء | أسرار بنص صريح |
|---|---|---|---|---|
| A. العمل | سياق المهمة الحالية وحالة الوكيل والنتائج المؤقتة | ذاكرة العملية؛ وصف المهمة يسجّل المدخلات والمخرجات كسجل تنفيذ | تُهمل بانتهاء المهمة | أبداً |
| B. المشروع | بنية المستودع وأطر العمل والمسارات والثوابت الأمنية والنتائج السابقة | `repositories_analysis` و`code_nodes` و`code_edges` و`endpoints` و`security_invariants` و`memory_items(type=project)` | تستمر؛ وتُستبدل العناصر عند تغيّر الإصدار (`superseded_by`) | أبداً |
| C. التقييم | النطاق وتاريخ الفحوص وهويات الاختبار والنتائج والأدلة والقرارات | `scope_manifests` و`scans` و`findings` و`evidence` و`memory_items(type=engagement)` | تستمر طوال التقييم ثم سياسة الاحتفاظ | أبداً؛ الهويات `credential_ref` فقط |
| D. المعرفة | المنهجيات وأنماط الثغرات وبيانات المهارات واستراتيجيات قابلة لإعادة الاستخدام | `skills` و`skill_metadata` و`memory_items(type=knowledge)` | بإصدارات حسب إصدار المهارة | أبداً |
| E. الإصلاح | الإصلاحات السابقة والأسباب الجذرية والإصلاحات الناجحة والفاشلة ونتائج الانحدار | `patches` و`patch_tests` و`memory_items(type=remediation)` | تستمر؛ وتُحفظ الإصلاحات الفاشلة كمعرفة سلبية | أبداً |

## 2.2 مقارنة أنواع التخزين

| النوع | التعريف | المكان | قابل للتعديل؟ | مثال |
|---|---|---|---|---|
| التخزين العلائقي | حقائق مهيكلة مع قيود | جداول PostgreSQL | نعم، بالقواعد | `findings.severity` |
| الاسترجاع المتجهي | بحث تشابه على التضمينات | أعمدة `embedding` وفهرس HNSW | يُعاد بناؤه عند إعادة الفهرسة | إيجاد مقاطع مهارات عن فحوص الملكية |
| حالة العمل قصيرة الأمد | سياق مهمة واحدة | ذاكرة العملية | نعم | قائمة فرضيات جزئية |
| ذاكرة المشروع طويلة الأمد | حقائق تستحق إعادة الاستخدام عبر الفحوص | `memory_items` وجداول المشروع | تُستبدل ولا تُحرَّر | "الطلبات يملكها `user_id`" |
| سجلات التنفيذ | ما الذي عمل وكيف | `agent_tasks` و`agent_runs` و`agent_messages` والسجلات المهيكلة | إلحاق غالباً | المحاولة 2 من التشغيل X |
| الأدلة غير القابلة للتعديل | إثبات النتيجة | `evidence` (محتوى مجزّأ في مخزن الكائنات) و`state_snapshots` | أبداً | تبادل HTTP مع SHA-256 |

## 2.3 ما يجب ألا يُخزَّن نصاً صريحاً

كلمات المرور ومفاتيح API (Groq وTavily) ورموز الجلسات وJWT وملفات الارتباط وترويسات `Authorization` والبيانات الشخصية في استجابات الاختبار. تعيش بيانات الاعتماد في مدير أسرار وتنتقل فقط كمراجع `cred_*` تُحلّ داخل العزل. ويُنقَّح الدليل **قبل** كتابته (وفق إرشاد `evidence-hygiene` في Claude-BugHunter)، وتمر كتابات الذاكرة بمرشّح أنماط أسرار يرفض الكتابة بدل تخزين سر مشتبه به.

# 3. استرجاع الذاكرة

![خط استرجاع الذاكرة](../diagrams/d11_retrieval.svg)

| المرحلة | ما يحدث |
|---|---|
| 1. ترشيح البيانات الوصفية | التقييد حسب `project_id` و`memory_type` وفئة الثغرة أو المرحلة و`expires_at IS NULL OR expires_at > now()`. وهذا ما يجعل الاسترجاع خاصاً بالمشروع ويمنع التسرب بين المشاريع |
| 2أ. استرجاع الكلمات | ترتيب نص كامل `tsvector` على الكلمات المفتاحية والعناوين؛ دقيق للمعرّفات مثل `IDOR` أو `hunt-idor` |
| 2ب. تشابه المتجهات | مسافة جيب التمام على التضمينات؛ يجد صياغات قريبة تفوت الكلمات |
| 3. الدمج الهجين | دمج الرتب التبادلي: `score = sum(1 / (60 + rank_i))` عبر القائمتين، فلا حاجة لمعايرة مقياس ts_rank مع جيب التمام |
| 4. إزالة التكرار | القيد الفريد `(project_id, memory_type, content_sha256)` عند الكتابة؛ وعند القراءة تُسقَط العناصر التي ضُبط فيها `superseded_by` |
| 5. الترتيب | `final = rrf x importance x freshness` حيث `freshness = 0.5^(age_days / half_life)` |
| 6. الميزانية | تعبئة ميزانية الرموز بترتيب الرتبة والتوقف عندها وإرفاق الإسناد (اسم المهارة والإصدار ومعرّف الذاكرة) |

**القيم الافتراضية المقترحة (تُضبط بالتجربة، وليست حقائق).** أنصاف الأعمار: المشروع 90 يوماً، التقييم 30، المعرفة 365، الإصلاح 180. الميزانية: المادة المسترجعة لا تتجاوز 25 بالمئة من سياق النموذج؛ وبحد أقصى 3 مقاطع مهارات لكل فرضية. ويُحاط النص المسترجع بحدود ويُوسم كبيانات غير موثوقة في كل مطالبة.

**استرجاع المهارات** يستخدم الخط نفسه على `skill_metadata` مرشّحاً بـ `vuln_categories` و`phases`. واستعلام المثال في ملحق SQL يعمل على المخطط؛ وقد جُرّب بمتجهات اصطناعية، وهذا يثبت أنه ينفّذ ولا يقول شيئاً عن جودة الاسترجاع. ويجب قياس الجودة على مهارات حقيقية في المرحلة 1.

# 4. معمارية قاعدة البيانات

## 4.1 لماذا 30 جدولاً

قُيّمت الكيانات التسعة والعشرون المطلوبة كلها. وأُبقيت جميعها لأن لكل منها دورة حياة أو نمط وصول مختلفاً. وأُضيف جدول واحد: `finding_evidence`. فالأدلة يجب أن تكون غير قابلة للتعديل، فلا يمكن أن تحمل `finding_id` يُملأ لاحقاً عند إنشاء النتيجة؛ وجدول الربط يصل بينهما دون تعديل صف دليل أبداً.

| السؤال | القرار |
|---|---|
| `agent_tasks` مقابل `agent_runs` | منفصلان: للمهمة الواحدة عدة تشغيلات (إعادات)، والعقد يحمل `task_id` و`agent_run_id` معاً |
| `test_cases` | يخزّن **خطط الاختبار** (بادئة العقد `tpl_`)؛ والاسم من قائمة الكيانات المطلوبة |
| `skills` مقابل `skill_metadata` | منفصلان: للمهارة الواحدة مقاطع كثيرة قابلة للاسترجاع مع تضمينات |
| `repositories_analysis` | يبقى ترويسة لكل فحص تنتمي إليها عقد الشيفرة |

**إلغاء التطبيع المقصود.** `security_invariants.applies_to_node_ids` مصفوفة لا جدول ربط لأنها للقراءة غالباً وتُقرأ دائماً مع الثابت. و`agent_tasks.depends_on` مصفوفة للسبب نفسه. و`findings` تكرر `endpoint_id` و`invariant_id` من فرضيتها لتكون قائمة النتائج بلا ربط.

## 4.2 مخططات علاقات الكيانات

مولَّدة من المفاتيح الأجنبية في المخطط الحي. تُظهر النظرة العامة كيف تعتمد مجموعات الجداول الثماني بعضها على بعض؛ وتُظهر الأشكال 12a إلى 12d الجداول داخل كل مجموعة. والمفاتيح الأجنبية العابرة للأشكال مذكورة في قيود كل جدول في القسم 5.

![ERD overview](../diagrams/d12_overview.svg)

![ERD a](../diagrams/d12a_erd.svg)

![ERD b](../diagrams/d12b_erd.svg)

![ERD c](../diagrams/d12c_erd.svg)

![ERD d](../diagrams/d12d_erd.svg)

# 5. مرجع الجداول

مولَّد من قاعدة البيانات الحية: الغرض والاحتفاظ مكتوبان يدوياً؛ أمّا الأعمدة والقيود والفهارس فمن فهارس PostgreSQL. وقيم الاحتفاظ **افتراضات مقترحة** قابلة للضبط لكل نشر.

### `agent_messages`

**الغرض.** رسائل الطلب/الاستجابة المُتحقَّق منها بين المنسّق والوكلاء.

**الاحتفاظ (مقترح).** مقترح: 90 يوماً (كبيرة ويمكن إعادة بنائها من المهام).

| العمود | النوع | يقبل null | الافتراضي |
|---|---|---|---|
| `id` | `msg_id` | no | - |
| `scan_id` | `scn_id` | no | - |
| `task_id` | `tsk_id` | yes | - |
| `correlation_id` | `text` | no | - |
| `from_agent` | `text` | no | - |
| `to_agent` | `text` | no | - |
| `message_type` | `text` | no | - |
| `schema_version` | `text` | no | - |
| `payload` | `jsonb` | no | - |
| `created_at` | `timestamp with time zone` | no | `now()` |

**القيود**

- `PRIMARY KEY (id)`
- `FOREIGN KEY (scan_id) REFERENCES scans(id) ON DELETE CASCADE`
- `FOREIGN KEY (task_id) REFERENCES agent_tasks(id) ON DELETE SET NULL`
- `CHECK ((message_type = ANY (ARRAY['request'::text, 'response'::text, 'event'::text, 'approval_request'::text])))`

**الفهارس**

- `agent_messages_correlation_id_idx ON agent_messages USING btree (correlation_id)`
- `UNIQUE agent_messages_pkey ON agent_messages USING btree (id)`
- `agent_messages_scan_id_created_at_idx ON agent_messages USING btree (scan_id, created_at)`

### `agent_runs`

**الغرض.** كل استدعاء لوكيل لمهمة (الإعادات تنشئ صفوفاً).

**الاحتفاظ (مقترح).** مقترح: 180 يوماً.

| العمود | النوع | يقبل null | الافتراضي |
|---|---|---|---|
| `id` | `run_id` | no | - |
| `task_id` | `tsk_id` | no | - |
| `attempt` | `integer` | no | - |
| `status` | `text` | no | - |
| `prompt_version` | `text` | no | - |
| `model` | `text` | no | - |
| `llm_calls` | `integer` | no | `0` |
| `input_tokens` | `integer` | no | `0` |
| `output_tokens` | `integer` | no | `0` |
| `error` | `jsonb` | yes | - |
| `started_at` | `timestamp with time zone` | no | `now()` |
| `finished_at` | `timestamp with time zone` | yes | - |

**القيود**

- `UNIQUE (task_id, attempt)`
- `PRIMARY KEY (id)`
- `FOREIGN KEY (task_id) REFERENCES agent_tasks(id) ON DELETE CASCADE`
- `CHECK ((attempt >= 1))`
- `CHECK ((status = ANY (ARRAY['running'::text, 'succeeded'::text, 'failed'::text, 'cancelled'::text])))`

**الفهارس**

- `UNIQUE agent_runs_pkey ON agent_runs USING btree (id)`
- `UNIQUE agent_runs_task_id_attempt_key ON agent_runs USING btree (task_id, attempt)`
- `agent_runs_task_id_idx ON agent_runs USING btree (task_id)`

### `agent_tasks`

**الغرض.** وحدات عمل الوكلاء مع الاعتماديات والمدخلات والمخرجات.

**الاحتفاظ (مقترح).** مقترح: 180 يوماً بعد انتهاء الفحص.

| العمود | النوع | يقبل null | الافتراضي |
|---|---|---|---|
| `id` | `tsk_id` | no | - |
| `scan_id` | `scn_id` | no | - |
| `agent` | `text` | no | - |
| `stage` | `text` | no | - |
| `status` | `text` | no | `'queued'::text` |
| `depends_on` | `tsk_id[]` | no | `'{}'::tsk_id[]` |
| `input` | `jsonb` | yes | - |
| `output` | `jsonb` | yes | - |
| `error` | `jsonb` | yes | - |
| `created_at` | `timestamp with time zone` | no | `now()` |
| `finished_at` | `timestamp with time zone` | yes | - |

**القيود**

- `UNIQUE (scan_id, stage)`
- `PRIMARY KEY (id)`
- `FOREIGN KEY (scan_id) REFERENCES scans(id) ON DELETE CASCADE`
- `CHECK ((agent = ANY (ARRAY['orchestrator'::text, 'code_intelligence'::text, 'recon'::text, 'vulnerability_research'::text, 'dynamic_testing'::text, 'verification'::text, 'remediation'::text])))`
- `CHECK ((status = ANY (ARRAY['queued'::text, 'running'::text, 'succeeded'::text, 'failed'::text, 'blocked'::text, 'needs_input'::text, 'cancelled'::text])))`

**الفهارس**

- `UNIQUE agent_tasks_pkey ON agent_tasks USING btree (id)`
- `UNIQUE agent_tasks_scan_id_stage_key ON agent_tasks USING btree (scan_id, stage)`
- `agent_tasks_scan_id_status_idx ON agent_tasks USING btree (scan_id, status)`

### `approvals`

**الغرض.** القرارات البشرية على الإصلاحات؛ البوابة الإلزامية.

**الاحتفاظ (مقترح).** تُحفظ للتدقيق.

| العمود | النوع | يقبل null | الافتراضي |
|---|---|---|---|
| `id` | `apr_id` | no | - |
| `patch_id` | `pat_id` | no | - |
| `requested_at` | `timestamp with time zone` | no | `now()` |
| `decision` | `text` | no | `'pending'::text` |
| `decided_by` | `usr_id` | yes | - |
| `decided_at` | `timestamp with time zone` | yes | - |
| `comment` | `text` | yes | - |

**القيود**

- `PRIMARY KEY (id)`
- `FOREIGN KEY (decided_by) REFERENCES users(id)`
- `FOREIGN KEY (patch_id) REFERENCES patches(id) ON DELETE CASCADE`
- `CHECK ((((decision = 'pending'::text) AND (decided_by IS NULL) AND (decided_at IS NULL)) OR ((decision <> 'pending'::text) AND (decided_by IS NOT NULL) AND (decided_at IS NOT NULL))))`
- `CHECK ((decision = ANY (ARRAY['pending'::text, 'approved'::text, 'rejected'::text, 'changes_requested'::text])))`

**الفهارس**

- `approvals_decision_idx ON approvals USING btree (decision) WHERE (decision = 'pending'::text)`
- `UNIQUE approvals_pkey ON approvals USING btree (id)`

### `audit_logs`

**الغرض.** سجل للإلحاق فقط للإجراءات بما فيها المحجوبة.

**الاحتفاظ (مقترح).** مقترح: سنتان؛ لا يُعدَّل.

| العمود | النوع | يقبل null | الافتراضي |
|---|---|---|---|
| `id` | `bigint` | no | - |
| `ts` | `timestamp with time zone` | no | `now()` |
| `actor_type` | `text` | no | - |
| `actor_id` | `text` | no | - |
| `action` | `text` | no | - |
| `scan_id` | `scn_id` | yes | - |
| `resource_type` | `text` | yes | - |
| `resource_id` | `text` | yes | - |
| `allowed` | `boolean` | no | - |
| `details` | `jsonb` | no | `'{}'::jsonb` |

**القيود**

- `PRIMARY KEY (id)`
- `FOREIGN KEY (scan_id) REFERENCES scans(id)`
- `CHECK ((actor_type = ANY (ARRAY['user'::text, 'agent'::text, 'system'::text])))`

**الفهارس**

- `UNIQUE audit_logs_pkey ON audit_logs USING btree (id)`
- `audit_logs_scan_id_ts_idx ON audit_logs USING btree (scan_id, ts)`
- `audit_logs_ts_idx ON audit_logs USING btree (ts) WHERE (allowed = false)`

### `code_edges`

**الغرض.** حواف رسم الشيفرة (استدعاءات وحراسة وقراءة وكتابة وتدفق بيانات).

**الاحتفاظ (مقترح).** كما في code_nodes.

| العمود | النوع | يقبل null | الافتراضي |
|---|---|---|---|
| `id` | `bigint` | no | - |
| `analysis_id` | `ran_id` | no | - |
| `src` | `bigint` | no | - |
| `dst` | `bigint` | no | - |
| `kind` | `text` | no | - |
| `props` | `jsonb` | no | `'{}'::jsonb` |

**القيود**

- `PRIMARY KEY (id)`
- `FOREIGN KEY (analysis_id) REFERENCES repositories_analysis(id) ON DELETE CASCADE`
- `FOREIGN KEY (dst) REFERENCES code_nodes(id) ON DELETE CASCADE`
- `FOREIGN KEY (src) REFERENCES code_nodes(id) ON DELETE CASCADE`
- `CHECK ((kind = ANY (ARRAY['calls'::text, 'imports'::text, 'handles_route'::text, 'guards'::text, 'reads'::text, 'writes'::text, 'data_flow'::text, 'depends_on'::text])))`

**الفهارس**

- `code_edges_analysis_id_dst_idx ON code_edges USING btree (analysis_id, dst)`
- `code_edges_analysis_id_src_idx ON code_edges USING btree (analysis_id, src)`
- `UNIQUE code_edges_pkey ON code_edges USING btree (id)`

### `code_nodes`

**الغرض.** عقد رسم الشيفرة (ملفات ودوال ومسارات وفحوص ونماذج).

**الاحتفاظ (مقترح).** مقترح: 90 يوماً؛ ويمكن اشتقاقها من الإصدار.

| العمود | النوع | يقبل null | الافتراضي |
|---|---|---|---|
| `id` | `bigint` | no | - |
| `analysis_id` | `ran_id` | no | - |
| `kind` | `text` | no | - |
| `name` | `text` | no | - |
| `file` | `text` | yes | - |
| `line` | `integer` | yes | - |
| `props` | `jsonb` | no | `'{}'::jsonb` |

**القيود**

- `PRIMARY KEY (id)`
- `FOREIGN KEY (analysis_id) REFERENCES repositories_analysis(id) ON DELETE CASCADE`
- `CHECK ((kind = ANY (ARRAY['file'::text, 'module'::text, 'function'::text, 'class'::text, 'route'::text, 'auth_check'::text, 'authz_check'::text, 'db_model'::text, 'db_operation'::text, 'dependency'::text])))`

**الفهارس**

- `code_nodes_analysis_id_file_idx ON code_nodes USING btree (analysis_id, file)`
- `code_nodes_analysis_id_kind_idx ON code_nodes USING btree (analysis_id, kind)`
- `UNIQUE code_nodes_pkey ON code_nodes USING btree (id)`

### `endpoints`

**الغرض.** نقاط النهاية المصرّح بها المكتشفة، مربوطة بعقد الشيفرة.

**الاحتفاظ (مقترح).** مع الفحص.

| العمود | النوع | يقبل null | الافتراضي |
|---|---|---|---|
| `id` | `ep_id` | no | - |
| `scan_id` | `scn_id` | no | - |
| `method` | `text` | no | - |
| `path` | `text` | no | - |
| `path_params` | `text[]` | no | `'{}'::text[]` |
| `auth_required` | `boolean` | yes | - |
| `source` | `text` | no | - |
| `code_node_id` | `bigint` | yes | - |

**القيود**

- `UNIQUE (scan_id, method, path)`
- `PRIMARY KEY (id)`
- `FOREIGN KEY (code_node_id) REFERENCES code_nodes(id) ON DELETE SET NULL`
- `FOREIGN KEY (scan_id) REFERENCES scans(id) ON DELETE CASCADE`
- `CHECK ((source = ANY (ARRAY['openapi'::text, 'code_routes'::text, 'crawl'::text])))`

**الفهارس**

- `UNIQUE endpoints_pkey ON endpoints USING btree (id)`
- `endpoints_scan_id_idx ON endpoints USING btree (scan_id)`
- `UNIQUE endpoints_scan_id_method_path_key ON endpoints USING btree (scan_id, method, path)`

### `engagements`

**الغرض.** تقييم مصرّح واحد مع الإقرار والنمط والبيئة.

**الاحتفاظ (مقترح).** يُحفظ لمدة التدقيق.

| العمود | النوع | يقبل null | الافتراضي |
|---|---|---|---|
| `id` | `eng_id` | no | - |
| `project_id` | `prj_id` | no | - |
| `name` | `text` | no | - |
| `assessment_mode` | `text` | no | - |
| `environment` | `text` | no | - |
| `status` | `text` | no | `'draft'::text` |
| `attested_by` | `usr_id` | yes | - |
| `attested_at` | `timestamp with time zone` | yes | - |
| `starts_at` | `timestamp with time zone` | yes | - |
| `ends_at` | `timestamp with time zone` | yes | - |
| `created_at` | `timestamp with time zone` | no | `now()` |

**القيود**

- `PRIMARY KEY (id)`
- `FOREIGN KEY (attested_by) REFERENCES users(id)`
- `FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE`
- `CHECK ((assessment_mode = ANY (ARRAY['code_only'::text, 'dynamic_only'::text, 'full'::text])))`
- `CHECK (((status = 'draft'::text) OR ((attested_by IS NOT NULL) AND (attested_at IS NOT NULL))))`
- `CHECK (((ends_at IS NULL) OR (starts_at IS NULL) OR (ends_at > starts_at)))`
- `CHECK ((environment = ANY (ARRAY['sandbox'::text, 'staging_approved'::text])))`
- `CHECK ((status = ANY (ARRAY['draft'::text, 'active'::text, 'closed'::text])))`

**الفهارس**

- `UNIQUE engagements_pkey ON engagements USING btree (id)`
- `engagements_project_id_idx ON engagements USING btree (project_id)`

### `evidence`

**الغرض.** سجلات أدلة غير قابلة للتعديل تشير إلى محتوى مجزّأ في مخزن الكائنات.

**الاحتفاظ (مقترح).** مقترح: سنة بعد إغلاق التقييم؛ والحجز القانوني يتقدم.

| العمود | النوع | يقبل null | الافتراضي |
|---|---|---|---|
| `id` | `evd_id` | no | - |
| `scan_id` | `scn_id` | no | - |
| `kind` | `text` | no | - |
| `content_ref` | `text` | no | - |
| `content_sha256` | `text` | no | - |
| `redacted` | `boolean` | no | `true` |
| `created_by_run` | `run_id` | yes | - |
| `created_at` | `timestamp with time zone` | no | `now()` |

**القيود**

- `PRIMARY KEY (id)`
- `FOREIGN KEY (created_by_run) REFERENCES agent_runs(id)`
- `FOREIGN KEY (scan_id) REFERENCES scans(id)`
- `CHECK ((content_sha256 ~ '^[0-9a-f]{64}$'::text))`
- `CHECK ((kind = ANY (ARRAY['http_exchange'::text, 'state_snapshot'::text, 'state_diff'::text, 'log'::text, 'patch_replay'::text, 'screenshot'::text])))`

**الفهارس**

- `UNIQUE evidence_pkey ON evidence USING btree (id)`
- `evidence_scan_id_kind_idx ON evidence USING btree (scan_id, kind)`

### `finding_evidence`

**الغرض.** جدول ربط يصل النتائج بالأدلة دون تعديل صفوف الأدلة.

**الاحتفاظ (مقترح).** مع النتيجة.

| العمود | النوع | يقبل null | الافتراضي |
|---|---|---|---|
| `finding_id` | `fnd_id` | no | - |
| `evidence_id` | `evd_id` | no | - |
| `role` | `text` | no | - |

**القيود**

- `PRIMARY KEY (finding_id, evidence_id)`
- `FOREIGN KEY (evidence_id) REFERENCES evidence(id)`
- `FOREIGN KEY (finding_id) REFERENCES findings(id) ON DELETE CASCADE`
- `CHECK ((role = ANY (ARRAY['request'::text, 'response'::text, 'state_diff'::text, 'replay'::text, 'supporting'::text])))`

**الفهارس**

- `finding_evidence_evidence_id_idx ON finding_evidence USING btree (evidence_id)`
- `UNIQUE finding_evidence_pkey ON finding_evidence USING btree (finding_id, evidence_id)`

### `findings`

**الغرض.** نتائج متحقق منها مع الحكم والخطورة وقابلية الإعادة والحالة.

**الاحتفاظ (مقترح).** تُحفظ؛ فهي المنتج.

| العمود | النوع | يقبل null | الافتراضي |
|---|---|---|---|
| `id` | `fnd_id` | no | - |
| `scan_id` | `scn_id` | no | - |
| `hypothesis_id` | `hyp_id` | no | - |
| `endpoint_id` | `ep_id` | no | - |
| `invariant_id` | `inv_id` | no | - |
| `verdict` | `text` | no | - |
| `confidence` | `numeric(3,2)` | no | - |
| `severity` | `text` | yes | - |
| `cvss_vector` | `text` | yes | - |
| `runs` | `integer` | no | - |
| `reproduced` | `integer` | no | - |
| `invariant_violated` | `boolean` | no | - |
| `status` | `text` | no | `'open'::text` |
| `rejection_reasons` | `text[]` | no | `'{}'::text[]` |
| `verified_by_run` | `run_id` | yes | - |
| `created_at` | `timestamp with time zone` | no | `now()` |

**القيود**

- `PRIMARY KEY (id)`
- `FOREIGN KEY (endpoint_id) REFERENCES endpoints(id)`
- `FOREIGN KEY (hypothesis_id) REFERENCES vulnerability_hypotheses(id)`
- `FOREIGN KEY (invariant_id) REFERENCES security_invariants(id)`
- `FOREIGN KEY (scan_id) REFERENCES scans(id) ON DELETE CASCADE`
- `FOREIGN KEY (verified_by_run) REFERENCES agent_runs(id)`
- `CHECK (((reproduced >= 0) AND (reproduced <= runs)))`
- `CHECK (((verdict <> 'confirmed'::text) OR ((severity IS NOT NULL) AND invariant_violated AND (reproduced >= 1))))`
- `CHECK (((confidence >= (0)::numeric) AND (confidence <= (1)::numeric)))`
- `CHECK ((runs >= 1))`
- `CHECK ((severity = ANY (ARRAY['informational'::text, 'low'::text, 'medium'::text, 'high'::text, 'critical'::text])))`
- `CHECK ((status = ANY (ARRAY['open'::text, 'patch_proposed'::text, 'fixed'::text, 'accepted_risk'::text, 'wont_fix'::text])))`
- `CHECK ((verdict = ANY (ARRAY['confirmed'::text, 'unconfirmed'::text, 'rejected'::text])))`

**الفهارس**

- `UNIQUE findings_pkey ON findings USING btree (id)`
- `findings_scan_id_severity_idx ON findings USING btree (scan_id, severity)`
- `findings_status_idx ON findings USING btree (status) WHERE (status = 'open'::text)`

### `memory_items`

**الغرض.** ذاكرة طويلة الأمد مع تضمينات وأهمية وانتهاء وإزالة تكرار.

**الاحتفاظ (مقترح).** حسب النوع: انظر القسم 2؛ والانتهاء عبر expires_at.

| العمود | النوع | يقبل null | الافتراضي |
|---|---|---|---|
| `id` | `mem_id` | no | - |
| `project_id` | `prj_id` | no | - |
| `scan_id` | `scn_id` | yes | - |
| `memory_type` | `text` | no | - |
| `key` | `text` | no | - |
| `content` | `text` | no | - |
| `metadata` | `jsonb` | no | `'{}'::jsonb` |
| `content_sha256` | `text` | no | - |
| `importance` | `real` | no | `0.5` |
| `embedding` | `vector(384)` | yes | - |
| `superseded_by` | `mem_id` | yes | - |
| `expires_at` | `timestamp with time zone` | yes | - |
| `created_at` | `timestamp with time zone` | no | `now()` |

**القيود**

- `UNIQUE (project_id, memory_type, content_sha256)`
- `PRIMARY KEY (id)`
- `FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE`
- `FOREIGN KEY (scan_id) REFERENCES scans(id) ON DELETE SET NULL`
- `FOREIGN KEY (superseded_by) REFERENCES memory_items(id)`
- `CHECK (((importance >= (0)::double precision) AND (importance <= (1)::double precision)))`
- `CHECK ((memory_type = ANY (ARRAY['project'::text, 'engagement'::text, 'knowledge'::text, 'remediation'::text])))`

**الفهارس**

- `memory_items_embedding_idx ON memory_items USING hnsw (embedding vector_cosine_ops)`
- `memory_items_expires_at_idx ON memory_items USING btree (expires_at) WHERE (expires_at IS NOT NULL)`
- `UNIQUE memory_items_pkey ON memory_items USING btree (id)`
- `UNIQUE memory_items_project_id_memory_type_content_sha256_key ON memory_items USING btree (project_id, memory_type, content_sha256)`
- `memory_items_project_id_memory_type_idx ON memory_items USING btree (project_id, memory_type)`

### `patch_tests`

**الغرض.** نتائج الوحدة والتكامل والانحدار والإعادة لكل إصلاح.

**الاحتفاظ (مقترح).** مع الإصلاح.

| العمود | النوع | يقبل null | الافتراضي |
|---|---|---|---|
| `id` | `ptt_id` | no | - |
| `patch_id` | `pat_id` | no | - |
| `suite` | `text` | no | - |
| `total` | `integer` | no | - |
| `passed` | `integer` | no | - |
| `failed` | `integer` | no | - |
| `evidence_id` | `evd_id` | yes | - |
| `started_at` | `timestamp with time zone` | no | `now()` |
| `finished_at` | `timestamp with time zone` | yes | - |

**القيود**

- `PRIMARY KEY (id)`
- `FOREIGN KEY (evidence_id) REFERENCES evidence(id)`
- `FOREIGN KEY (patch_id) REFERENCES patches(id) ON DELETE CASCADE`
- `CHECK (((passed + failed) <= total))`
- `CHECK ((suite = ANY (ARRAY['unit'::text, 'integration'::text, 'regression'::text, 'replay'::text])))`

**الفهارس**

- `UNIQUE patch_tests_pkey ON patch_tests USING btree (id)`

### `patches`

**الغرض.** محاولات الإصلاح على فروع معزولة مع الفروق والسبب الجذري.

**الاحتفاظ (مقترح).** تُحفظ مع النتيجة.

| العمود | النوع | يقبل null | الافتراضي |
|---|---|---|---|
| `id` | `pat_id` | no | - |
| `finding_id` | `fnd_id` | no | - |
| `attempt` | `integer` | no | - |
| `branch` | `text` | no | - |
| `diff_ref` | `text` | no | - |
| `diff_sha256` | `text` | no | - |
| `changed_files` | `text[]` | no | - |
| `root_cause` | `jsonb` | no | - |
| `status` | `text` | no | `'proposed'::text` |
| `created_by_run` | `run_id` | yes | - |
| `created_at` | `timestamp with time zone` | no | `now()` |

**القيود**

- `UNIQUE (finding_id, attempt)`
- `PRIMARY KEY (id)`
- `FOREIGN KEY (created_by_run) REFERENCES agent_runs(id)`
- `FOREIGN KEY (finding_id) REFERENCES findings(id) ON DELETE CASCADE`
- `CHECK (((attempt >= 1) AND (attempt <= 3)))`
- `CHECK ((status = ANY (ARRAY['proposed'::text, 'tests_failed'::text, 'ready_for_review'::text, 'approved'::text, 'rejected'::text, 'merged_by_human'::text, 'superseded'::text])))`

**الفهارس**

- `UNIQUE patches_finding_id_attempt_key ON patches USING btree (finding_id, attempt)`
- `patches_finding_id_idx ON patches USING btree (finding_id)`
- `UNIQUE patches_pkey ON patches USING btree (id)`

### `projects`

**الغرض.** الحاوية العليا لتطبيق مستهدف.

**الاحتفاظ (مقترح).** حتى يؤرشفه المالك ثم سياسة المشروع.

| العمود | النوع | يقبل null | الافتراضي |
|---|---|---|---|
| `id` | `prj_id` | no | - |
| `owner_id` | `usr_id` | no | - |
| `name` | `text` | no | - |
| `language` | `text` | no | `'python'::text` |
| `framework_hint` | `text` | yes | - |
| `created_at` | `timestamp with time zone` | no | `now()` |
| `archived_at` | `timestamp with time zone` | yes | - |

**القيود**

- `UNIQUE (owner_id, name)`
- `PRIMARY KEY (id)`
- `FOREIGN KEY (owner_id) REFERENCES users(id)`
- `CHECK ((language = 'python'::text))`

**الفهارس**

- `projects_owner_id_idx ON projects USING btree (owner_id)`
- `UNIQUE projects_owner_id_name_key ON projects USING btree (owner_id, name)`
- `UNIQUE projects_pkey ON projects USING btree (id)`

### `reports`

**الغرض.** ملفات التقارير المولّدة مع التجزئة وإصدار المولّد.

**الاحتفاظ (مقترح).** تُحفظ كما صدرت ويمكن إعادة توليدها.

| العمود | النوع | يقبل null | الافتراضي |
|---|---|---|---|
| `id` | `rpt_id` | no | - |
| `scan_id` | `scn_id` | no | - |
| `format` | `text` | no | - |
| `version` | `integer` | no | `1` |
| `content_ref` | `text` | no | - |
| `content_sha256` | `text` | no | - |
| `generator_version` | `text` | no | - |
| `generated_at` | `timestamp with time zone` | no | `now()` |

**القيود**

- `UNIQUE (scan_id, format, version)`
- `PRIMARY KEY (id)`
- `FOREIGN KEY (scan_id) REFERENCES scans(id) ON DELETE CASCADE`
- `CHECK ((format = ANY (ARRAY['pdf'::text, 'html'::text, 'markdown'::text, 'json'::text])))`

**الفهارس**

- `UNIQUE reports_pkey ON reports USING btree (id)`
- `UNIQUE reports_scan_id_format_version_key ON reports USING btree (scan_id, format, version)`

### `repositories`

**الغرض.** مستودعات المصدر (GitHub أو ZIP) لمشروع.

**الاحتفاظ (مقترح).** مع المشروع.

| العمود | النوع | يقبل null | الافتراضي |
|---|---|---|---|
| `id` | `rep_id` | no | - |
| `project_id` | `prj_id` | no | - |
| `source_type` | `text` | no | - |
| `url` | `text` | no | - |
| `default_ref` | `text` | no | `'main'::text` |
| `latest_commit` | `text` | yes | - |
| `created_at` | `timestamp with time zone` | no | `now()` |

**القيود**

- `UNIQUE (project_id, url)`
- `PRIMARY KEY (id)`
- `FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE`
- `CHECK ((latest_commit ~ '^[0-9a-f]{7,40}$'::text))`
- `CHECK ((source_type = ANY (ARRAY['github'::text, 'zip'::text])))`

**الفهارس**

- `UNIQUE repositories_pkey ON repositories USING btree (id)`
- `UNIQUE repositories_project_id_url_key ON repositories USING btree (project_id, url)`

### `repositories_analysis`

**الغرض.** ترويسة تحليل واحدة لكل فحص: الإصدار وأطر العمل ونقاط الدخول والتحذيرات.

**الاحتفاظ (مقترح).** مقترح: سنة.

| العمود | النوع | يقبل null | الافتراضي |
|---|---|---|---|
| `id` | `ran_id` | no | - |
| `scan_id` | `scn_id` | no | - |
| `repository_id` | `rep_id` | no | - |
| `commit_sha` | `text` | no | - |
| `files_analyzed` | `integer` | no | - |
| `frameworks` | `text[]` | no | `'{}'::text[]` |
| `entry_points` | `text[]` | no | `'{}'::text[]` |
| `warnings` | `jsonb` | no | `'[]'::jsonb` |
| `created_at` | `timestamp with time zone` | no | `now()` |

**القيود**

- `UNIQUE (scan_id)`
- `PRIMARY KEY (id)`
- `FOREIGN KEY (repository_id) REFERENCES repositories(id)`
- `FOREIGN KEY (scan_id) REFERENCES scans(id) ON DELETE CASCADE`

**الفهارس**

- `UNIQUE repositories_analysis_pkey ON repositories_analysis USING btree (id)`
- `UNIQUE repositories_analysis_scan_id_key ON repositories_analysis USING btree (scan_id)`

### `scans`

**الغرض.** تنفيذ واحد لسير العمل مع correlation id.

**الاحتفاظ (مقترح).** يُحفظ مع التقييم.

| العمود | النوع | يقبل null | الافتراضي |
|---|---|---|---|
| `id` | `scn_id` | no | - |
| `engagement_id` | `eng_id` | no | - |
| `scope_manifest_id` | `scm_id` | no | - |
| `repository_id` | `rep_id` | yes | - |
| `commit_sha` | `text` | yes | - |
| `correlation_id` | `text` | no | - |
| `status` | `text` | no | `'queued'::text` |
| `config` | `jsonb` | no | `'{}'::jsonb` |
| `requested_by` | `usr_id` | no | - |
| `created_at` | `timestamp with time zone` | no | `now()` |
| `started_at` | `timestamp with time zone` | yes | - |
| `finished_at` | `timestamp with time zone` | yes | - |

**القيود**

- `UNIQUE (correlation_id)`
- `PRIMARY KEY (id)`
- `FOREIGN KEY (engagement_id) REFERENCES engagements(id)`
- `FOREIGN KEY (repository_id) REFERENCES repositories(id)`
- `FOREIGN KEY (requested_by) REFERENCES users(id)`
- `FOREIGN KEY (scope_manifest_id) REFERENCES scope_manifests(id)`
- `CHECK ((commit_sha ~ '^[0-9a-f]{7,40}$'::text))`
- `CHECK ((correlation_id ~ '^cor_[0-9a-f]{8,}$'::text))`
- `CHECK ((status = ANY (ARRAY['queued'::text, 'running'::text, 'awaiting_approval'::text, 'completed'::text, 'failed'::text, 'cancelled'::text, 'blocked'::text])))`

**الفهارس**

- `UNIQUE scans_correlation_id_key ON scans USING btree (correlation_id)`
- `scans_engagement_id_created_at_idx ON scans USING btree (engagement_id, created_at DESC)`
- `UNIQUE scans_pkey ON scans USING btree (id)`
- `scans_status_idx ON scans USING btree (status) WHERE (status = ANY (ARRAY['queued'::text, 'running'::text, 'awaiting_approval'::text]))`

### `scope_manifests`

**الغرض.** بيانات نطاق بإصدارات وتجزئة محتوى.

**الاحتفاظ (مقترح).** تُحفظ مع التقييم؛ لا تُعدَّل بل تُصدَّر إصدارات.

| العمود | النوع | يقبل null | الافتراضي |
|---|---|---|---|
| `id` | `scm_id` | no | - |
| `engagement_id` | `eng_id` | no | - |
| `version` | `integer` | no | - |
| `manifest` | `jsonb` | no | - |
| `manifest_sha256` | `text` | no | - |
| `valid` | `boolean` | no | `false` |
| `validated_at` | `timestamp with time zone` | yes | - |
| `created_by` | `usr_id` | no | - |
| `created_at` | `timestamp with time zone` | no | `now()` |

**القيود**

- `UNIQUE (engagement_id, version)`
- `PRIMARY KEY (id)`
- `FOREIGN KEY (created_by) REFERENCES users(id)`
- `FOREIGN KEY (engagement_id) REFERENCES engagements(id) ON DELETE CASCADE`
- `CHECK ((version > 0))`

**الفهارس**

- `UNIQUE scope_manifests_engagement_id_version_key ON scope_manifests USING btree (engagement_id, version)`
- `UNIQUE scope_manifests_pkey ON scope_manifests USING btree (id)`

### `security_invariants`

**الغرض.** القواعد المرشحة والمعتمدة التي يجب أن يحققها التطبيق.

**الاحتفاظ (مقترح).** عمر المشروع؛ تُسحب ولا تُحذف.

| العمود | النوع | يقبل null | الافتراضي |
|---|---|---|---|
| `id` | `inv_id` | no | - |
| `project_id` | `prj_id` | no | - |
| `analysis_id` | `ran_id` | yes | - |
| `statement` | `text` | no | - |
| `kind` | `text` | no | - |
| `source` | `text` | no | - |
| `confidence` | `numeric(3,2)` | no | - |
| `status` | `text` | no | `'candidate'::text` |
| `applies_to_node_ids` | `bigint[]` | no | `'{}'::bigint[]` |
| `reviewed_by` | `usr_id` | yes | - |
| `created_at` | `timestamp with time zone` | no | `now()` |

**القيود**

- `PRIMARY KEY (id)`
- `FOREIGN KEY (analysis_id) REFERENCES repositories_analysis(id) ON DELETE SET NULL`
- `FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE`
- `FOREIGN KEY (reviewed_by) REFERENCES users(id)`
- `CHECK (((confidence >= (0)::numeric) AND (confidence <= (1)::numeric)))`
- `CHECK ((kind = ANY (ARRAY['ownership'::text, 'role_restriction'::text, 'state_transition'::text, 'authentication_required'::text])))`
- `CHECK ((source = ANY (ARRAY['code'::text, 'declared_policy'::text])))`
- `CHECK ((status = ANY (ARRAY['candidate'::text, 'accepted'::text, 'rejected'::text, 'retired'::text])))`

**الفهارس**

- `UNIQUE security_invariants_pkey ON security_invariants USING btree (id)`
- `security_invariants_project_id_status_idx ON security_invariants USING btree (project_id, status)`

### `skill_metadata`

**الغرض.** مقاطع المهارات القابلة للاسترجاع مع الكلمات المفتاحية والتضمينات.

**الاحتفاظ (مقترح).** يُعاد بناؤها عند إعادة الفهرسة؛ تتبع skills.

| العمود | النوع | يقبل null | الافتراضي |
|---|---|---|---|
| `id` | `skm_id` | no | - |
| `skill_id` | `skl_id` | no | - |
| `chunk_index` | `integer` | no | - |
| `heading` | `text` | yes | - |
| `content_excerpt` | `text` | no | - |
| `token_count` | `integer` | no | - |
| `phases` | `text[]` | no | `'{}'::text[]` |
| `vuln_categories` | `text[]` | no | `'{}'::text[]` |
| `keywords` | `tsvector` | yes | - |
| `embedding` | `vector(384)` | yes | - |

**القيود**

- `UNIQUE (skill_id, chunk_index)`
- `PRIMARY KEY (id)`
- `FOREIGN KEY (skill_id) REFERENCES skills(id) ON DELETE CASCADE`
- `CHECK ((token_count > 0))`

**الفهارس**

- `skill_metadata_embedding_idx ON skill_metadata USING hnsw (embedding vector_cosine_ops)`
- `skill_metadata_keywords_idx ON skill_metadata USING gin (keywords)`
- `UNIQUE skill_metadata_pkey ON skill_metadata USING btree (id)`
- `UNIQUE skill_metadata_skill_id_chunk_index_key ON skill_metadata USING btree (skill_id, chunk_index)`
- `skill_metadata_vuln_categories_idx ON skill_metadata USING gin (vuln_categories)`

### `skill_usage_logs`

**الغرض.** أي مقاطع مهارات حُقنت في أي تشغيل وكيل مع الرموز.

**الاحتفاظ (مقترح).** مقترح: سنة (أثر الإسناد).

| العمود | النوع | يقبل null | الافتراضي |
|---|---|---|---|
| `id` | `bigint` | no | - |
| `skill_id` | `skl_id` | no | - |
| `agent_run_id` | `run_id` | no | - |
| `chunk_ids` | `skm_id[]` | no | - |
| `score` | `real` | no | - |
| `tokens_injected` | `integer` | no | - |
| `created_at` | `timestamp with time zone` | no | `now()` |

**القيود**

- `PRIMARY KEY (id)`
- `FOREIGN KEY (agent_run_id) REFERENCES agent_runs(id) ON DELETE CASCADE`
- `FOREIGN KEY (skill_id) REFERENCES skills(id)`

**الفهارس**

- `skill_usage_logs_agent_run_id_idx ON skill_usage_logs USING btree (agent_run_id)`
- `UNIQUE skill_usage_logs_pkey ON skill_usage_logs USING btree (id)`

### `skills`

**الغرض.** مهارات Claude-BugHunter المفهرسة مع الإصدار والمسار والتراخيص.

**الاحتفاظ (مقترح).** بإصدارات؛ وتبقى الإصدارات القديمة ما دامت مرجعاً في سجلات الاستخدام.

| العمود | النوع | يقبل null | الافتراضي |
|---|---|---|---|
| `id` | `skl_id` | no | - |
| `name` | `text` | no | - |
| `source_repo` | `text` | no | - |
| `source_commit` | `text` | no | - |
| `path` | `text` | no | - |
| `description` | `text` | no | - |
| `upstream_sources` | `text[]` | no | `'{}'::text[]` |
| `license_code` | `text` | no | `'MIT'::text` |
| `license_content` | `text` | no | `'CC-BY-4.0'::text` |
| `category` | `text` | yes | - |
| `enabled` | `boolean` | no | `true` |
| `indexed_at` | `timestamp with time zone` | no | `now()` |

**القيود**

- `UNIQUE (name, source_commit)`
- `PRIMARY KEY (id)`

**الفهارس**

- `skills_category_idx ON skills USING btree (category) WHERE enabled`
- `UNIQUE skills_name_source_commit_key ON skills USING btree (name, source_commit)`
- `UNIQUE skills_pkey ON skills USING btree (id)`

### `state_snapshots`

**الغرض.** صفوف حالة قاعدة البيانات قبل وبعد في العزل (غير قابلة للتعديل).

**الاحتفاظ (مقترح).** كما في الأدلة.

| العمود | النوع | يقبل null | الافتراضي |
|---|---|---|---|
| `id` | `snp_id` | no | - |
| `scan_id` | `scn_id` | no | - |
| `execution_id` | `exe_id` | yes | - |
| `sandbox_id` | `text` | no | - |
| `phase` | `text` | no | - |
| `table_name` | `text` | no | - |
| `row_key` | `jsonb` | no | - |
| `row_data` | `jsonb` | no | - |
| `row_hash` | `text` | no | - |
| `evidence_id` | `evd_id` | yes | - |
| `taken_at` | `timestamp with time zone` | no | `now()` |

**القيود**

- `PRIMARY KEY (id)`
- `FOREIGN KEY (evidence_id) REFERENCES evidence(id)`
- `FOREIGN KEY (execution_id) REFERENCES test_executions(id)`
- `FOREIGN KEY (scan_id) REFERENCES scans(id) ON DELETE CASCADE`
- `CHECK ((phase = ANY (ARRAY['before'::text, 'after'::text])))`

**الفهارس**

- `state_snapshots_execution_id_idx ON state_snapshots USING btree (execution_id)`
- `UNIQUE state_snapshots_pkey ON state_snapshots USING btree (id)`
- `state_snapshots_scan_id_table_name_idx ON state_snapshots USING btree (scan_id, table_name)`

### `test_cases`

**الغرض.** خطط الاختبار (بادئة tpl_) مع الخطوات وفحوص الحالة.

**الاحتفاظ (مقترح).** مع الفحص.

| العمود | النوع | يقبل null | الافتراضي |
|---|---|---|---|
| `id` | `tpl_id` | no | - |
| `hypothesis_id` | `hyp_id` | no | - |
| `method` | `text` | no | - |
| `steps` | `jsonb` | no | - |
| `identities` | `text[]` | no | - |
| `expected_secure_behavior` | `text` | no | - |
| `state_checks` | `jsonb` | no | `'[]'::jsonb` |
| `status` | `text` | no | `'approved'::text` |
| `created_at` | `timestamp with time zone` | no | `now()` |

**القيود**

- `PRIMARY KEY (id)`
- `FOREIGN KEY (hypothesis_id) REFERENCES vulnerability_hypotheses(id) ON DELETE CASCADE`
- `CHECK (((method <> 'paired_identity'::text) OR (cardinality(identities) >= 2)))`
- `CHECK ((method = ANY (ARRAY['paired_identity'::text, 'single_identity'::text, 'workflow_sequence'::text])))`
- `CHECK ((status = ANY (ARRAY['draft'::text, 'approved'::text, 'executed'::text])))`

**الفهارس**

- `test_cases_hypothesis_id_idx ON test_cases USING btree (hypothesis_id)`
- `UNIQUE test_cases_pkey ON test_cases USING btree (id)`

### `test_executions`

**الغرض.** كل طلب منفّذ من خطة اختبار، صف لكل خطوة هوية.

**الاحتفاظ (مقترح).** مع الفحص؛ منقّحة.

| العمود | النوع | يقبل null | الافتراضي |
|---|---|---|---|
| `id` | `exe_id` | no | - |
| `test_case_id` | `tpl_id` | no | - |
| `task_id` | `tsk_id` | no | - |
| `identity_id` | `text` | no | - |
| `case_label` | `text` | no | - |
| `request` | `jsonb` | no | - |
| `response_status` | `integer` | yes | - |
| `response_excerpt` | `text` | yes | - |
| `sandbox_id` | `text` | no | - |
| `evidence_id` | `evd_id` | yes | - |
| `started_at` | `timestamp with time zone` | no | `now()` |
| `finished_at` | `timestamp with time zone` | yes | - |

**القيود**

- `PRIMARY KEY (id)`
- `FOREIGN KEY (evidence_id) REFERENCES evidence(id)`
- `FOREIGN KEY (task_id) REFERENCES agent_tasks(id)`
- `FOREIGN KEY (test_case_id) REFERENCES test_cases(id)`

**الفهارس**

- `UNIQUE test_executions_pkey ON test_executions USING btree (id)`
- `test_executions_test_case_id_idx ON test_executions USING btree (test_case_id)`

### `users`

**الغرض.** مستخدمو التطبيق وأدوارهم؛ والهوية عند مزوّد خارجي.

**الاحتفاظ (مقترح).** عمر الحساب؛ يُعطَّل ولا يُحذف.

| العمود | النوع | يقبل null | الافتراضي |
|---|---|---|---|
| `id` | `usr_id` | no | - |
| `email` | `text` | no | - |
| `display_name` | `text` | no | - |
| `role` | `text` | no | - |
| `auth_subject` | `text` | yes | - |
| `created_at` | `timestamp with time zone` | no | `now()` |
| `disabled_at` | `timestamp with time zone` | yes | - |

**القيود**

- `UNIQUE (auth_subject)`
- `UNIQUE (email)`
- `PRIMARY KEY (id)`
- `CHECK ((role = ANY (ARRAY['admin'::text, 'analyst'::text, 'reviewer'::text, 'viewer'::text])))`

**الفهارس**

- `UNIQUE users_auth_subject_key ON users USING btree (auth_subject)`
- `UNIQUE users_email_key ON users USING btree (email)`
- `UNIQUE users_pkey ON users USING btree (id)`

### `vulnerability_hypotheses`

**الغرض.** فرضيات قابلة للاختبار مع الفئة والتعليل والأولوية.

**الاحتفاظ (مقترح).** مع الفحص.

| العمود | النوع | يقبل null | الافتراضي |
|---|---|---|---|
| `id` | `hyp_id` | no | - |
| `scan_id` | `scn_id` | no | - |
| `endpoint_id` | `ep_id` | no | - |
| `invariant_id` | `inv_id` | no | - |
| `category` | `text` | no | - |
| `title` | `text` | no | - |
| `rationale` | `text` | no | - |
| `priority` | `smallint` | no | - |
| `status` | `text` | no | `'proposed'::text` |
| `skill_refs` | `text[]` | no | `'{}'::text[]` |
| `created_by_run` | `run_id` | yes | - |
| `created_at` | `timestamp with time zone` | no | `now()` |

**القيود**

- `PRIMARY KEY (id)`
- `FOREIGN KEY (created_by_run) REFERENCES agent_runs(id)`
- `FOREIGN KEY (endpoint_id) REFERENCES endpoints(id)`
- `FOREIGN KEY (invariant_id) REFERENCES security_invariants(id)`
- `FOREIGN KEY (scan_id) REFERENCES scans(id) ON DELETE CASCADE`
- `CHECK ((category = ANY (ARRAY['broken_access_control'::text, 'idor'::text, 'authn_authz_flaw'::text, 'business_logic'::text])))`
- `CHECK (((priority >= 1) AND (priority <= 5)))`
- `CHECK ((status = ANY (ARRAY['proposed'::text, 'testing'::text, 'confirmed'::text, 'unconfirmed'::text, 'rejected'::text])))`

**الفهارس**

- `UNIQUE vulnerability_hypotheses_pkey ON vulnerability_hypotheses USING btree (id)`
- `vulnerability_hypotheses_scan_id_priority_idx ON vulnerability_hypotheses USING btree (scan_id, priority)`


# 6. دمج pgvector

![دمج pgvector](../diagrams/d13_pgvector.svg)

- عمودا متجهات: `skill_metadata.embedding` و`memory_items.embedding` من النوع `vector(384)`.
- **البعد 384 مقترح.** ويجب أن يساوي حجم خرج نموذج التضمين المختار في المرحلة 1؛ وتغيير النموذج يعني إعادة التضمين وإعادة بناء الفهرس.
- الفهرس: HNSW مع `vector_cosine_ops`؛ والاستعلام بالمعامل `<=>` مع `ORDER BY ... LIMIT k`.
- يُدمج البحث المتجهي دائماً مع مرشحات البيانات الوصفية. فمع فهرس تقريبي قد يعيد مرشّح مقيّد يُطبَّق بعد مسح الفهرس أقل من `k` صفاً؛ وتضيف إصدارات pgvector الأحدث خيارات لهذا، فتحقق من إصدار pgvector المنشور (الإصدار المُتحقَّق منه هنا 0.6.0).
- المتجهات مساعد استرجاع فقط. وفقدانها يكلّف إعادة فهرسة لا فقدان بيانات.

# 7. دورة حياة البيانات والاحتفاظ

![دورة حياة البيانات](../diagrams/d14_lifecycle.svg)

| البيانات | الاحتفاظ المقترح | ملاحظات |
|---|---|---|
| الأدلة ولقطات الحالة | سنة بعد إغلاق التقييم | المحتوى في مخزن الكائنات؛ والحجز القانوني يتقدم |
| النتائج والإصلاحات والموافقات والتقارير | تُحفظ | فهي المُخرَج وسجل القرار |
| سجلات التدقيق | سنتان | للإلحاق فقط؛ والإجراءات المحجوبة (`allowed=false`) مفهرسة |
| رسائل الوكلاء والمهام والتشغيلات | 90 إلى 180 يوماً | تبقى الملخصات القابلة لإعادة البناء في النتائج |
| عقد الشيفرة وحوافها | 90 يوماً | قابلة للاشتقاق من الإصدار المثبّت |
| عناصر الذاكرة | حسب `expires_at` | تبقى العناصر المستبدلة حتى التطهير |
| سجلات استخدام المهارات | سنة | أثر الإسناد للامتثال لـ CC BY 4.0 |

يعمل التطهير بدور مخصص يملك إجراء التطهير. ولا تملك أدوار التطبيق صلاحية DELETE على الجداول غير القابلة للتعديل.

# 8. الأمان

- **الأدوار (مقترح):** `app_rw` (بلا DELETE أو TRUNCATE على `evidence` و`state_snapshots` و`audit_logs`)، و`app_ro` للوحة التحكم، و`purge_role` للاحتفاظ.
- **عدم التعديل:** مشغلات الصفوف تمنع UPDATE وDELETE. ولا تمنع مشغلات الصفوف `TRUNCATE`؛ فتُسحب هذه الصلاحية من أدوار التطبيق.
- **تعدد المستأجرين:** ليس في النسخة الأولى. وعند إضافته يُستخدم أمان مستوى الصف بمفتاح `project_id`.
- **النقل والتخزين:** TLS إلى قاعدة البيانات؛ والتشفير عند السكون في طبقة القرص أو الخدمة المُدارة؛ ونسخ احتياطية مشفرة.
- **السلامة:** كل صف دليل يخزّن SHA-256 لمحتواه؛ ويعيد التحقق فحصه قبل الاستخدام.
- **قابلية التدقيق:** قرارات بوابة النطاق والموافقات والإجراءات المحجوبة تُكتب في `audit_logs`.

# 9. التحقق المنفَّذ

| الفحص | النتيجة |
|---|---|
| تنفيذ DDL كاملاً على PostgreSQL 16 مع pgvector 0.6.0 | نجح؛ 30 جدولاً |
| رفض نتيجة مؤكدة بلا خطورة | نجح |
| رفض UPDATE على `evidence` | نجح |
| رفض DELETE على `audit_logs` | نجح |
| رفض بادئة معرّف خاطئة بالنطاق | نجح |
| رفض اختبار مزدوج بهوية واحدة | نجح |
| رفض موافقة محسومة بلا مراجع | نجح |
| رفض عنصر ذاكرة مكرر | نجح |
| تنفيذ استعلام الاسترجاع الهجين على pgvector | نجح (متجهات اصطناعية؛ بلا ادعاء جودة) |

# 10. القيود المعروفة

- لم يُختبر تحت حمل؛ وخيارات الفهارس والتقسيم على نطاق واسع غير مختبرة. و`audit_logs` و`code_nodes` و`code_edges` مرشحة للتقسيم.
- التضمين بـ 384 بعداً وكل فترات الاحتفاظ مقترحات.
- سلوك pgvector مُتحقَّق منه على 0.6.0 فقط.
- أمان مستوى الصف ومنح الأدوار موصوفان لكن غير مضمَّنين في DDL.

# 11. المراجع

- وثائق PostgreSQL 16: https://www.postgresql.org/docs/16/
- pgvector: https://github.com/pgvector/pgvector
- Claude-BugHunter: https://github.com/elementalsouls/Claude-BugHunter
