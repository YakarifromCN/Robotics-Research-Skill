# 基线复现

基线选择必须记录代码 commit、配置 hash、环境收据、命令、任务/数据身份、随机种子、
预期指标、容差和必需工件。自主改进声明要求基线状态为 `REPRODUCED`；偏差必须取得
用户明确批准。恢复流程可以修复入口、指标版本、随机种子或环境问题，但不能为了制造
复现结果而改变算法。

# English

# Baseline Reproduction

Baseline selection records the code commit, config hash, environment receipt, command,
task/data identity, seeds, expected metrics, tolerance, and required artifacts.
Autonomous improvement claims require `REPRODUCED`; variance requires explicit user
approval. Recovery may repair an entry point, metric version, seed, or environment
problem, but may not change the algorithm in order to manufacture reproduction.
