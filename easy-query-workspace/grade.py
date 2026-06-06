import json, re, os

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "iteration-1")

TIMING = {
    "eval-0-kotlin-entity-and-query": {"with_skill": (35024,59001), "without_skill": (25432,34141)},
    "eval-1-kotlin-ksp-setup":        {"with_skill": (32081,53689), "without_skill": (27247,63490)},
    "eval-2-java-spring-crud-service":{"with_skill": (39536,69973), "without_skill": (27508,62367)},
    "eval-3-dynamic-filter-pagination":{"with_skill": (34227,75169), "without_skill": (27583,62976)},
    "eval-4-transactional-multi-write":{"with_skill": (36465,67043), "without_skill": (27992,63622)},
    "eval-5-write-unit-test":         {"with_skill": (35871,68470), "without_skill": (27735,67669)},
    "eval-6-relation-query-include":  {"with_skill": (33533,60788), "without_skill": (25937,42630)},
}

PROMPTS = {
    "eval-0-kotlin-entity-and-query": "Kotlin: define Topic entity + query stars>100 desc createTime",
    "eval-1-kotlin-ksp-setup": "Kotlin Gradle easy-query setup; kapt or ksp?",
    "eval-2-java-spring-crud-service": "Spring Boot UserService CRUD + application.yml",
    "eval-3-dynamic-filter-pagination": "Java optional-filter paginated Order query",
    "eval-4-transactional-multi-write": "Pure Java order+balance in one transaction",
    "eval-5-write-unit-test": "Unit test without external DB for stars>100",
    "eval-6-relation-query-include": "One-to-many SysUser->BankCard eager load, no N+1",
}

FORBIDDEN = r"QueryWrapper|LambdaQueryWrapper|BaseMapper|ServiceImpl|CriteriaBuilder|EntityManager|@Entity\b|createCriteria"

def has(t, pat): return re.search(pat, t, re.I) is not None
def hasnt(t, pat): return re.search(pat, t, re.I) is None

def assertions(eid, t):
    A=[]
    nf = ("no forbidden ORM symbols (MyBatis/JPA/QueryDSL)", hasnt(t, FORBIDDEN))
    if eid=="eval-0-kotlin-entity-and-query":
        A=[("entity implements ProxyEntityAvailable", has(t,"ProxyEntityAvailable")),
           ("@Table and @EntityProxy present", has(t,"@Table") and has(t,"@EntityProxy")),
           ("Kotlin trailing-lambda where { }", has(t,r"where\s*\{")),
           ("uses Type::class.java", has(t,r"::class\.java")),
           ("stars filter via .stars().gt", has(t,r"stars\(\)\.gt")), nf]
    elif eid=="eval-1-kotlin-ksp-setup":
        A=[("uses KSP processor (sql-ksp-processor)", has(t,"sql-ksp-processor") or has(t,r"ksp\(")),
           ("KSP gradle plugin com.google.devtools.ksp", has(t,r"com\.google\.devtools\.ksp")),
           ("answers kapt question by choosing KSP (not kapt)", has(t,"ksp") and has(t,r"kapt")),
           ("adds build/generated/ksp srcDir", has(t,r"generated/ksp")),
           ("init via EasyQueryBootstrapper + DefaultEasyEntityQuery", has(t,"EasyQueryBootstrapper") and has(t,"DefaultEasyEntityQuery")), nf]
    elif eid=="eval-2-java-spring-crud-service":
        A=[("injects EasyEntityQuery", has(t,"EasyEntityQuery")),
           ("unique lookup uses singleOrNull", has(t,"singleOrNull")),
           ("application.yml easy-query.enable", has(t,"enable") and has(t,"easy-query")),
           ("insert via insertable(...).executeRows", has(t,"insertable") and has(t,"executeRows")),
           ("update via updatable+setColumns", has(t,"updatable") and has(t,"setColumns")), nf]
    elif eid=="eval-3-dynamic-filter-pagination":
        A=[("gated dynamic conditions (cond,value overload)", (has(t,"isNotBlank") or has(t,r"!=\s*null") or has(t,"StringUtil")) and has(t,r"\.like\(")),
           ("pagination via toPageResult", has(t,"toPageResult")),
           ("stable order with id tiebreaker", has(t,"orderBy") and has(t,r"id\(\)\.(asc|desc)")),
           ("reads getData/getTotal", has(t,"getData") or has(t,"getTotal")),
           ("notes deterministic/stable pagination ordering", has(t,r"稳定|stable|确定性|tie-?break|tiebreaker")), nf]
    elif eid=="eval-4-transactional-multi-write":
        A=[("beginTransaction used", has(t,"beginTransaction")),
           ("commit called", has(t,r"\.commit\(")),
           ("balance decrement in SQL", has(t,"decrement")),
           ("atomic guard (executeRows(1 or balance>=)", has(t,r"executeRows\(\s*1") or has(t,r"balance\(\)\.ge") or has(t,r"balance\s*>=")),
           ("auto-rollback on exception/missing commit described", has(t,r"rollback|回滚")), nf]
    elif eid=="eval-5-write-unit-test":
        A=[("H2 in-memory datasource", has(t,r"h2:mem")),
           ("H2DatabaseConfiguration dialect", has(t,"H2DatabaseConfiguration")),
           ("code-first syncTableCommand", has(t,"syncTableCommand")),
           ("DB_CLOSE_DELAY keep-alive", has(t,"DB_CLOSE_DELAY")),
           ("behavior assertion (assertEquals/assertTrue)", has(t,r"assert(Equals|True|That|NotNull)")), nf]
    elif eid=="eval-6-relation-query-include":
        A=[("@Navigate OneToMany", has(t,"@Navigate") and has(t,"OneToMany")),
           ("eager load via .include(", has(t,r"\.include\(")),
           ("explains avoiding N+1", has(t,r"N\+1")),
           ("entities implement ProxyEntityAvailable", has(t,"ProxyEntityAvailable")), nf]
    return A

