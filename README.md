# 英语听力试题 TTS 工具

将英语听力考试原文脚本转换为标准语音音频，支持对话、独白、广播等全部题型。

## 功能特点

- **双引擎支持**：edge-tts（免费，无需 API Key）+ OpenAI TTS（高质量）
- **多说话人**：自动为不同角色分配不同声音（男声/女声）
- **多题型**：对话、讲座、广播通知、采访访谈
- **题号播报**：自动识别并语音播报 "Number 1" 等题号
- **批量处理**：一次转换整个文件夹的所有脚本
- **口音选择**：美式、英式、澳式口音

---

## 安装

```bash
cd english-listening-tts

# 安装依赖
pip install -r requirements.txt

# 安装 ffmpeg（pydub 依赖）
# macOS:
brew install ffmpeg
# Ubuntu/Debian:
# sudo apt install ffmpeg

# 配置环境变量（只使用 edge-tts 可跳过）
cp .env.example .env
# 如需使用 OpenAI TTS，在 .env 中填入 OPENAI_API_KEY
```

---

## 脚本格式

新建一个 `.txt` 文件，按以下格式编写：

### 对话格式（自动分配男女声）

```
@title: Unit 3 Dialogue
@type: dialogue

Number 1.
[Man]: Excuse me, where is the library?
[Woman]: It's on the second floor, next to the computer lab.
[Man]: Thank you very much.

Number 2.
[Man]: What time does the library close?
[Woman]: It closes at nine PM on weekdays.
```

### 独白/讲座格式

```
@title: Lecture on Global Warming
@type: monologue

Today I'm going to talk about climate change and its effects...
Number 3. Scientists have found that temperatures have risen by 1.5 degrees...
```

### 广播通知格式

```
@title: School Announcement
@type: broadcast

[Announcer]: Attention all students. The school sports day scheduled for Friday...
```

### 可选：指定口音

```
@title: British English Dialogue
@voice_a: male_uk
@voice_b: female_uk

[Man]: Shall we have a spot of tea?
[Woman]: That sounds lovely.
```

**口音选项：**

| 代码 | 说明 |
|------|------|
| `male` / `female` | 美式（默认）|
| `male_uk` / `female_uk` | 英式 |
| `male_au` / `female_au` | 澳式 |

---

## 使用方法

### 转换单个文件（推荐新手）

```bash
# 使用免费的 edge-tts（默认）
python main.py convert examples/dialogue.txt

# 指定输出路径
python main.py convert examples/dialogue.txt -o output/unit3.mp3

# 使用 OpenAI TTS（需要 API Key）
python main.py convert examples/dialogue.txt --provider openai
```

### 批量转换整个文件夹

```bash
python main.py batch examples/ -o output/
```

### 预览脚本结构（不生成音频）

```bash
python main.py preview examples/dialogue.txt
```

### 查看可用声音

```bash
# 所有英式声音
python main.py voices --accent uk

# 所有美式声音
python main.py voices --accent us
```

---

## 输出示例

```
Script:   examples/dialogue.txt
Title:    Unit 5 - At the Restaurant
Type:     dialogue
Speakers: ['Man', 'Woman']
Provider: edge
Output:   output/dialogue.mp3

Synthesizing  ████████████████████  8/8
Done! Audio saved to: output/dialogue.mp3
```

---

## 项目结构

```
english-listening-tts/
├── main.py              # 命令行入口
├── config.py            # 声音配置、音频参数
├── requirements.txt
├── .env.example
├── parser/
│   └── script_parser.py # 解析脚本文件
├── tts/
│   ├── base.py          # TTS 基类
│   ├── edge_provider.py # edge-tts（免费）
│   └── openai_provider.py # OpenAI TTS
├── audio/
│   └── processor.py     # 合并音频片段
├── examples/            # 示例脚本
│   ├── dialogue.txt     # 情景对话
│   ├── monologue.txt    # 独白/讲座
│   ├── broadcast.txt    # 广播通知
│   └── interview.txt    # 采访访谈
└── output/              # 生成的音频文件
```

---

## 常见问题

**Q: 不需要 API Key 吗？**
A: 使用 edge-tts 完全免费，不需要任何 API Key。OpenAI TTS 需要付费的 OpenAI API Key。

**Q: 支持哪些输出格式？**
A: 默认 MP3，可在 `config.py` 的 `AUDIO_SETTINGS` 中改为 `wav`。

**Q: 如何调整语速？**
A: 在 `config.py` 中修改 `edge_rate`（如 `"-10%"` 更慢）或 `openai_speed`（如 `0.85` 更慢）。

**Q: 生成的音频时长大概多少？**
A: 取决于文本长度。通常每个对话（4-6 句）约 30-60 秒。
