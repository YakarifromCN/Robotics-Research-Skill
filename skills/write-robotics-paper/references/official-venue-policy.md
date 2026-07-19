# 中文版

## 轻量官方目标载体政策层

仅在任务涉及已命名目标载体或投稿就绪性时使用本层。它不得重塑科学主张，也不得充当录用模型。

### 实时核验协议

1. 记录目标载体、文章或投稿类型、周期或期号、时区及访问时间戳。
2. 打开当前官方征稿通知和作者指南。优先采用出版商、学会和当前活动网站，而非聚合站点。
3. 核验：范围；页数或字数限制以及参考文献是否计入；模板；匿名；作者元数据；补充材料或视频；既往发表与期刊—会议转投；评审或 rebuttal；AI 使用披露；截止时间；终稿要求。
4. 每个值均保存精确来源 URL 和原字段名；使用简短释义，不大段复制原文。
5. 若当前官方页面相互冲突，输出 `RULE_CONFLICT` 并保留两组值和 URL。若必需字段无法核验，输出 `RULE_NOT_VERIFIED`。绝不能依据往年网站推断规则。

建议的快照结构：

```json
{
  "target": "",
  "normalized_target": "",
  "submission_type": "",
  "cycle": "",
  "checked_at": "YYYY-MM-DDTHH:MM:SSZ",
  "status": "VERIFIED | RULE_CONFLICT | RULE_NOT_VERIFIED",
  "fields": {
    "length": {"value": "", "source": "", "checked_at": ""},
    "anonymity": {"value": "", "source": "", "checked_at": ""},
    "supplement": {"value": "", "source": "", "checked_at": ""}
  },
  "conflicts": []
}
```

将 `RAP` 和 `RA-P` 规范化为 **IEEE Robotics and Automation Practice**。严格区分 **Soft Robotics**（Sage 期刊）、**T-SRO**（IEEE Transactions on Soft Robotics）和 **RoboSoft**（IEEE-RAS 会议）。

### 官方来源起点

以下链接仅用于发现，不是冻结的政策快照。继续进入其当前作者指南链接。

| 目标载体 | 官方起点 |
|---|---|
| ICRA | https://www.ieee-ras.org/conferences-workshops/fully-sponsored/icra/ 及当前会议网站 |
| IROS | https://www.ieee-ras.org/conferences-workshops/financially-co-sponsored/iros/ 及当前会议网站 |
| SII | 当前 IEEE/SICE SII 会议网站（例如相应周期的作者指南） |
| Humanoids | https://www.ieee-ras.org/conferences-workshops/fully-sponsored/humanoids/ 及当前会议网站 |
| ROBIO | 当前 IEEE ROBIO 会议网站及 PaperPlaza 条目 |
| RA-L | https://www.ieee-ras.org/publications/ra-l/ |
| RA-P/RAP | https://www.ieee-ras.org/publications/ra-p/ |
| T-RO | https://www.ieee-ras.org/publications/t-ro/ |
| IJRR | https://journals.sagepub.com/home/ijr 及其投稿指南 |
| RSS | https://roboticsconference.org/information/cfp/ |
| CoRL | 当前 Conference on Robot Learning 官方网站及作者指南 |
| CASE | https://www.ieee-ras.org/conferences-workshops/fully-sponsored/case/ 及当前会议网站 |
| Science Robotics | https://www.science.org/journal/scirobotics 及 AAAS 作者指南 |
| RoboSoft | https://www.ieee-ras.org/conferences-workshops/fully-sponsored/ 及当前 RoboSoft 网站 |
| Soft Robotics | https://journals.sagepub.com/home/srb 及其投稿指南 |
| T-SRO | https://www.ieee-ras.org/publications/t-sro/ 及其作者信息页 |

若适用 IEEE-RAS 双匿名政策，还要核验 https://www.ieee-ras.org/publications/rules-for-the-double-anonymous-review-process 。即使会议与期刊共用模板或转投通道，其规则也可能独立变化。

### 科学校准保持独立

完成实时核验后，政策只可用于：

- 分配页数或字数；
- 匿名或去匿名；
- 准备允许的附件；
- 套用必需模板和元数据；
- 满足披露与上传规则。

