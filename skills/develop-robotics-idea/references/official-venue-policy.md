# 中文版

## 轻量官方目标载体政策层

仅在共同机器人研究流形上形成科学构想后使用本文件。它不维护固定目标池，也不编码录用模型或隔离工作流。每次只针对用户当前指定的会议、期刊或其他载体，检索实时一手来源。

### 检索规则

打开目标载体当前官方主页、征稿通知与作者指南。为每个请求字段记录精确访问日期和来源 URL：

- 当前范围、文章类型与目标读者；
- 截止时间与时区；
- 页数或字数限制，以及参考文献是否计入；
- 匿名政策；
- 既往发表与一稿多投政策；
- 补充材料、视频、研究产物与外部链接政策；
- rebuttal 或修改通道；
- 期刊转会议展示选项；
- 模板、投稿系统与最终上传要求。

不要从记忆或名称猜测官网地址；使用搜索找到目标载体的官方组织、学会、出版商或会议域名，再进入当前周期页面。年度会议规则与期刊政策会变化，旧快照不能当作当前规则。

### 与证据画像的边界

当前官方范围、文章类型与读者特征属于第 4 步的 `target_context`，可与用户目标共同提取 `target_vector=T`。载体名称本身和声望假设不能直接设置任何布尔位、轴下限或深度模块，也不得保存载体到向量的固定映射。

第 8 步只处理格式与实时政策包装，不能静默覆盖已锁定画像。如果新核验的当前范围或读者语境要求实质重校准，返回第 4 步，创建带 `supersedes` 的新 `research_intensity` 版本并重新执行十项审计。

`target_outside_claim` 只暴露目标语境超出主张的部分，不得用于膨胀证据负担、实验计划或主张；`claim_outside_target` 只暴露适配欠缺，不得削弱科学要求。

### 字段状态

将每个政策字段设置为：

- `VERIFIED`：当前官方来源给出单一可定位值；
- `RULE_CONFLICT`：两个当前官方来源冲突，必须保留两组值与 URL；
- `RULE_NOT_VERIFIED`：没有找到足够的一手证据。

冲突或缺失时不得猜测。

### 快照结构

```json
{
  "venue": "用户指定目标载体 / user-specified target outlet",
  "cycle": "YYYY",
  "verified_at": "YYYY-MM-DD",
  "official_source_urls": ["https://..."],
  "fields": {
    "page_limit": {
      "status": "VERIFIED",
      "value": "逐字规范化后的值 / verbatim-normalized value",
      "source_urls": ["https://..."]
    }
  }
}
```

快照置于锁定科学核心之外。它可以改变投稿包装；不能原地修改机制、主张、证伪测试或证据画像。

---

# English Version

## Thin official target-outlet policy layer

Use this file only after the scientific idea has been formed on the common Robotics Research Manifold. It maintains no fixed target pool and encodes neither an acceptance model nor an isolated workflow. Each time, retrieve live primary sources only for the conference, journal, or other outlet currently specified by the user.

### Retrieval rule

Open the target outlet's current official home page, call, and author instructions. Record the exact access date and source URL for every requested field:

- current scope, article type, and intended readership;
- deadline and timezone;
- page or word limit and whether references count;
- anonymity policy;
- prior-publication and dual-submission policy;
- supplement, video, artifact, and external-link policy;
- rebuttal or revision channel;
- journal-to-conference presentation option;
- template, submission system, and final-upload requirements.

Do not guess an official address from memory or from the outlet name. Search for the official organization, society, publisher, or conference domain, then follow the current-cycle page. Annual conference rules and journal policies change; an old snapshot is not a current rule.

### Boundary with the evidence profile

Current official scope, article type, and readership features belong in Step 4 `target_context` and may combine with the user objective to extract `target_vector=T`. The outlet name itself and prestige assumptions cannot directly set a Boolean bit, axis floor, or depth module, and no fixed outlet-to-vector mapping may be stored.

Step 8 handles format and live-policy packaging only and cannot silently overwrite a locked profile. If newly verified current scope or readership context requires substantive recalibration, return to Step 4, create a new `research_intensity` version with `supersedes`, and rerun the ten-check audit.

`target_outside_claim` only exposes target context beyond the claim and cannot inflate the evidence burden, experiment plan, or claim; `claim_outside_target` only exposes an alignment gap and cannot weaken scientific requirements.

### Field status

Set each policy field to:

- `VERIFIED`: one locatable value from a current official source;
- `RULE_CONFLICT`: conflicting current official sources, with both values and URLs retained;
- `RULE_NOT_VERIFIED`: insufficient primary evidence was found.

Never guess when values conflict or remain missing.

### Snapshot structure

```json
{
  "venue": "user-specified target outlet",
  "cycle": "YYYY",
  "verified_at": "YYYY-MM-DD",
  "official_source_urls": ["https://..."],
  "fields": {
    "page_limit": {
      "status": "VERIFIED",
      "value": "verbatim-normalized value",
      "source_urls": ["https://..."]
    }
  }
}
```

Keep the snapshot outside the locked scientific core. It may change submission packaging; it cannot mutate the mechanism, claim, falsification test, or evidence profile in place.
