# AegisTrace — UI Visual Design & Page Specification

> **Design direction:** Dark Enterprise Cybersecurity · Neon Violet · Electric Blue · Cyan · Glassmorphism  
> **Tagline:** From Code Understanding to Verified Security Remediation.  
> **Purpose:** تصور موحّد للواجهة النهائية المستقبلية. الـ Dummy Web الحالي مستثنى من تقييم التصميم ولا يُطلب إعادة بنائه ضمن هذا التصور.

## 1. Unified Visual Design System

| Token | Suggested value | Usage |
|---|---|---|
| Background | `#090B1C` | خلفية التطبيق |
| Surface | `#15152B` | Cards وPanels |
| Primary | `#793BFF` | الأزرار والعناصر الأساسية |
| Accent | `#24C8F5` | البيانات والروابط |
| Success | `#20D6A0` | Verified / Success |
| Warning | `#FFB547` | التحذيرات |
| Critical | `#FF5578` | Critical findings |
| Text | `#A5A7C4` | النصوص الثانوية |

### Global design rules
- Sidebar ثابتة في صفحات التطبيق الداخلية.
- Topbar موحّدة للبحث والإشعارات والحساب واختيار المشروع عند الحاجة.
- Page header موحّد: Breadcrumb، عنوان، وصف، وأفعال الصفحة.
- Cards وTables وModals وButtons وStatus Badges لها قواعد مشتركة.
- Purple للـ primary actions، Cyan للبيانات، Green للنجاح، Amber للتحذير، Red للخطر.
- Animations هادئة وتخدم فهم الحالة، ولا تُستخدم كبديل عن حالة Backend حقيقية.
- دعم Responsive Design وKeyboard Navigation وAccessible Contrast.

## 2. Visual Reference

الصورة المرفقة في ملف PDF هي لوحة تصميم تخيلية واحدة (Composite Design Board) تضم عدة شاشات من AegisTrace في Theme موحّد. بعض تفاصيل اللوحة تمثيلية وليست مواصفات تنفيذية أو بيانات فعلية.

## 3. Page-by-Page Specification

### 01. Landing Page / Hero

أول نقطة اتصال مع المستخدم قبل تسجيل الدخول.

- **Header:** شعار AegisTrace وروابط Product وPlatform وFeatures وDocumentation وPricing وزر Get Started.
- **Hero headline:** “From Code Understanding to Verified Security Remediation.”
- **Supporting copy:** تعريف مختصر يوضح أن المنصة تحلل الكود، تختبر السلوك، تثبت الثغرات، وتقترح الإصلاحات.
- **Primary CTA:** Start Free Assessment. **Secondary CTA:** Explore Platform.
- **Visual direction:** درع ثلاثي الأبعاد مضيء، حوله إشارات Code وNetwork وSecurity Signals.
- **Below the fold:** How It Works، Code-to-Behavior Security Twin، Seven AI Agents، Capabilities، Human Approval، Integrations، CTA نهائي وFooter.

### 02. Authentication

تسجيل الدخول وإنشاء الحساب واستعادة كلمة المرور.

- Email وPassword وRemember Me وForgot Password.
- Sign In وCreate Account، مع OAuth مثل GitHub فقط إذا كان مدعومًا فعليًا.
- بطاقة Login في المنتصف، خلفية Navy داكنة وخطوط Network بنفسجية هادئة.
- حالات واضحة للتحميل والأخطاء والتحقق من المدخلات.

### 03. Main Dashboard

نظرة شاملة على وضع المشاريع والفحوصات والنتائج.

- Header يتضمن Project Selector وDate Filter وNotifications وProfile.
- KPI cards: Total Projects، Total Scans، Confirmed Findings، Resolved Findings، Critical Findings.
- رسوم: Findings Over Time، Severity Distribution، Scan Activity، Project Security Overview.
- أقسام سفلية: Recent Scans، Recent Findings، Pending Approvals، Agent Activity.
- جميع الأرقام يجب أن تأتي من Backend؛ الأرقام في الصورة التخيلية ليست بيانات فعلية.

### 04. Projects Management

إدارة المشاريع ومصادر الكود وحالة كل مشروع.

- جدول أو Cards تعرض Project Name وRepository وProject Type وLast Scan وSecurity Status وFindings وTechnologies.
- Create Project وفتح Project Overview.
- صفحة تفاصيل المشروع تجمع إعداداته وسجل الفحوصات والنتائج المرتبطة به.