for eid in TIMING:
    for cfg in ("with_skill","without_skill"):
        d = os.path.join(ROOT, eid, cfg)
        ans = os.path.join(d,"outputs","answer.md")
        t = open(ans,encoding="utf-8").read() if os.path.exists(ans) else ""
        tok,dur = TIMING[eid][cfg]
        timing={"total_tokens":tok,"duration_ms":dur,"total_duration_seconds":round(dur/1000,1)}
        exps=[{"text":txt,"passed":bool(p),"evidence":("matched" if p else "not found in answer.md")}
              for txt,p in assertions(eid,t)]
        passed=sum(1 for e in exps if e["passed"]); total=len(exps)
        grading={"run_id":f"{eid}-{cfg}",
                 "summary":{"pass_rate":round(passed/total,4) if total else 0.0,
                            "passed":passed,"failed":total-passed,"total":total},
                 "timing":timing,"expectations":exps}
        # viewer reads grading/timing at the config dir; aggregator needs a run-1/ subdir
        json.dump(timing, open(os.path.join(d,"timing.json"),"w"))
        json.dump(grading, open(os.path.join(d,"grading.json"),"w"),ensure_ascii=False,indent=2)
        run1=os.path.join(d,"run-1"); os.makedirs(run1,exist_ok=True)
        json.dump(timing, open(os.path.join(run1,"timing.json"),"w"))
        json.dump(grading, open(os.path.join(run1,"grading.json"),"w"),ensure_ascii=False,indent=2)
    # eval_metadata.json
    md={"eval_id":eid,"eval_name":eid,"prompt":PROMPTS[eid],
        "assertions":[a["text"] for a in [{"text":x[0]} for x in assertions(eid,"")]]}
    json.dump(md,open(os.path.join(ROOT,eid,"eval_metadata.json"),"w"),ensure_ascii=False,indent=2)

# summary
print("eval | with_skill | baseline")
for eid in TIMING:
    g=lambda c: json.load(open(os.path.join(ROOT,eid,c,"grading.json")))["summary"]
    w,b=g("with_skill"),g("without_skill")
    print(f"{eid:34} {w['passed']}/{w['total']}      {b['passed']}/{b['total']}")
