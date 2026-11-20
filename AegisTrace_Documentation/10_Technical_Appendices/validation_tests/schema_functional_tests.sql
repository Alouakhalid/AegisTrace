\set ON_ERROR_STOP off
INSERT INTO users VALUES ('usr_0192f19e','a@x.io','Analyst','analyst','sub1',now(),NULL),('usr_0192f19f','r@x.io','Reviewer','reviewer','sub2',now(),NULL);
INSERT INTO projects(id,owner_id,name) VALUES ('prj_0192f1a0','usr_0192f19e','ShopLite');
INSERT INTO repositories(id,project_id,source_type,url) VALUES ('rep_0192f1a1','prj_0192f1a0','github','https://github.com/example-org/shoplite-api');
INSERT INTO engagements(id,project_id,name,assessment_mode,environment,status,attested_by,attested_at) VALUES ('eng_0192f1b4','prj_0192f1a0','E1','full','sandbox','active','usr_0192f19e',now());
INSERT INTO scope_manifests(id,engagement_id,version,manifest,manifest_sha256,valid,created_by) VALUES ('scm_0192f1b9','eng_0192f1b4',1,'{"allowed_hosts":["shoplite-app"]}','ab',true,'usr_0192f19e');
INSERT INTO scans(id,engagement_id,scope_manifest_id,repository_id,commit_sha,correlation_id,requested_by) VALUES ('scn_0192f1c9','eng_0192f1b4','scm_0192f1b9','rep_0192f1a1','a1b2c3d4e5f6','cor_0192f230','usr_0192f19e');
INSERT INTO repositories_analysis(id,scan_id,repository_id,commit_sha,files_analyzed) VALUES ('ran_0192f1d0','scn_0192f1c9','rep_0192f1a1','a1b2c3d4e5f6',86);
INSERT INTO code_nodes(analysis_id,kind,name,file,line) VALUES ('ran_0192f1d0','route','PATCH /api/v1/orders/{order_id}','app/routes/orders.py',58);
INSERT INTO security_invariants(id,project_id,analysis_id,statement,kind,source,confidence) VALUES ('inv_0192f1e0','prj_0192f1a0','ran_0192f1d0','Order owner only','ownership','code',0.86);
INSERT INTO endpoints(id,scan_id,method,path,source) VALUES ('ep_0192f1f0','scn_0192f1c9','PATCH','/api/v1/orders/{order_id}','openapi');
INSERT INTO vulnerability_hypotheses(id,scan_id,endpoint_id,invariant_id,category,title,rationale,priority) VALUES ('hyp_0192f200','scn_0192f1c9','ep_0192f1f0','inv_0192f1e0','idor','t','r',1);
INSERT INTO evidence(id,scan_id,kind,content_ref,content_sha256) VALUES ('evd_0192f21b','scn_0192f1c9','state_diff','obj://x',repeat('a',64));
\echo '--- T1 confirmed finding without severity must FAIL'
INSERT INTO findings(id,scan_id,hypothesis_id,endpoint_id,invariant_id,verdict,confidence,runs,reproduced,invariant_violated) VALUES ('fnd_0192f201','scn_0192f1c9','hyp_0192f200','ep_0192f1f0','inv_0192f1e0','confirmed',0.9,3,3,true);
\echo '--- T2 valid confirmed finding must SUCCEED'
INSERT INTO findings(id,scan_id,hypothesis_id,endpoint_id,invariant_id,verdict,confidence,severity,runs,reproduced,invariant_violated) VALUES ('fnd_0192f200','scn_0192f1c9','hyp_0192f200','ep_0192f1f0','inv_0192f1e0','confirmed',0.97,'medium',3,3,true);
INSERT INTO finding_evidence VALUES ('fnd_0192f200','evd_0192f21b','state_diff');
\echo '--- T3 UPDATE evidence must FAIL (append-only)'
UPDATE evidence SET redacted=false WHERE id='evd_0192f21b';
\echo '--- T4 DELETE audit log must FAIL'
INSERT INTO audit_logs(actor_type,actor_id,action,allowed) VALUES ('system','scope_gate','http_request',false);
DELETE FROM audit_logs;
\echo '--- T5 bad id prefix must FAIL'
INSERT INTO projects(id,owner_id,name) VALUES ('xyz_123','usr_0192f19e','bad');
\echo '--- T6 paired_identity with one identity must FAIL'
INSERT INTO test_cases(id,hypothesis_id,method,steps,identities,expected_secure_behavior) VALUES ('tpl_0192f300','hyp_0192f200','paired_identity','[]',ARRAY['id_buyer_a'],'x');
\echo '--- T7 approval decided without reviewer must FAIL'
INSERT INTO patches(id,finding_id,attempt,branch,diff_ref,diff_sha256,changed_files,root_cause) VALUES ('pat_0192f500','fnd_0192f200',1,'fix/x','p.diff','h',ARRAY['a.py'],'{}');
INSERT INTO approvals(id,patch_id,decision) VALUES ('apr_0192f600','pat_0192f500','approved');
\echo '--- T8 pending approval must SUCCEED'
INSERT INTO approvals(id,patch_id) VALUES ('apr_0192f601','pat_0192f500');
\echo '--- T9 pgvector hybrid retrieval'
INSERT INTO skills(id,name,source_repo,source_commit,path,description) VALUES ('skl_0192f700','hunt-idor','https://github.com/elementalsouls/Claude-BugHunter','64410ed','skills/hunt-idor/SKILL.md','IDOR');
INSERT INTO skill_metadata(id,skill_id,chunk_index,heading,content_excerpt,token_count,vuln_categories,keywords,embedding)
SELECT 'skm_0192f7'||lpad(g::text,2,'0'),'skl_0192f700',g,'h'||g,'order id object reference check '||g,40,ARRAY['idor'],to_tsvector('english','order id object reference ownership check '||g),
       ('['||array_to_string(ARRAY(SELECT round(random()::numeric,3) FROM generate_series(1,384)),',')||']')::vector FROM generate_series(1,20) g;
WITH kw AS (SELECT id, ts_rank(keywords, plainto_tsquery('english','order ownership')) s FROM skill_metadata WHERE vuln_categories @> ARRAY['idor'] AND keywords @@ plainto_tsquery('english','order ownership') LIMIT 20),
 vec AS (SELECT id, 1-(embedding <=> (SELECT embedding FROM skill_metadata WHERE chunk_index=3)) s FROM skill_metadata ORDER BY embedding <=> (SELECT embedding FROM skill_metadata WHERE chunk_index=3) LIMIT 20)
SELECT id, round(sum(1.0/(60+rank))::numeric,4) rrf FROM (SELECT id,row_number() OVER (ORDER BY s DESC) rank FROM kw UNION ALL SELECT id,row_number() OVER (ORDER BY s DESC) FROM vec) t GROUP BY id ORDER BY rrf DESC LIMIT 3;
\echo '--- T10 dedupe memory item must FAIL on duplicate'
INSERT INTO memory_items(id,project_id,memory_type,key,content,content_sha256) VALUES ('mem_0192f800','prj_0192f1a0','project','routes','c','h1');
INSERT INTO memory_items(id,project_id,memory_type,key,content,content_sha256) VALUES ('mem_0192f801','prj_0192f1a0','project','routes','c','h1');
