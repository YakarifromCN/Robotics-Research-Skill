# 历史归档

## 中文

`legacy-v1/` 保存已被当前实现替代、仍有迁移或来源追溯价值的文件，包括旧载体目录、早期分析流水线和参考文档。归档按历史状态保留，不承诺兼容当前 API。

普通 Skill、安装器和默认测试不依赖归档；发布运行包不复制它。需要追溯旧行为时显式查阅，不把归档加入运行搜索路径。没有追溯价值的重复文件可由 Git 历史保留。

当前文件带 `v1` 后缀不代表过时。例如 runtime、子流形模型和模式卡仍使用有效的 v1 schema；当前依赖见 [corpus/README.md](../corpus/README.md)。

# English

## Historical archive

`legacy-v1/` retains superseded files with migration or provenance value, including old venue catalogs, analysis pipelines and reference documents. They remain in historical form and may not work with current APIs.

Normal Skills, installers and default tests do not depend on this archive; runtime releases omit it. Consult it explicitly when tracing old behavior, without adding it to runtime search paths. Git history can retain duplicates that no longer have an active archival purpose.

A `v1` suffix does not imply obsolescence. The runtime, manifold model and pattern cards still use active v1 schemas. See [current dependencies](../corpus/README.md).