不得用目标载体名称选择深度模块、增加证据负担、改写研究向量、隐藏负面证据或夸大重要性。如果证据锁定后的故事不符合已核验范围或格式，应建议改投；只有主张变化才能证明修改科学契约是合理的。

---

# English Version

## Thin official venue-policy layer

Use this layer only for a named target or submission-readiness task. It must not reshape the scientific claim or act as an acceptance model.

### Live-check protocol

1. Record target, article/submission type, cycle or issue, timezone, and access timestamp.
2. Open the current official CFP and author instructions. Prefer the publisher/society and current event site over aggregators.
3. Verify: scope, page/word limit and whether references count; template; anonymity; author metadata; supplement/video; prior-publication and journal-conference transfer; review/rebuttal; AI-use disclosure; deadlines; and camera-ready requirements.
4. Store each value with its exact source URL and quoted field name, using short paraphrases rather than copied prose.
5. If official pages disagree, emit `RULE_CONFLICT` with both values and URLs. If a required value is absent, emit `RULE_NOT_VERIFIED`. Never infer a rule from last year's site.

Suggested snapshot shape:

```json
{
  "target": "",
  "normalized_target": "",
  "submission_type": "",
  "cycle": "",
  "checked_at": "YYYY-MM-DDTHH:MM:SSZ",
  "status": "VERIFIED | RULE_CONFLICT | RULE_NOT_VERIFIED",
  "fields": {
    "length": {"value": "", "source": "", "checked_at": ""},
    "anonymity": {"value": "", "source": "", "checked_at": ""},
    "supplement": {"value": "", "source": "", "checked_at": ""}
  },
  "conflicts": []
}
```

Normalize `RAP` and `RA-P` to **IEEE Robotics and Automation Practice**. Keep **Soft Robotics** (Sage journal), **T-SRO** (IEEE Transactions on Soft Robotics), and **RoboSoft** (IEEE-RAS conference) distinct.

### Official-source starting points

These are discovery anchors, not frozen policy snapshots. Follow the current author-instruction links they expose.

| Target | Official starting point |
|---|---|
| ICRA | https://www.ieee-ras.org/conferences-workshops/fully-sponsored/icra/ and the current conference site |
| IROS | https://www.ieee-ras.org/conferences-workshops/financially-co-sponsored/iros/ and the current conference site |
| SII | current IEEE/SICE SII conference site (for example, the cycle-specific author instructions) |
| Humanoids | https://www.ieee-ras.org/conferences-workshops/fully-sponsored/humanoids/ and the current conference site |
| ROBIO | current IEEE ROBIO conference site and PaperPlaza entry |
| RA-L | https://www.ieee-ras.org/publications/ra-l/ |
| RA-P/RAP | https://www.ieee-ras.org/publications/ra-p/ |
| T-RO | https://www.ieee-ras.org/publications/t-ro/ |
| IJRR | https://journals.sagepub.com/home/ijr and its submission guidelines |
| RSS | https://roboticsconference.org/information/cfp/ |
| CoRL | current official Conference on Robot Learning site and author instructions |
| CASE | https://www.ieee-ras.org/conferences-workshops/fully-sponsored/case/ and the current conference site |
| Science Robotics | https://www.science.org/journal/scirobotics and AAAS author instructions |
| RoboSoft | https://www.ieee-ras.org/conferences-workshops/fully-sponsored/ and the current RoboSoft site |
| Soft Robotics | https://journals.sagepub.com/home/srb and its submission guidelines |
| T-SRO | https://www.ieee-ras.org/publications/t-sro/ and its information-for-authors page |

For IEEE-RAS double-anonymous policy, also check https://www.ieee-ras.org/publications/rules-for-the-double-anonymous-review-process when it applies. Conference and journal rules can change independently even when they share a template or transfer route.

### Scientific calibration remains separate

After live verification, use policy only to:

- allocate pages/words;
- anonymize or de-anonymize;
- prepare allowed attachments;
- render the required template and metadata;
- satisfy disclosure and upload rules.

Do not use a target name to select depth modules, add evidence burden, rewrite the research vector, hide negative evidence, or inflate importance. If the evidence-locked story does not fit the verified scope or format, recommend rerouting; only a claim change may justify revising the scientific contract.
