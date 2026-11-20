import subprocess, pathlib, collections
def q(sql):
    r=subprocess.run(["su","postgres","-c",f"psql -At -F '\x1f' -d aegis_test -c \"{sql}\""],capture_output=True,text=True)
    return [l.split("\x1f") for l in r.stdout.strip().split("\n") if l]
tables=[r[0] for r in q("select tablename from pg_tables where schemaname='public' order by tablename")]
cols=collections.defaultdict(list)
for t,n,ty,nn,df in q("select c.relname,a.attname,format_type(a.atttypid,a.atttypmod),a.attnotnull,coalesce(pg_get_expr(d.adbin,d.adrelid),'') from pg_attribute a join pg_class c on c.oid=a.attrelid join pg_namespace s on s.oid=c.relnamespace left join pg_attrdef d on d.adrelid=a.attrelid and d.adnum=a.attnum where s.nspname='public' and c.relkind='r' and a.attnum>0 and not a.attisdropped order by c.relname,a.attnum"):
    cols[t].append((n,ty,"no" if nn=="t" else "yes",df))
cons=collections.defaultdict(list)
for t,k,d in q("select conrelid::regclass::text,contype,pg_get_constraintdef(oid) from pg_constraint where connamespace='public'::regnamespace and contype in ('p','f','u','c') order by conrelid::regclass::text,contype desc,conname"):
    cons[t].append((k,d))
idx=collections.defaultdict(list)
for t,d in q("select tablename,indexdef from pg_indexes where schemaname='public' order by tablename,indexname"):
    idx[t].append(d.replace("CREATE INDEX ","").replace("CREATE UNIQUE INDEX ","UNIQUE ").replace("public.",""))
