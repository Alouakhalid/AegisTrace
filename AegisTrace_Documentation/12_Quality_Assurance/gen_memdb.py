import pathlib
C=pathlib.Path("/home/claude/build/content")
en = """# 1. Overview and Design Principles

This document defines how AegisTrace stores, remembers and retrieves information: the memory model, the retrieval pipeline, the PostgreSQL schema and its pgvector usage, retention and security. The DDL in `AegisTrace_Database_SQL_Appendix.sql` was **executed on PostgreSQL 16 with pgvector 0.6.0** and the table reference in Section 5 is generated from that live schema, so the document cannot drift from the SQL.

| Principle | Consequence |
|---|---|
| Prefixed text identifiers equal contract identifiers | A database id and a JSON id are the same string; domains (`prj_id`, `fnd_id`...) reject wrong prefixes |
| Evidence is immutable | `evidence`, `state_snapshots` and `audit_logs` reject UPDATE and DELETE by trigger |
| Relational first | PostgreSQL is the system of record; vectors only help retrieval |
| `jsonb` only for variable payloads | Scope manifests, request bodies and task input/output; everything queried by a rule is a column |
| Secrets are never stored | Only references (`cred_*`); redaction happens before evidence is written |
| No table without a reason | 30 tables; each justified in Section 4 |

# 2. Memory Architecture

![Memory architecture](../diagrams/d10_memory.svg)

## 2.1 The five memory categories

| Category | What it holds | Stored in | Persist / expire | Plaintext secrets |
|---|---|---|---|---|
| A. Working | Current task context, agent state, temporary results | Process memory; the task row records input and output as an execution record | Discarded when the task ends | Never |
| B. Project | Repository structure, frameworks, routes, security invariants, earlier findings | `repositories_analysis`, `code_nodes`, `code_edges`, `endpoints`, `security_invariants`, `memory_items(type=project)` | Persist; items superseded when the commit changes (`superseded_by`) | Never |
| C. Engagement | Scope, scan history, test identities, findings, evidence, decisions | `scope_manifests`, `scans`, `findings`, `evidence`, `memory_items(type=engagement)` | Persist for the engagement, then the retention policy | Never; identities are `credential_ref` only |
| D. Knowledge | Methodologies, vulnerability patterns, skill metadata, reusable strategies | `skills`, `skill_metadata`, `memory_items(type=knowledge)` | Versioned by skill commit | Never |
| E. Remediation | Previous patches, root causes, successful and failed fixes, regression results | `patches`, `patch_tests`, `memory_items(type=remediation)` | Persist; failed fixes are kept as negative knowledge | Never |

## 2.2 Storage kinds compared

| Kind | Definition | Where | Mutable? | Example |
|---|---|---|---|---|
| Relational storage | Structured facts with constraints | PostgreSQL tables | Yes, by rules | `findings.severity` |
| Vector retrieval | Similarity search over embeddings | `embedding` columns, HNSW index | Rebuilt on re-index | Find skill chunks about ownership checks |
| Short-term working state | Context for one task | Process memory | Yes | Partial hypothesis list |
| Long-term project memory | Facts worth reusing across scans | `memory_items` and project tables | Superseded, not edited | "Orders are owned by `user_id`" |
| Execution logs | What ran and how | `agent_tasks`, `agent_runs`, `agent_messages`, structured logs | Append-mostly | Retry attempt 2 of run X |
| Immutable evidence | Proof for a finding | `evidence` (hashed content in the object store), `state_snapshots` | Never | HTTP exchange with SHA-256 |

## 2.3 What must never be stored as plaintext

Passwords, API keys (Groq, Tavily), session tokens, JWTs, cookies, `Authorization` headers and personal data from test responses. Credentials live in a secret manager and travel only as `cred_*` references that are resolved inside the sandbox. Evidence is redacted **before** it is written (following the Claude-BugHunter `evidence-hygiene` guidance), and memory writes pass a secret-pattern filter that rejects the write rather than storing a suspected secret.

# 3. Memory Retrieval

![Memory retrieval pipeline](../diagrams/d11_retrieval.svg)

| Stage | What happens |
|---|---|
| 1. Metadata filter | Restrict by `project_id`, `memory_type`, vulnerability category or phase, and `expires_at IS NULL OR expires_at > now()`. This is what makes retrieval project-specific and prevents cross-project leakage |
| 2a. Keyword retrieval | Full-text `tsvector` rank over keywords and headings; precise for identifiers such as `IDOR` or `hunt-idor` |
| 2b. Vector similarity | Cosine distance over embeddings; finds related wording that keywords miss |
| 3. Hybrid merge | Reciprocal Rank Fusion: `score = sum(1 / (60 + rank_i))` across the two lists, so no scale calibration between ts_rank and cosine is needed |
| 4. Deduplication | Unique `(project_id, memory_type, content_sha256)` on write; at read, drop items with `superseded_by` set |
| 5. Ranking | `final = rrf x importance x freshness` where `freshness = 0.5^(age_days / half_life)` |
| 6. Budget | Fill the token budget in rank order, stop at the budget, and attach attribution (skill name, commit, memory id) |

**Proposed defaults (to be tuned by experiment, not facts).** Half-lives: project 90 days, engagement 30, knowledge 365, remediation 180. Budget: retrieved material at most 25 percent of the model context; at most 3 skill chunks per hypothesis. Retrieved text is delimited and marked as untrusted data in every prompt.

**Skill retrieval** uses the same pipeline against `skill_metadata`, filtered by `vuln_categories` and `phases`. The example query in the SQL appendix runs against the schema; it was exercised on synthetic vectors, which proves it executes but says nothing about retrieval quality. Quality must be measured on real skills in Phase 1.

# 4. Database Architecture

## 4.1 Why 30 tables

All 29 requested entities were evaluated. All are kept because each has a distinct lifecycle or access pattern. One table was added: `finding_evidence`. Evidence must be immutable, so it cannot carry a `finding_id` that is filled in later when a finding is created; a junction table links them without ever updating an evidence row.

| Question | Decision |
|---|---|
| `agent_tasks` vs `agent_runs` | Separate: one task can have several runs (retries), and the contract carries both `task_id` and `agent_run_id` |
| `test_cases` | Stores **test plans** (contract prefix `tpl_`); the name follows the requested entity list |
| `skills` vs `skill_metadata` | Separate: one skill has many retrievable chunks with embeddings |
| `repositories_analysis` | Kept as the per-scan header that code nodes belong to |

**Deliberate denormalization.** `security_invariants.applies_to_node_ids` is an array rather than a junction table because it is read-mostly and always read with the invariant. `agent_tasks.depends_on` is an array for the same reason. `findings` duplicates `endpoint_id` and `invariant_id` from its hypothesis so the findings list needs no joins.

## 4.2 Entity relationship diagrams

Generated from the foreign keys of the live schema. The overview shows how the eight table groups depend on each other; Figures 12a to 12d show the tables inside each group. Foreign keys that cross figures are listed in each table's constraints in Section 5.

![ERD overview](../diagrams/d12_overview.svg)

![ERD a](../diagrams/d12a_erd.svg)

![ERD b](../diagrams/d12b_erd.svg)

![ERD c](../diagrams/d12c_erd.svg)

![ERD d](../diagrams/d12d_erd.svg)

# 5. Table Reference

Generated from the live database: purpose and retention are authored; columns, constraints and indexes come from PostgreSQL catalogs. Retention values are **proposed defaults**, configurable per deployment.

@@TABLES@@

# 6. pgvector Integration

![pgvector integration](../diagrams/d13_pgvector.svg)

- Two vector columns: `skill_metadata.embedding` and `memory_items.embedding`, type `vector(384)`.
- **The dimension 384 is a proposal.** It must equal the output size of the embedding model chosen in Phase 1; changing the model means re-embedding and rebuilding the index.
- Index: HNSW with `vector_cosine_ops`; query with the `<=>` operator and `ORDER BY ... LIMIT k`.
- Always combine vector search with metadata filters. With an approximate index, a restrictive filter applied after the index scan can return fewer than `k` rows; newer pgvector releases add options for this, so verify against the pgvector version you deploy (the validated version here is 0.6.0).
- Vectors are a retrieval aid only. Losing them costs a re-index, never data.

# 7. Data Lifecycle and Retention

![Data lifecycle](../diagrams/d14_lifecycle.svg)

| Data | Proposed retention | Notes |
|---|---|---|
| Evidence, state snapshots | 1 year after engagement close | Content in the object store; legal hold overrides |
| Findings, patches, approvals, reports | Kept | They are the deliverable and the decision record |
| Audit logs | 2 years | Append-only; blocked actions (`allowed=false`) are indexed |
| Agent messages, tasks and runs | 90 to 180 days | Reproducible summaries stay in findings |
| Code nodes and edges | 90 days | Re-derivable from the pinned commit |
| Memory items | By `expires_at` | Superseded items are retained until purged |
| Skill usage logs | 1 year | Attribution trail for CC BY 4.0 compliance |

Purging runs under a dedicated role that owns the purge procedure. Application roles hold no DELETE privilege on immutable tables.

# 8. Security

- **Roles (proposal):** `app_rw` (no DELETE or TRUNCATE on `evidence`, `state_snapshots`, `audit_logs`), `app_ro` for the dashboard, `purge_role` for retention.
- **Immutability:** row triggers block UPDATE and DELETE. Row triggers do not block `TRUNCATE`; revoke that privilege from application roles.
- **Multi-tenancy:** not in the MVP. If added, use row-level security keyed by `project_id`.
- **Transport and storage:** TLS to the database; encryption at rest at the disk or managed-service layer; encrypted backups.
- **Integrity:** every evidence row stores a SHA-256 of its content; Verification re-checks it before use.
- **Auditability:** scope-gate decisions, approvals and blocked actions are written to `audit_logs`.

# 9. Validation Performed

| Check | Result |
|---|---|
| Full DDL executed on PostgreSQL 16 with pgvector 0.6.0 | Succeeded; 30 tables |
| Confirmed finding without severity rejected | Passed |
| UPDATE on `evidence` rejected | Passed |
| DELETE on `audit_logs` rejected | Passed |
| Wrong id prefix rejected by domain | Passed |
| Paired test with one identity rejected | Passed |
| Decided approval without reviewer rejected | Passed |
| Duplicate memory item rejected | Passed |
| Hybrid retrieval query executes on pgvector | Passed (synthetic vectors; no quality claim) |

# 10. Known Limitations

- Not load-tested; index and partition choices at scale are untested. `audit_logs`, `code_nodes` and `code_edges` are candidates for partitioning.
- The 384-dimension embedding and all retention periods are proposals.
- pgvector behavior was validated on 0.6.0 only.
- Row-level security and role grants are described but not included in the DDL.

# 11. References

- PostgreSQL 16 documentation: https://www.postgresql.org/docs/16/
- pgvector: https://github.com/pgvector/pgvector
- Claude-BugHunter: https://github.com/elementalsouls/Claude-BugHunter
"""
ar = """# 1. نظرة عامة ومبادئ التصميم

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

@@TABLES@@

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
"""
for lang,txt in (("en",en),("ar",ar)):
    t=(C/f"_db_tables_{lang}.md").read_text(encoding="utf-8")
    (C/f"memdb_{lang}.md").write_text(txt.replace("@@TABLES@@",t),encoding="utf-8")
print("ok")
