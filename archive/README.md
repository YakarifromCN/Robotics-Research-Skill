# 历史归档

`archive/legacy-v1/` 保存已经被当前运行链替代、但对迁移或来源追溯仍有价值的 v1 文件。
其中包括旧 venue catalog、旧子流形分析入口、旧 ResearchStudio signature/cluster/axis
流水线、一次性 catalog 迁移器，以及已由当前 Skill 本地 packs/运行说明覆盖的早期参考文档。

归档契约：

- 正常路由、Skill 文档、安装器和默认测试不得导入 `archive/`；
- staged 安装永远不复制 `archive/`；
- 归档代码按历史状态保存，不承诺能在当前 API 上直接执行；
- 当前代码若需要归档文件，说明依赖闭包发生回退，发布检查应失败；
- 没有追溯或迁移价值的重复 wrapper、动态 `.source` 快照和孤立生成物直接删除，由 Git 历史保留。

当前 schema 使用 `v1` 后缀不等于归档。例如
`robotics-research-runtime.v1.json`、`robotics-submanifold.v1.json` 和
`researchstudio-pattern-cards.v1.json` 仍是当前运行工件，因为没有替代 schema。

---

# English

## Historical archive

`archive/legacy-v1/` retains v1 files that have been superseded by the current
runtime but still have migration or provenance value. It includes the old
venue catalog, old submanifold analysis entry point, the old ResearchStudio
signature/cluster/axis pipeline, the one-time catalog migrator, and early
reference documents superseded by current Skill-local packs and runtime docs.

Archive contract:

- normal routing, Skill documentation, installers, and default tests must not
  import `archive/`;
- staged installations never copy `archive/`;
- archived code is preserved in historical form and is not guaranteed to run
  against current APIs;
- any current-code dependency on an archived file is a runtime-closure
  regression and must fail release validation;
- duplicate wrappers, dynamic `.source` snapshots, and orphaned generated
  files without provenance value are deleted and remain recoverable through
  Git history.

A current schema with a `v1` suffix is not automatically archived. For
example, `robotics-research-runtime.v1.json`,
`robotics-submanifold.v1.json`, and `researchstudio-pattern-cards.v1.json` are
still active runtime artifacts because no replacement schema exists.
