#!/usr/bin/env python3
"""发现稿件图与评审范围。 / Discover the manuscript graph and review scope."""
from __future__ import annotations
import argparse, json, re, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
IGNORE_DIRS={".git","build","output","_minted-","reviews","review","old","archive","previous","submitted"}
EXCLUDED_NAMES=re.compile(r"^(response|letter|review|old|draft|slides|presentation)",re.I)
FIG_EXT={".pdf",".png",".eps",".jpg",".jpeg",".svg"}
def ignored(path:Path,root:Path)->bool:
    rel=path.resolve().relative_to(root.resolve())
    return any(part.lower() in IGNORE_DIRS or part.lower().startswith("_minted-") for part in rel.parts)
def text(path:Path)->str:
    return path.read_text(encoding="utf-8",errors="replace")
def inside(path:Path,root:Path)->bool:
    try:path.resolve().relative_to(root.resolve());return True
    except ValueError:return False
def include_names(source:str):
    return re.findall(r"\\(?:input|include|subfile)\s*\{([^}]+)\}",re.sub(r"(?m)^\s*%.*$","",source))
def resolve_ref(raw:str,base:Path,root:Path):
    raw=raw.strip(); candidates=[base/raw]
    if Path(raw).suffix=="":candidates.append(base/(raw+".tex"))
    for candidate in candidates:
        candidate=candidate.resolve()
        if candidate.is_file() and inside(candidate,root) and not ignored(candidate,root):return candidate
    return None
def include_graph(main:Path,root:Path):
    found=[];seen=set();queue=[main]
    while queue:
        current=queue.pop(0)
        if current in seen:continue
        seen.add(current);found.append(current)
        if current.suffix.lower()==".tex":
            for raw in include_names(text(current)):
                child=resolve_ref(raw,current.parent,root)
                if child is not None:queue.append(child)
    return found
def locate_main(root:Path,explicit:str|None):
    if explicit:
        path=(root/explicit).resolve() if not Path(explicit).is_absolute() else Path(explicit).resolve()
        if not path.is_file() or not inside(path,root):raise ValueError("explicit main file must be an existing file inside paper root")
        return path
    if root.is_file():return root.resolve()
    tex=[p for p in root.rglob("*.tex") if not ignored(p,root) and not EXCLUDED_NAMES.match(p.name)]
    candidates=[p for p in tex if "\\documentclass" in text(p) or "\\begin{document}" in text(p)]
    if len(candidates)==1:return candidates[0].resolve()
    if len(candidates)>1:
        scored=sorted(((len(include_names(text(p))),p) for p in candidates),reverse=True)
        if len(scored)==1 or scored[0][0]>scored[1][0]:return scored[0][1].resolve()
        raise ValueError("multiple LaTeX main files are ambiguous; pass --main")
    docs=[p for p in root.rglob("*.md") if not ignored(p,root) and not EXCLUDED_NAMES.match(p.name)]
    if len(docs)==1:return docs[0].resolve()
    raise ValueError("could not discover one manuscript main file; pass --main")
def referenced_figures(files:list[Path],root:Path):
    refs=[]
    for path in files:
        refs.extend(re.findall(r"\\includegraphics(?:\[[^]]*\])?\s*\{([^}]+)\}",text(path)))
    output=[]
    for raw in refs:
        raw_path=Path(raw); bases=[root/raw_path]
        for file in files:bases.append(file.parent/raw_path)
        candidates=[]
        for base in bases:
            candidates.append(base)
            if base.suffix=="":candidates.extend(base.with_suffix(ext) for ext in FIG_EXT)
        for candidate in candidates:
            candidate=candidate.resolve()
            if candidate.is_file() and inside(candidate,root) and candidate not in output:output.append(candidate)
    return output
def title_abstract(main:Path):
    source=text(main)
    title_match=re.search(r"\\title\s*\{([^}]*)\}",source,re.S)
    abstract_match=re.search(r"\\begin\{abstract\}(.*?)\\end\{abstract\}",source,re.S)
    if main.suffix.lower()==".md":
        lines=source.splitlines(); title=next((line.lstrip("# ").strip() for line in lines if line.startswith("#")),None); abstract=None
    else:title=title_match.group(1).strip() if title_match else None;abstract=abstract_match.group(1).strip() if abstract_match else None
    return title,abstract
def main():
    parser=argparse.ArgumentParser();parser.add_argument("paper_root",type=Path);parser.add_argument("--main");parser.add_argument("--output",required=True);args=parser.parse_args()
    root=args.paper_root.resolve();root=root.parent if root.is_file() else root;main_file=locate_main(root,args.main);files=include_graph(main_file,root);figures=referenced_figures(files,root);tables=[p for p in files if p.name.lower().find("table")>=0 or any(part.lower() in {"table","tables"} for part in p.parts)]
    title,abstract=title_abstract(main_file);all_allowed=[]
    for p in files+figures+tables:
        if p not in all_allowed:all_allowed.append(p)
    cjk=len(re.findall(r"[\u3400-\u9fff]",''.join(text(p) for p in files)));latin=len(re.findall(r"[A-Za-z]",''.join(text(p) for p in files)))
    context={"schema_version":"robotics-review-context.v1","review_id":"REV-001","mode":"full","created_at":None,"paper":{"root":str(root),"main_file":str(main_file),"include_graph":[str(p) for p in files],"figure_files":[str(p) for p in figures],"table_files":[str(p) for p in tables],"supplementary_files":[],"language":"zh-en" if cjk and latin else ("zh" if cjk else "en"),"title":title,"abstract":abstract},"scope_guard":{"allowed_files":[str(p) for p in all_allowed],"ignored_patterns":["**/reviews/**","**/old/**","**/archive/**","**/*response*","**/*letter*","**/README*"],"untrusted_materials":True},"target_fit_snapshot":{"target":None,"article_type":None,"official_sources":[],"checked_at":None,"expires_at":None},"scientific_contract":{"research_card":None,"experiment_contract":None,"result_bundle":None,"claim_ledger":None},"claim_shape":None,"domain_packs":[],"reviewer_configuration":[],"status":"DISCOVERED"}
    Path(args.output).write_text(json.dumps(context,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
if __name__=="__main__":main()