M={ # table: (purpose en, purpose ar, retention en, retention ar)
"users":("Application users and roles; identity lives at the external provider.","مستخدمو التطبيق وأدوارهم؛ والهوية عند مزوّد خارجي.","Life of the account; disable, do not delete.","عمر الحساب؛ يُعطَّل ولا يُحذف."),
"projects":("Top-level container for a target application.","الحاوية العليا لتطبيق مستهدف.","Until archived by the owner; then project policy.","حتى يؤرشفه المالك ثم سياسة المشروع."),
"repositories":("Source repositories (GitHub or ZIP) of a project.","مستودعات المصدر (GitHub أو ZIP) لمشروع.","With the project.","مع المشروع."),
"engagements":("One authorized assessment with attestation, mode and environment.","تقييم مصرّح واحد مع الإقرار والنمط والبيئة.","Kept for audit for the audit period.","يُحفظ لمدة التدقيق."),
"scope_manifests":("Versioned scope manifests with a content hash.","بيانات نطاق بإصدارات وتجزئة محتوى.","Kept with the engagement; never edited, only versioned.","تُحفظ مع التقييم؛ لا تُعدَّل بل تُصدَّر إصدارات."),
"scans":("One execution of the workflow with its correlation id.","تنفيذ واحد لسير العمل مع correlation id.","Kept with the engagement.","يُحفظ مع التقييم."),
"agent_tasks":("Units of agent work with dependencies, input and output.","وحدات عمل الوكلاء مع الاعتماديات والمدخلات والمخرجات.","Proposal: 180 days after scan end.","مقترح: 180 يوماً بعد انتهاء الفحص."),
"agent_runs":("Each invocation of an agent for a task (retries create rows).","كل استدعاء لوكيل لمهمة (الإعادات تنشئ صفوفاً).","Proposal: 180 days.","مقترح: 180 يوماً."),
"agent_messages":("Validated request/response messages between Orchestrator and agents.","رسائل الطلب/الاستجابة المُتحقَّق منها بين المنسّق والوكلاء.","Proposal: 90 days (large, reproducible from tasks).","مقترح: 90 يوماً (كبيرة ويمكن إعادة بنائها من المهام)."),
"repositories_analysis":("One analysis header per scan: commit, frameworks, entry points, warnings.","ترويسة تحليل واحدة لكل فحص: الإصدار وأطر العمل ونقاط الدخول والتحذيرات.","Proposal: 1 year.","مقترح: سنة."),
"code_nodes":("Nodes of the code graph (files, functions, routes, checks, models).","عقد رسم الشيفرة (ملفات ودوال ومسارات وفحوص ونماذج).","Proposal: 90 days; re-derivable from the commit.","مقترح: 90 يوماً؛ ويمكن اشتقاقها من الإصدار."),
"code_edges":("Edges of the code graph (calls, guards, reads, writes, data flow).","حواف رسم الشيفرة (استدعاءات وحراسة وقراءة وكتابة وتدفق بيانات).","Same as code_nodes.","كما في code_nodes."),
"security_invariants":("Candidate and accepted rules the application must satisfy.","القواعد المرشحة والمعتمدة التي يجب أن يحققها التطبيق.","Project lifetime; retire, do not delete.","عمر المشروع؛ تُسحب ولا تُحذف."),
"endpoints":("Discovered authorized endpoints, linked to code nodes.","نقاط النهاية المصرّح بها المكتشفة، مربوطة بعقد الشيفرة.","With the scan.","مع الفحص."),
"vulnerability_hypotheses":("Testable hypotheses with category, rationale and priority.","فرضيات قابلة للاختبار مع الفئة والتعليل والأولوية.","With the scan.","مع الفحص."),
"test_cases":("Test plans (contract prefix tpl_) with steps and state checks.","خطط الاختبار (بادئة tpl_) مع الخطوات وفحوص الحالة.","With the scan.","مع الفحص."),
"test_executions":("Each executed request of a test plan, one row per identity step.","كل طلب منفّذ من خطة اختبار، صف لكل خطوة هوية.","With the scan; redacted.","مع الفحص؛ منقّحة."),
"state_snapshots":("Immutable before/after rows of database state in the sandbox.","صفوف حالة قاعدة البيانات قبل وبعد في العزل (غير قابلة للتعديل).","Same as evidence.","كما في الأدلة."),
"evidence":("Immutable evidence records pointing to hashed content in the object store.","سجلات أدلة غير قابلة للتعديل تشير إلى محتوى مجزّأ في مخزن الكائنات.","Proposal: 1 year after engagement close; legal hold overrides.","مقترح: سنة بعد إغلاق التقييم؛ والحجز القانوني يتقدم."),
"findings":("Verified findings with verdict, severity, reproducibility and status.","نتائج متحقق منها مع الحكم والخطورة وقابلية الإعادة والحالة.","Kept; they are the product.","تُحفظ؛ فهي المنتج."),
"finding_evidence":("Junction linking findings to evidence without mutating evidence rows.","جدول ربط يصل النتائج بالأدلة دون تعديل صفوف الأدلة.","With the finding.","مع النتيجة."),
"skills":("Indexed Claude-BugHunter skills with commit, path and licenses.","مهارات Claude-BugHunter المفهرسة مع الإصدار والمسار والتراخيص.","Versioned; old commits kept while referenced by usage logs.","بإصدارات؛ وتبقى الإصدارات القديمة ما دامت مرجعاً في سجلات الاستخدام."),
"skill_metadata":("Retrievable skill chunks with keywords and embeddings.","مقاطع المهارات القابلة للاسترجاع مع الكلمات المفتاحية والتضمينات.","Rebuilt on re-index; follows skills.","يُعاد بناؤها عند إعادة الفهرسة؛ تتبع skills."),
"skill_usage_logs":("Which skill chunks were injected into which agent run, with tokens.","أي مقاطع مهارات حُقنت في أي تشغيل وكيل مع الرموز.","Proposal: 1 year (attribution trail).","مقترح: سنة (أثر الإسناد)."),
"patches":("Patch attempts on isolated branches with diffs and root cause.","محاولات الإصلاح على فروع معزولة مع الفروق والسبب الجذري.","Kept with the finding.","تُحفظ مع النتيجة."),
"patch_tests":("Unit, integration, regression and replay results per patch.","نتائج الوحدة والتكامل والانحدار والإعادة لكل إصلاح.","With the patch.","مع الإصلاح."),
"approvals":("Human decisions on patches; the mandatory gate.","القرارات البشرية على الإصلاحات؛ البوابة الإلزامية.","Kept for audit.","تُحفظ للتدقيق."),
"reports":("Generated report files with hashes and generator version.","ملفات التقارير المولّدة مع التجزئة وإصدار المولّد.","Kept; regenerable from data but preserved as issued.","تُحفظ كما صدرت ويمكن إعادة توليدها."),
"audit_logs":("Append-only log of actions, including blocked ones.","سجل للإلحاق فقط للإجراءات بما فيها المحجوبة.","Proposal: 2 years; never edited.","مقترح: سنتان؛ لا يُعدَّل."),
"memory_items":("Long-term memory with embeddings, importance, expiry and deduplication.","ذاكرة طويلة الأمد مع تضمينات وأهمية وانتهاء وإزالة تكرار.","Per type: see Section 2; expiry via expires_at.","حسب النوع: انظر القسم 2؛ والانتهاء عبر expires_at."),
}
assert set(M)==set(tables),(set(tables)^set(M))
def tbl(lang):
    i=0 if lang=="en" else 1; out=[]
    L=dict(en=("Purpose","Retention (proposal)","Columns","Constraints","Indexes","Column","Type","Nullable","Default"),ar=("الغرض","الاحتفاظ (مقترح)","الأعمدة","القيود","الفهارس","العمود","النوع","يقبل null","الافتراضي"))[lang]
    kn={"p":"PRIMARY KEY","f":"FOREIGN KEY","u":"UNIQUE","c":"CHECK"}
    for t in tables:
        rows="\n".join(f"| `{n}` | `{ty}` | {nl} | {('`'+df.replace('|','/')+'`') if df else '-'} |" for n,ty,nl,df in cols[t])
        cs="\n".join(f"- `{d.replace(chr(10),' ')}`" for k,d in cons[t]) or "-"
        ix="\n".join(f"- `{d}`" for d in idx[t]) or "-"
        out.append(f"### `{t}`\n\n**{L[0]}.** {M[t][i]}\n\n**{L[1]}.** {M[t][2+i]}\n\n| {L[5]} | {L[6]} | {L[7]} | {L[8]} |\n|---|---|---|---|\n{rows}\n\n**{L[3]}**\n\n{cs}\n\n**{L[4]}**\n\n{ix}\n")
    return "\n".join(out)
pathlib.Path("/home/claude/build/content/_db_tables_en.md").write_text(tbl("en"),encoding="utf-8")
pathlib.Path("/home/claude/build/content/_db_tables_ar.md").write_text(tbl("ar"),encoding="utf-8")
print(len(tables),"tables documented")
