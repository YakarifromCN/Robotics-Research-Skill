# Third-party notices

## Humanizer

Writing 的离线语言适配基于 Humanizer 3.0.0，作者 Siqi Chen，MIT 许可。
来源、文件校验值与适配类型记录在 `skills/write-robotics-paper/assets/dependencies.json`；
完整许可证位于 `skills/write-robotics-paper/references/humanizer-LICENSE.txt`。
这是保留学术证据边界的精简适配，不代表上游完整 Skill。

The offline Writing language adaptation derives from Humanizer 3.0.0 by Siqi Chen,
under the MIT license. Source and digests are recorded in the dependency manifest
above; the adjacent license file preserves the full notice. This compact academic
adaptation is not the complete upstream Skill.

This project is inspired by and adapts ideas from Microsoft ResearchStudio and the paper *ResearchStudio-Idea: An Evidence-Grounded Research-Ideation Skill Suite from ML Conference Outcomes*.

ResearchStudio repository: https://github.com/microsoft/ResearchStudio

Snapshot commit: `3c120d8e801428d56f3ed66fc3e20b4e286df053`.

The original repository is distributed under the MIT License:

```text
MIT License

Copyright (c) 2026 Happy

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

This project does not reproduce ResearchStudio's ML-conference acceptance statistics as robotics-conference priors. Robotics outlets form one coverage-check set; target-context features are derived at runtime from current official scope and readership, while formal submission policies must be re-verified for each submission cycle.

## Additional public method references

The following public projects were read for method comparison, workflow distillation, or interface design. No upstream checkout is a runtime dependency, and no source is presented as an acceptance-probability or quality-ranking model. Unless a license is explicitly stated below, users should consult the upstream repository for its current license and reuse conditions.

| Source | Use in this repository |
| --- | --- |
| [HKUSTDial/Supervisor-Skills](https://github.com/HKUSTDial/Supervisor-Skills) | Supervision, stage orchestration, and human checkpoint comparison; no runtime import. |
| [ResearchStudio paper](https://arxiv.org/abs/2607.04439) | Descriptive research-strategy analysis; no acceptance or quality inference. |
| [Academic Research Skills](https://github.com/Imbad0202/academic-research-skills-codex) | Academic search, reading, writing, and review workflow comparison. |
| [Awesome-Journal-Skills](https://github.com/brycewang-stanford/Awesome-Journal-Skills) | Cross-venue workflow comparison; common invariants only. |
| [Yuan1z0825/nature-skills](https://github.com/Yuan1z0825/nature-skills) | Citation, data, figure, literature, and paper-preparation workflow comparison. |
| Publicly searchable conference/journal papers and official pages | Analysis corpus for robotics axes, prior work, evidence, writing, and venue routing; not acceptance probability, quality ranking, or statistical causal evidence. |

The corpus is retained as auditable metadata, URLs, hashes, and compact summaries rather than copied paper text. Public awards, oral/spotlight records, and community reuse are discovery signals only.

## ARIS (Auto-Research in Sleep)

This project also distills domain-neutral lifecycle, evidence, gate, artifact,
trace, isolation, and resumability patterns from [ARIS](https://github.com/wanshuiyin/auto-claude-code-research-in-sleep).

Pinned source commit: `3e49e63aae6a653067f9e2101d50457f1f7d6a2f`.

ARIS is distributed under the MIT License, copyright © 2026 wanshuiyin. The
Robotics-AR implementation rewrites only generic contract shapes and does not
ship ARIS code, skills, provider settings, MCP servers, UI, or runtime checkout.
The auditable source receipt, inventory, distillation matrix, license decision,
and neutrality audit are kept in `agent/robotics-ar-distillation/` during local
development. Any future substantive ARIS code/text reuse requires a fresh
mapping and attribution review.

```text
MIT License

Copyright (c) 2026 wanshuiyin

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## Awesome-Journal-Skills

This project also reviewed and distilled robotics-related skill material from:

https://github.com/brycewang-stanford/Awesome-Journal-Skills

Snapshot commit: `9f86f094d6a7a680fb14e169336dd98bf75436ec`.

That repository is distributed under the MIT License, copyright © 2026 Bryce Wang. The distilled project retains only cross-venue scientific invariants and source-calibration notes; it does not treat repository venue heuristics as official policy. The full MIT license text is available in the upstream repository.

```text
MIT License

Copyright (c) 2026 Bryce Wang

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## Review orchestration references

The review subskill adapts orchestration ideas from [AI-research-feedback review-paper](https://github.com/claesbackman/AI-research-feedback/blob/main/Skills/review-paper/SKILL.md) and protocol ideas from [academic-research-skills academic-paper-reviewer](https://github.com/Imbad0202/academic-research-skills/blob/main/academic-paper-reviewer/SKILL.md). It does not copy their economics or general-science reviewer personas. The robotics implementation adds claim-lock checks, nonordinal evidence profiles, robotics-specific specialist prompts, stable evidence anchors, and explicit artifact/revision gates.

## Evidence-Bound Press-Conference Revision Skill

The bidirectional contribution-calibration protocol distills behavioral ideas
from [Evidence-Bound-Press-Conference-Revision-Skill](https://github.com/lensback940701/Evidence-Bound-Press-Conference-Revision-Skill),
inspected at commit `5c67ea9`. The robotics implementation rewrites the method
around Claim Ledger ceilings, stable result/number/citation IDs, objection
burden, robotics evidence states, and fail-closed validators; no upstream
checkout is a runtime dependency.

The upstream project is distributed under the MIT License:

```text
MIT License

Copyright (c) 2026 lensback940701

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```