### 05. New Security Assessment

Wizard لإعداد فحص جديد قبل تشغيله.

- Step 1: اختيار مشروع أو إنشاء مشروع.
- Step 2: Source Configuration مثل GitHub Repository أو ZIP أو OpenAPI أو Authorized Staging URL.
- Step 3: Scope & Authorization لتحديد Hosts وEndpoints وعمليات الاختبار المسموح بها.
- Step 4: Credentials & Roles لحسابات الاختبار والأدوار المختلفة.
- Step 5: Review & Start لمراجعة الإعدادات قبل التشغيل.
- يجب إظهار Scope Summary والتحذيرات قبل أي Active Testing.

### 06. Agent Workspace

مراقبة تنفيذ الـ 7 Agents وتدفق المهام بينهم.

- عرض Orchestrator وCode Intelligence وRecon وVulnerability Research وDynamic Testing وVerification وRemediation.
- لكل Agent: Status، Current Task، Duration، Tools Used، Input/Output، Logs، Error Details.
- Workflow Timeline وCurrent Scan State وAgent Communication وExecution Logs.
- التمثيل البصري لا يعني أن التنفيذ خطي دائمًا؛ اعرض Dependencies وحالة التنفيذ الحقيقية من Backend.

### 07. Code Intelligence

إظهار كيف فهم النظام بنية المستودع ومسارات البيانات.

- Repository Structure، Routes & Controllers، Authentication Middleware، Authorization Logic.
- Database Models، Dependencies، Code Graph، Data Flow، Candidate Security Invariants.
- استخدام Graph View لربط API Route → Auth Middleware → Controller → ORM → Database.
- الضغط على Node يعرض الملف الأصلي والمعلومات المستخرجة منه.

### 08. Attack Surface

خريطة نقاط الدخول والـ API Endpoints داخل النطاق المصرح.

- عرض Endpoints وHTTP Methods ومتطلبات Authentication وAuthorization والParameters والRoles.
- Filters حسب Endpoint وMethod وAuthentication وRole وTechnology وRisk.
- ربط كل Endpoint بالـ Controller أو الملف المسؤول عنه متى توفرت العلاقة.

### 09. Vulnerability Findings

قائمة موحدة بالثغرات المكتشفة وحالة كل واحدة.

- أعمدة: Finding ID، Title، Severity، Confidence، Endpoint، Verification، Status.
- Filters وSearch وSorting حسب الخطورة والحالة والنوع.
- أنواع MVP الأساسية: Broken Access Control وIDOR وAuthentication/Authorization Flaws وBusiness Logic Vulnerabilities.

### 10. Finding Details & Evidence

صفحة تفصيلية تثبت لماذا اعتُبرت النتيجة ثغرة.

- Tabs: Overview، Root Cause، Evidence، Reproduction، Affected Code، Verification، Remediation.
- Evidence Viewer يعرض HTTP Request/Response وهوية المستخدم ومالك المورد وحالة قاعدة البيانات قبل وبعد.
- خطوات إعادة الإنتاج والملفات المتأثرة والاستنتاج المدعوم بالأدلة.
- يجب التمييز بين ملاحظة مشبوهة وثغرة Confirmed.

### 11. Verification Center

التحقق من صحة النتائج وتقليل الـ False Positives.

- Verification Status، Reproduction Attempts، Evidence Validation، False Positive Checks.
- Security Invariant Results وConfidence وVerification Timeline.
- حالات واضحة: Confirmed، Unconfirmed، Rejected، Needs More Evidence.
- لا تعتمد حالة Confirmed على استنتاج LLM وحده؛ يجب وجود دليل قابل للتحقق.

### 12. Remediation Center

مراجعة الإصلاح المقترح واختبار تأثيره.

- Vulnerability Summary وRoot Cause Analysis وProposed Patch وCode Diff Viewer وChanged Files.
- نتائج Unit Tests وIntegration Tests وOriginal Vulnerability Replay وRegression Tests.
- عرض Before/After والملفات المتغيرة.
- إنشاء الـ Patch في Isolated Branch أو Workspace، دون تعديل مباشر أو نشر تلقائي.

### 13. Human Approval Center

نقطة تحكم بشرية مستقلة قبل الإجراءات الحساسة.

