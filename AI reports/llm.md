[
  {
    "category": "模型更新与价格调整",
    "items": [
      {
        "title": "OpenAI发布o3-pro模型",
        "content": "o3-pro已面向ChatGPT Pro用户和API开放，性能显著优于o3：在Extended NYT Connections基准测试中得分87.3（原82.5），首次在SnakeBench登顶，并解决汉诺塔10层问题。用户反馈其非代码任务表现远超Claude Opus 4。但推理速度比o1-pro慢3倍。",
        "links": [
          {
            "text": "性能详情",
            "url": "https://twitter.com/OpenAI/status/1932586531560304960"
          },
          {
            "text": "定价策略",
            "url": "https://twitter.com/scaling01/status/1932596796347252937"
          }
        ]
      },
      {
        "title": "OpenAI大幅降价",
        "content": "o3模型价格降低80%（输入$2/百万token，输出$8/百万token），比GPT-4o便宜20%，可能迫使Google和Anthropic跟进出价调整。",
        "links": [
          {
            "text": "市场影响",
            "url": "https://twitter.com/scaling01/status/1932566284270538966"
          }
        ]
      },
      {
        "title": "Kimi K2 Thinking: 1T-A32B params, SOTA HLE, BrowseComp, TauBench && Soumith leaves Pytorch",
        "content": "Moonshot AI发布Kimi K2 Thinking，1万亿参数MoE模型，320亿活跃专家，支持INT4量化训练，256K上下文窗口，多项基准领先。部署于vLLM并提供OpenAI兼容API，早期用户报告API不稳定。",
        "links": [
          {
            "text": "官方介绍",
            "url": "https://news.smol.ai/issues/25-11-06-kimi-k2"
          }
        ]
      },
      {
        "title": "Claude Haiku 4.5",
        "content": "Anthropic推出Claude Haiku 4.5，速度提升2倍、成本降低3倍，相比Sonnet 4.5更具性价比，尤其适合高频迭代场景。早期评估显示其推理能力接近主流模型，且在多任务上表现优异。",
        "links": [
          {
            "text": "技术亮点",
            "url": "https://news.smol.ai/issues/25-10-15-haiku-45"
          }
        ]
      },
      {
        "title": "DeepSeek-V3.2-Exp: Sparse Attention算法优化长上下文成本",
        "content": "DeepSeek发布V3.2-Exp模型，引入稀疏注意力机制，将长上下文推理成本降低50%以上，同时保持高质量输出，是当前最经济的千亿级大模型之一。",
        "links": [
          {
            "text": "模型细节",
            "url": "https://news.smol.ai/issues/25-09-29-sonnet-45"
          }
        ]
      },
      {
        "title": "OpenAI Dev Day: Apps SDK, AgentKit, Codex GA, GPT‑5 Pro and Sora 2 APIs",
        "content": "OpenAI在DevDay发布多个重磅产品：GPT-5 Pro、Sora 2（含Pro版）、Codex通用可用性，以及Apps SDK与AgentKit开发套件，全面构建应用平台生态。定价为输入$15/百万token，输出$120/百万token。",
        "links": [
          {
            "text": "发布会详情",
            "url": "https://news.smol.ai/issues/25-10-06-devday"
          }
        ]
      },
      {
        "title": "MiniMax M2 230BA10B — 8% of Claude Sonnet's price, ~2x faster, new SOTA open model",
        "content": "Hailuo AI发布MiniMax M2，约2300亿参数、100亿活跃参数的开源稀疏MoE模型，MIT许可，API价格仅为Claude Sonnet的8%，推理速度快2倍，成为新的开源SOTA。",
        "links": [
          {
            "text": "模型主页",
            "url": "https://news.smol.ai/issues/25-10-27-minimax-m2"
          }
        ]
      },
      {
        "title": "GPT-5 Pro vs Gemini 2.5 Deep Think: FrontierMath Tier 4结果揭晓",
        "content": "FrontierMath Tier 4测试中，GPT-5 Pro以微弱优势胜出Gemini 2.5 Deep Think，但数据泄露担忧被Epoch AI Research澄清；微软与Mila提出Markovian Thinking方法提升效率。",
        "links": [
          {
            "text": "测试报告",
            "url": "https://news.smol.ai/issues/25-10-10-not-much"
          }
        ]
      }
    ]
  },
  {
    "category": "Agent与工具生态",
    "items": [
      {
        "title": "Claude Agent Skills - glorified AGENTS.md? or MCP killer?",
        "content": "Anthropic推出新Agent Skills系统，使用Markdown文件+元数据构建专用Agent，可处理PDF、PPT等文档任务，被评价为‘比MCP更重要的突破’，正推动开发者社区爆发式创新。",
        "links": [
          {
            "text": "技能系统说明",
            "url": "https://news.smol.ai/issues/25-10-16-claude-skills"
          }
        ]
      },
      {
        "title": "Cursor 2.0 & Composer-1: Fast Models and New Agents UI",
        "content": "Cursor 2.0上线Composer-1编码Agent，支持多智能体协作、内置浏览器测试及语音转代码功能，界面重构实现高效Agent管理，显著提升开发体验。",
        "links": [
          {
            "text": "产品页面",
            "url": "https://news.smol.ai/issues/25-10-29-cursor-2"
          }
        ]
      },
      {
        "title": "LangChain & LangGraph 1.0: Agent Engineering Stack正式发布",
        "content": "LangChain v1.0整合Agent工程能力，统一文档与控制流，支持多轮评估与可观测性，月下载量超8500万，Fortune 500企业中有35%采用该框架。",
        "links": [
          {
            "text": "版本公告",
            "url": "https://news.smol.ai/issues/25-10-22-not-much"
          }
        ]
      },
      {
        "title": "Anthropic Skills + Microsoft Learn MCP Server: Agent Workflow加速器",
        "content": "Anthropic Skills结合Microsoft Learn MCP服务器，实现即时文档查询与多工具集成，极大提升Grounded Agent工作流效率，适用于企业级Agent开发与部署。",
        "links": [
          {
            "text": "技术文档",
            "url": "https://news.smol.ai/issues/25-10-16-claude-skills"
          }
        ]
      },
      {
        "title": "Thinking Machines Tinker API: LoRA-based Fine-tuning for MoE models",
        "content": "Thinking Machines推出Tinker API，专为Qwen-235B等混合专家模型设计LoRA微调服务，提供低层Post-training primitives，附带开源Cookbook库，助力研究者快速实验。",
        "links": [
          {
            "text": "产品介绍",
            "url": "https://news.smol.ai/issues/25-10-01-thinky"
          }
        ]
      },
      {
        "title": "Google DeepMind CodeMender: 自动化安全补丁生成",
        "content": "Google DeepMind发布CodeMender，可在大型代码库中自动识别漏洞并生成修复补丁，减少人工审查负担，已在部分开源项目中验证效果。",
        "links": [
          {
            "text": "技术博客",
            "url": "https://news.smol.ai/issues/25-10-07-gemini-cua"
          }
        ]
      },
      {
        "title": "HuggingChat Omni: Meta-Routing across 115 Open Models",
        "content": "HuggingFace推出HuggingChat Omni，通过Arch-Router-1.5B实现跨15家提供商的115个开源模型动态路由，提升多模态任务调度效率，推动模型即服务（MaaS）发展。",
        "links": [
          {
            "text": "平台入口",
            "url": "https://news.smol.ai/issues/25-10-17-not-much"
          }
        ]
      }
    ]
  },
  {
    "category": "推理优化与架构创新",
    "items": [
      {
        "title": "vLLM支持NVIDIA Nemotron Nano 2：Hybrid Transformer-Mamba架构提速6x",
        "content": "vLLM新增对NVIDIA Nemotron Nano 2的支持，该模型采用Transformer-Mamba混合架构，通过可调‘思考预算’机制实现高达6倍Token生成速度提升，适用于高吞吐场景。",
        "links": [
          {
            "text": "vLLM集成公告",
            "url": "https://news.smol.ai/issues/25-10-24-not-much"
          }
        ]
      },
      {
        "title": "SparseServe动态稀疏注意力优化GPU KV Cache管理",
        "content": "SparseServe引入基于KV tiering的动态稀疏注意力机制，在GPU内存受限环境下大幅提升吞吐和降低延迟，是未来大规模推理部署的关键基础设施。",
        "links": [
          {
            "text": "技术白皮书",
            "url": "https://news.smol.ai/issues/25-10-10-not-much"
          }
        ]
      },
      {
        "title": "Samsung 7M Tiny Recursive Model (TRM): 小模型也能强推理",
        "content": "Samsung发布7M参数递归模型TRM，用MLP替代自注意力结构，在ARC-AGI和Sudoku任务上超越更大模型，证明小而精架构的潜力，适合边缘设备部署。",
        "links": [
          {
            "text": "论文链接",
            "url": "https://news.smol.ai/issues/25-10-08-not-much"
          }
        ]
      },
      {
        "title": "OpenAI Titan XPU：自研ASIC芯片计划启动",
        "content": "OpenAI正在设计定制ASIC芯片用于推理，目标部署10GW算力，配合NVIDIA与AMD现有合作，总算力目标达250GW，相当于美国能源消耗的一半，支撑海量ambient agents运行。",
        "links": [
          {
            "text": "硬件路线图",
            "url": "https://news.smol.ai/issues/25-10-13-oai-broadcom"
          }
        ]
      },
      {
        "title": "Together AI Atlas：Speculative Decoding加速推理4倍",
        "content": "Together AI发布Atlas，一种自适应推测解码方案，使DeepSeek-V3.1推理速度提升4倍，同时减少RL训练时间60%，为低成本高性能推理提供新范式。",
        "links": [
          {
            "text": "技术演示",
            "url": "https://news.smol.ai/issues/25-10-10-not-much"
          }
        ]
      }
    ]
  },
  {
    "category": "视频与多模态生成",
    "items": [
      {
        "title": "Sora 2: 视频+音频模型落地社交App",
        "content": "OpenAI发布Sora 2，具备物理世界建模能力与角色一致性特性，集成至社交网络应用，引发病毒式传播，但也引发内容滥用和审核挑战，Sam Altman强调兼顾用户体验与社会责任。",
        "links": [
          {
            "text": "产品发布页",
            "url": "https://news.smol.ai/issues/25-09-30-sora2"
          }
        ]
      },
      {
        "title": "Kling 2.5 Turbo: 文本到视频生成领导者",
        "content": "Kling AI发布2.5 Turbo版本，文本到视频生成能力行业领先，定价极具竞争力，适合创作者快速迭代内容，支持图像到视频转换，推动短视频AIGC普及。",
        "links": [
          {
            "text": "模型对比评测",
            "url": "https://news.smol.ai/issues/25-10-02-not-much"
          }
        ]
      },
      {
        "title": "Google DeepMind Veo 3.1：精度编辑与场景融合领先",
        "content": "Veo 3.1在社区基准中表现最佳，支持高级精度编辑和无缝场景拼接，适合专业影视制作流程，已被多家工作室纳入生产管线。",
        "links": [
          {
            "text": "Benchmark结果",
            "url": "https://news.smol.ai/issues/25-10-20-deepseek-ocr"
          }
        ]
      },
      {
        "title": "Alibaba Qwen3-VL: 轻量级视觉语言模型媲美72B大模型",
        "content": "阿里发布Qwen3-VL系列轻量模型（4B/8B），FP8量化支持，上下文可达1M tokens，视觉理解准确率超97%，在OSS社区获得广泛支持，适合本地部署与嵌入式场景。",
        "links": [
          {
            "text": "GitHub仓库",
            "url": "https://news.smol.ai/issues/25-10-14-not-much"
          }
        ]
      },
      {
        "title": "DeepSeek-OCR：视觉压缩文本实现10倍效率提升",
        "content": "DeepSeek发布DeepSeek-OCR，将长文本压缩为视觉格式后仍保持97%解码精度，每秒处理3300万页文档，打破传统token化限制，有望实现无限上下文。",
        "links": [
          {
            "text": "ICCV论文",
            "url": "https://news.smol.ai/issues/25-10-20-deepseek-ocr"
          }
        ]
      }
    ]
  },
  {
    "category": "开源模型与社区进展",
    "items": [
      {
        "title": "MiniMax M2: MIT许可的230B MoE模型登顶开源榜单",
        "content": "MiniMax M2开源发布，参数规模230B、激活10B，MIT许可证，支持代码与Agent任务，排名Artificial Analysis Intelligence Index第5名，是当前最强开源模型之一。",
        "links": [
          {
            "text": "Hugging Face页面",
            "url": "https://news.smol.ai/issues/25-10-27-minimax-m2"
          }
        ]
      },
      {
        "title": "Radical Numerics RND1: 开源扩散LM模型引领研究",
        "content": "Radical Numerics开源RND1模型，30B参数稀疏MoE扩散语言模型，提供完整代码与权重，推动diffusion LM社区发展，可用于文本生成、图像理解等多种任务。",
        "links": [
          {
            "text": "GitHub仓库",
            "url": "https://news.smol.ai/issues/25-10-09-state-of-ai"
          }
        ]
      },
      {
        "title": "Qwen3 Omni Realtime: 多模态统一模型发布",
        "content": "阿里巴巴发布Qwen3 Omni实时版，支持音频、视频、文本统一输入输出，语言与语音能力强大，BigBench Audio任务中超越Gemini 2.0 Flash，适合多模态交互场景。",
        "links": [
          {
            "text": "模型介绍",
            "url": "https://news.smol.ai/issues/25-10-08-not-much"
          }
        ]
      },
      {
        "title": "Zhipu GLM-4.6：355B参数MoE模型发布",
        "content": "智谱AI发布GLM-4.6，采用Mixture-of-Experts架构，参数量达355B，专注于编程与逻辑推理，已在Design Arena基准中取得亮眼成绩，是国产大模型的重要里程碑。",
        "links": [
          {
            "text": "官方博客",
            "url": "https://news.smol.ai/issues/25-10-07-gemini-cua"
          }
        ]
      }
    ]
  },
  {
    "category": "基础设施与部署优化",
    "items": [
      {
        "title": "Terminal-Bench 2.0 and Harbor：云容器化推理平台上线",
        "content": "Terminal-Bench 2.0发布，支持Harbor框架的云容器部署，显著提升模型服务稳定性，被Kimi K2 Thinking和Claude 4.5采纳，适配Apple Silicon与消费级硬件。",
        "links": [
          {
            "text": "项目文档",
            "url": "https://news.smol.ai/issues/25-11-07-tbench2"
          }
        ]
      },
      {
        "title": "vLLM集成支持：从NVIDIA到Meta再到Hugging Face",
        "content": "vLLM持续扩展支持范围，现已支持NVIDIA Nemotron Nano 2、IBM Granite 4.0、Kimi Linear等多款前沿模型，成为最灵活的本地LLM部署引擎之一。",
        "links": [
          {
            "text": "vLLM官网",
            "url": "https://news.smol.ai/issues/25-10-24-not-much"
          }
        ]
      },
      {
        "title": "CoreWeave / Weights & Biases / OpenPipe：Serverless RL基础设施上线",
        "content": "三大平台联合推出Serverless Reinforcement Learning解决方案，无需配置环境即可训练Agent，显著降低RL成本与门槛，加速小型团队的Agent研发进程。",
        "links": [
          {
            "text": "平台介绍",
            "url": "https://news.smol.ai/issues/25-10-08-not-much"
          }
        ]
      },
      {
        "title": "LlamaIndex LIGHT框架：长程记忆任务提升160%",
        "content": "LlamaIndex LIGHT框架在1000万token长程记忆任务中相较原始RAG基线提升160.6%，是目前最有效的本地知识增强方案之一，适合复杂对话与长期代理记忆管理。",
        "links": [
          {
            "text": "GitHub项目",
            "url": "https://news.smol.ai/issues/25-11-03-not-much"
          }
        ]
      }
    ]
  },
  {
    "category": "企业合作与投资动态",
    "items": [
      {
        "title": "OpenAI与AWS战略结盟：380亿美元计算合同签署",
        "content": "OpenAI与AWS达成380亿美元算力协议，部署数千块NVIDIA GB200/GP300芯片，强化云端推理能力，同时微软获准向阿联酋出口GPU，计划投资79亿美元建设数据中心。",
        "links": [
          {
            "text": "新闻原文",
            "url": "https://news.smol.ai/issues/25-11-03-not-much"
          }
        ]
      },
      {
        "title": "Reflection融资20亿美元专注安全评估",
        "content": "Reflection完成20亿美元融资，由AlphaGo、PaLM、Gemini团队核心成员主导，目标打造高安全性开源模型生态，重视模型可信度与可解释性，推动AI治理标准化。",
        "links": [
          {
            "text": "融资详情",
            "url": "https://news.smol.ai/issues/25-10-09-state-of-ai"
          }
        ]
      },
      {
        "title": "SoftBank收购ABB机器人部门：$5.4B布局人形机器人",
        "content": "软银宣布收购ABB机器人部门，金额达54亿美元，聚焦家庭与工业场景人形机器人，意图打造下一代具身智能硬件生态，与Figure 03形成竞争格局。",
        "links": [
          {
            "text": "交易公告",
            "url": "https://news.smol.ai/issues/25-10-09-state-of-ai"
          }
        ]
      },
      {
        "title": "Figure 03：下一代非遥控人形机器人亮相",
        "content": "Figure公司发布Figure 03，主打自主操作能力，可在家庭或工厂环境中执行复杂任务，强调‘无需远程操控’的设计理念，标志着人形机器人进入实用阶段。",
        "links": [
          {
            "text": "产品页面",
            "url": "https://news.smol.ai/issues/25-10-09-state-of-ai"
          }
        ]
      }
    ]
  },
  {
    "category": "benchmarking与评估体系",
    "items": [
      {
        "title": "FrontierMath Tier 4：GPT-5 Pro小幅领先Gemini 2.5",
        "content": "FrontierMath Tier 4结果显示GPT-5 Pro在数学推理准确率上略胜Gemini 2.5 Deep Think，Epoch AI Research澄清了此前关于题库泄露的争议，推动更公平的模型评测标准。",
        "links": [
          {
            "text": "排行榜",
            "url": "https://news.smol.ai/issues/25-10-10-not-much"
          }
        ]
      },
      {
        "title": "Arena WebDev Leaderboard：MiniMax M2与Claude Sonnet 4.5平分秋色",
        "content": "Arena平台WebDev榜单更新，MiniMax M2 230B与Claude Sonnet 4.5同列榜首，表明开源模型在代码任务上的成熟度已逼近闭源前沿模型，开发者选择更多样化。",
        "links": [
          {
            "text": "榜单地址",
            "url": "https://news.smol.ai/issues/25-11-03-not-much"
          }
        ]
      },
      {
        "title": "IMO-Bench数学推理评测：Gemini DeepThink表现突出",
        "content": "DeepMind发布IMO-Bench，一个全新的数学推理评估集，Gemini DeepThink在其中得分高，ProofAutoGrader与人类评分高度相关，证明模型能有效自我修正错误。",
        "links": [
          {
            "text": "评测页面",
            "url": "https://news.smol.ai/issues/25-11-04-not-much"
          }
        ]
      },
      {
        "title": "GPQA Diamond评测：Kimi-K2宣称77%得分超越GPT-4.5",
        "content": "Kimi-K2 Reasoner在GPQA Diamond测试中得分77%，高于GPT-4.5的71.4%，虽未公开验证，但引起广泛关注，凸显中国模型在逻辑推理上的进步。",
        "links": [
          {
            "text": "模型评测报告",
            "url": "https://news.smol.ai/issues/25-11-05-not-much"
          }
        ]
      }
    ]
  },
  {
    "category": "开发者工具与IDE革新",
    "items": [
      {
        "title": "VS Code Agent Sessions功能上线",
        "content": "微软VS Code引入Agent Sessions功能，统一管理Copilot、Codex及其他AI Agent会话，提升开发者生产力，支持历史回溯与项目隔离，是Agent IDE的里程碑。",
        "links": [
          {
            "text": "功能说明",
            "url": "https://news.smol.ai/issues/25-11-05-not-much"
          }
        ]
      },
      {
        "title": "OpenAI Codex IDE扩展：语音与控制器驱动编程",
        "content": "Codex新增语音输入与控制器编程支持，提高代码生成效率，内部团队已实现高频率交付，开发者称其为‘真正的生产力革命’，适合敏捷开发与自动化脚本。",
        "links": [
          {
            "text": "Codex文档",
            "url": "https://news.smol.ai/issues/25-10-06-devday"
          }
        ]
      },
      {
        "title": "Claude Code V2：VS Code插件与终端升级",
        "content": "Anthropic发布Claude Code V2，包含本地VS Code插件、检查点保存、全新终端UI及新 mascot Clawd，进一步强化其作为开发者首选Agent的地位。",
        "links": [
          {
            "text": "更新日志",
            "url": "https://news.smol.ai/issues/25-09-29-sonnet-45"
          }
        ]
      },
      {
        "title": "Google AI Studio Annotation Mode：Gemini代码变更可视化",
        "content": "Google AI Studio新增Annotation模式，可直观展示Gemini代码修改前后差异，提升团队协作效率，特别适合多人协同开发与代码审计场景。",
        "links": [
          {
            "text": "Studio功能页",
            "url": "https://news.smol.ai/issues/25-10-23-not-much"
          }
        ]
      }
    ]
  },
  {
    "category": "芯片与硬件进展",
    "items": [
      {
        "title": "NVIDIA Blackwell B200：vLLM+Kernel Competition开启",
        "content": "NVIDIA与GPU_MODE联合发起3个月NVFP4内核优化竞赛，奖励包括DGX Spark与RTX 50XX GPU，鼓励社区优化推理效率，Blackwell架构成新一代LLM训练主力平台。",
        "links": [
          {
            "text": "竞赛页面",
            "url": "https://news.smol.ai/issues/25-11-03-not-much"
          }
        ]
      },
      {
        "title": "OpenAI自研ASIC芯片：Titan XPU规划落地",
        "content": "OpenAI公布自研ASIC芯片设计，目标部署10GW推理算力，配合NVIDIA与AMD现有资源，总目标250GW，能耗仅占美国电力一半，标志其走向底层算力自主可控。",
        "links": [
          {
            "text": "硬件路线图",
            "url": "https://news.smol.ai/issues/25-10-13-oai-broadcom"
          }
        ]
      },
      {
        "title": "AMD MI300X vs NVIDIA H100/H200：ROCm稳定性改善",
        "content": "InferenceMAX报告ROCm稳定性显著提升，MI300X在LLaMA-3-70B FP8负载下表现趋近H100，为开源社区提供更多硬件选择，打破NVIDIA垄断。",
        "links": [
          {
            "text": "性能对比",
            "url": "https://news.smol.ai/issues/25-10-13-oai-broadcom"
          }
        ]
      }
    ]
  },
  {
    "category": "学术研究与前沿探索",
    "items": [
      {
        "title": "Stanford Palimpsest方法：检测模型训练顺序指纹",
        "content": "斯坦福研究提出Palimpsest方法，通过训练顺序特征识别模型来源，具有统计学保证，有助于打击伪造与溯源，是未来模型监管的基础工具之一。",
        "links": [
          {
            "text": "论文链接",
            "url": "https://news.smol.ai/issues/25-10-24-not-much"
          }
        ]
      },
      {
        "title": "JEPA-SCORE：无需重训练实现密度估计",
        "content": "Yann LeCun团队提出JEPA-SCORE方法，利用预训练编码器直接进行密度估计，避免重新训练，适用于无监督学习与异常检测，提升模型泛化能力。",
        "links": [
          {
            "text": "技术博客",
            "url": "https://news.smol.ai/issues/25-10-08-not-much"
          }
        ]
      },
      {
        "title": "Cell2Sentence-Scale 27B：生成癌症假说的开源模型",
        "content": "Google与耶鲁联合发布Cell2Sentence-Scale 27B模型，能从细胞数据中生成实验验证的癌症假设，推动AI在生物医学领域的应用落地，权重完全开源供社区复现。",
        "links": [
          {
            "text": "项目页面",
            "url": "https://news.smol.ai/issues/25-10-15-haiku-45"
          }
        ]
      },
      {
        "title": "ModernVBERT：MIT图像-文本检索模型发布",
        "content": "MIT发布ModernVBERT，高效图像-文本检索模型，支持跨模态搜索，已在多模态应用中验证效果，是开源社区图像理解的新标杆。",
        "links": [
          {
            "text": "GitHub仓库",
            "url": "https://news.smol.ai/issues/25-10-03-not-much"
          }
        ]
      }
    ]
  }
]