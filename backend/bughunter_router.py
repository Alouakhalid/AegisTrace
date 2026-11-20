"""Claude-BugHunter Skills Retrieval and Routing Engine for AegisTrace.
Discovers skills in skills/Claude-BugHunter/skills, indexes their methodologies,
and routes relevant skills to the 7 agents based on selected assessment categories.
"""

import os
import re
from typing import Dict, Any, List, Optional

WORKSPACE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS_DIR = os.path.join(WORKSPACE_ROOT, "skills", "Claude-BugHunter", "skills")

CATEGORY_SKILL_MAP: Dict[str, List[str]] = {
    "idor_access_control": [
        "hunt-idor",
        "hunt-auth-bypass"
    ],
    "authentication": [
        "hunt-auth-bypass",
        "hunt-session",
        "hunt-jwt-crypto",
        "hunt-oauth"
    ],
    "injection": [
        "hunt-sqli",
        "hunt-rce",
        "hunt-nosqli",
        "hunt-ssti",
        "hunt-html-injection"
    ],
    "business_logic": [
        "hunt-business-logic",
        "hunt-race-condition",
        "hunt-exceptional-conditions"
    ],
    "data_security": [
        "hunt-deserialization",
        "hunt-source-leak",
        "hunt-file-upload"
    ],
    "api_security": [
        "hunt-api-misconfig",
        "hunt-cors",
        "hunt-graphql",
        "hunt-spa-api"
    ],
    "dependencies": [
        "supply-chain-attack-recon",
        "triage-validation"
    ],
    "ai_security": [
        "hunt-llm-ai",
        "hunt-rag-vector"
    ]
}

CATEGORY_METADATA = [
    {
        "id": "idor_access_control",
        "name": "Access Control & IDOR",
        "icon": "shield-check",
        "description": "Broken Object Level Authorization (BOLA), horizontal/vertical privilege escalation, and missing tenancy checks."
    },
    {
        "id": "authentication",
        "name": "Authentication & Session",
        "icon": "key",
        "description": "Auth bypass flaws, weak session token handling, JWT cryptographic pitfalls, and OAuth flaws."
    },
    {
        "id": "injection",
        "name": "Injection Flaws",
        "icon": "terminal",
        "description": "SQL injection, remote command execution, NoSQL injection, and server-side template injection."
    },
    {
        "id": "business_logic",
        "name": "Business Logic & State",
        "icon": "workflow",
        "description": "Race conditions, inconsistent state transitions, price/parameter tampering, and workflow bypasses."
    },
    {
        "id": "data_security",
        "name": "Data Security & Deserialization",
        "icon": "database",
        "description": "Insecure Python pickle/joblib deserialization, source code leaks, and unauthenticated file handling."
    },
    {
        "id": "api_security",
        "name": "API & Interface Security",
        "icon": "network",
        "description": "Excessive data exposure, CORS misconfiguration, GraphQL introspection vulnerabilities, and shadow endpoints."
    },
    {
        "id": "dependencies",
        "name": "Dependencies & Threat Intel",
        "icon": "layers",
        "description": "Vulnerable third-party libraries correlated in real-time with Tavily live CVE threat intelligence."
    },
    {
        "id": "ai_security",
        "name": "AI & LLM Model Security",
        "icon": "cpu",
        "description": "Prompt injection vectors, unsafe RAG document loading, and untrusted model weight deserialization."
    }
]

class BugHunterSkillRouter:
    """Indexes and routes Claude-BugHunter methodology skills to the 7 agents."""

    def __init__(self, skills_root: Optional[str] = None):
        self.skills_root = skills_root or SKILLS_DIR
        self._skills_cache: Dict[str, Dict[str, Any]] = {}
        self._index_skills()

    def _index_skills(self) -> None:
        """Indexes all available skill folders and parses their metadata."""
        if not os.path.isdir(self.skills_root):
            return

        for entry in os.listdir(self.skills_root):
            entry_path = os.path.join(self.skills_root, entry)
            if not os.path.isdir(entry_path):
                continue

            skill_md = os.path.join(entry_path, "SKILL.md")
            desc = "Security hunting skill methodology"
            has_doc = os.path.isfile(skill_md)

            if has_doc:
                try:
                    with open(skill_md, "r", encoding="utf-8", errors="ignore") as fh:
                        raw = fh.read()
                        yaml_match = re.search(r"^description:\s*(.+)$", raw, re.MULTILINE)
                        if yaml_match:
                            desc = yaml_match.group(1).strip().strip('"')
                        else:
                            for line in raw.splitlines()[:15]:
                                if line.strip() and not line.startswith("#") and not line.startswith("---"):
                                    desc = line.strip()[:140]
                                    break
                except Exception:
                    pass

            self._skills_cache[entry] = {
                "skill_name": entry,
                "path": entry_path,
                "has_doc": has_doc,
                "description": desc
            }

    def get_all_skills(self) -> List[Dict[str, Any]]:
        """Returns all discovered BugHunter skills."""
        return list(self._skills_cache.values())

    def get_available_categories(self) -> List[Dict[str, Any]]:
        """Returns metadata for all supported assessment categories."""
        return CATEGORY_METADATA

    def route_skills(self, selected_categories: List[str], detected_frameworks: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Retrieves and packages only the skills relevant to the user's chosen categories.
        Enforces strict scope rules: unselected categories contribute zero skills.
        """
        matched_names = set()
        for cat in selected_categories:
            skill_list = CATEGORY_SKILL_MAP.get(cat, [])
            for s in skill_list:
                matched_names.add(s)

        if detected_frameworks:
            for fw in detected_frameworks:
                fw_lower = fw.lower()
                if "fastapi" in fw_lower or "flask" in fw_lower:
                    if "api_security" in selected_categories:
                        matched_names.add("hunt-api-misconfig")
                if "scikit-learn" in fw_lower or "torch" in fw_lower or "pandas" in fw_lower:
                    if "data_security" in selected_categories:
                        matched_names.add("hunt-deserialization")

        results = []
        for name in sorted(matched_names):
            if name in self._skills_cache:
                results.append(self._skills_cache[name])
            else:
                results.append({
                    "skill_name": name,
                    "path": os.path.join(self.skills_root, name),
                    "has_doc": False,
                    "description": f"Automated methodology for {name}"
                })

        return results

    def load_skill_content(self, skill_name: str) -> Optional[str]:
        """Loads the full markdown methodology instructions of a specific skill."""
        skill_info = self._skills_cache.get(skill_name)
        if not skill_info or not skill_info.get("has_doc"):
            candidate = os.path.join(self.skills_root, skill_name, "SKILL.md")
            if os.path.isfile(candidate):
                try:
                    with open(candidate, "r", encoding="utf-8") as fh:
                        return fh.read()
                except Exception:
                    return None
            return None

        skill_md = os.path.join(skill_info["path"], "SKILL.md")
        try:
            with open(skill_md, "r", encoding="utf-8") as fh:
                return fh.read()
        except Exception:
            return None