- مؤشرات Pending Approvals وApproved وRejected وExpired.
- كل طلب يعرض Finding Summary وPatch Hash وTarget Branch وCode Diff وTest Results وSecurity Impact.
- القرارات: Approve Patch وReject وRequest Changes وDefer.
- الموافقة مرتبطة ببصمة النسخة المحددة من الـ Patch؛ أي تعديل بعدها يبطل الموافقة السابقة.
- صلاحيات التطبيق والدمج والنشر يجب أن تكون منفصلة ومتحققًا منها على الخادم.

### 14. Reports & Analytics

تقارير تنفيذية وتقنية قابلة للتصدير.

- Executive Security Report، Technical Vulnerability Report، Evidence Report، Remediation Report، Verification Report، Project Security History.
- PDF وJSON وCSV Export حسب ما يدعمه النظام.
- الرسوم والإحصاءات يجب أن تُشتق من نتائج فعلية مع إظهار الفترة ومصدر البيانات.

### 15. Skills Library

إدارة مهارات الأمن ومعرفة أي Agent يستخدمها.

- Installed/Available Skills، Metadata، Supported Vulnerability Classes، Compatible Agents.
- Skill Version وSource وLicense وLast Used.
- Search وFilters وSkill Details.
- تحميل المهارات المناسبة عند الحاجة عبر Skill Router بدل ضخ كل المهارات في كل Prompt.

### 16. Benchmarks

قياس الأداء ومقارنة أوضاع التحليل.

- مقارنة Static Only وStatic + Dynamic وFull AegisTrace.
- Metrics: Precision، Recall، False Positive Rate، Reproduction Rate، Patch Success Rate، Regression Rate، Time to Confirm، API Cost، Execution Time.
- يجب فصل الأهداف المتوقعة عن القياسات الفعلية وعدم اختلاق نتائج.

### 17. Settings & Integrations

إعدادات المنصة والتكاملات والصلاحيات.

- General، Security، API Keys، Integrations، AI Models، Agent Configuration، Notifications، Team & Roles، Audit Logs.
- تكاملات محتملة: Groq وGitHub وTavily وDocker وDatabase، مع إظهار حالة الاتصال الفعلية.
- لا تعرض الأسرار؛ استخدم إدارة آمنة للمفاتيح وصلاحيات دقيقة.

### 18. Supporting States & Screens

الشاشات المساندة المطلوبة لاكتمال التجربة.

- Project Overview وScan Details وScan History وAgent Run Details.
- Audit Logs وNotifications وTeam Management وProfile.
- Empty States وLoading Skeletons وError States و404 و500.
- الحفاظ على نفس الـ Design System في كل الحالات.

## 4. Recommended Sidebar Navigation

### Workspace
- Overview
- Projects
- Assessments
- Agent Workspace

### Security Intelligence
- Code Intelligence
- Attack Surface
- Findings
- Verification Center

### Remediation
- Remediation
- Human Approvals
- Reports

### Platform
- Skills Library
- Benchmarks
- Settings

## 5. Recommended Design & Delivery Order

1. **Core Experience:** Landing Page، Authentication، Dashboard، Projects، New Assessment.
2. **Security Intelligence:** Agent Workspace، Code Intelligence، Attack Surface، Findings، Evidence.
3. **Remediation:** Verification Center، Remediation Center، Human Approval Center.
4. **Platform Management:** Reports، Skills Library، Benchmarks، Settings، Audit Logs.
5. **Polish:** Responsive Design، Loading States، Error States، Accessibility، Motion.

## 6. Product Design Principles

- لا تُظهر أرقامًا أو نتائج تجريبية على أنها بيانات حقيقية.
- كل Status أو Metric يجب أن يرتبط بمصدر بيانات واضح.
- لا تجعل Agent Workspace مجرد Animation؛ اعرض حالة التنفيذ الفعلية.
- Evidence هي مركز الثقة في Finding Details.
- Approval يجب أن يكون Server-enforced ومربوطًا ببصمة الـ Patch.
- لا تخلط بين إنشاء Patch في Sandbox وبين تطبيقه على Branch مشترك أو نشره.
- حافظ على الاتساق البصري دون التضحية بوضوح المعلومات وكثافتها.

## 7. Important Scope Note

هذا المستند مواصفة تصميم وتصور للواجهة النهائية، وليس طلبًا لإعادة بناء المشروع الحالي. الـ Dummy Web الحالي خارج نطاق التقييم البصري. يجب الحفاظ على Backend والـ APIs والـ Architecture الحالية، وربط الواجهة النهائية بها وفق العقود الموجودة بعد التحقق منها.
