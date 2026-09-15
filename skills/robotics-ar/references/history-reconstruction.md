# 历史重建

只追加的 trial ledger 会导入过去的 `robotics-ar` 工件、报告、交接文档、任务文件、
本地结果文件、日志和用户提供的记录。没有代码/配置/环境绑定的结果不能升级为
`VERIFIED`。bug 和环境失败应标记为 `INVALID`，而不是科学上的负结果；缺失 provenance
仍保持为 `UNKNOWN` 或 `UNREPRODUCIBLE`。

Do-Not-Repeat Registry 保存实质性 fingerprint 及其原因。重试必须记录实质差异，不能
只重命名一个参数。

# English

# History Reconstruction

The append-only trial ledger imports prior `robotics-ar` artifacts, reports,
handoffs, task files, local result files, logs, and user-supplied records. A result
without code/config/environment binding cannot be upgraded to `VERIFIED`. Bugs and
environment failures are `INVALID` rather than scientific negative results; missing
provenance remains `UNKNOWN` or `UNREPRODUCIBLE`.

The Do-Not-Repeat Registry stores substantive fingerprints and a reason. A retry needs
a recorded material difference, not a cosmetic parameter rename.
