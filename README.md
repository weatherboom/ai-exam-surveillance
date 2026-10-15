# Aegis AI // 考试监控套件

一套自主化多考生考试监考系统，基于 YOLOv8、17 关键点人体姿态估计、课桌空间追踪与时序行为分析技术构建。
适用于各类摄像头视角（包括斜向闭路监控视角与教室过道正向视角），能够高精度识别作弊行为，实现零误报。

---

## 🚀 快速开始（三步运行）

### 1. 克隆并进入项目目录
```bash
git clone https://github.com/ShashankJangid/ai-exam-surveillance.git
cd ai-exam-surveillance
```

### 2. 创建虚拟环境并安装依赖
```bash
# 创建虚拟环境
python -m venv .venv

# Windows 下激活：
.venv\Scripts\activate
# Linux / macOS 下激活：
# source .venv/bin/activate

# 安装所需依赖包
pip install -r requirements.txt
```

### 3. 启动 Web 控制台
```bash
python app.py
```
用浏览器打开：
```text
http://127.0.0.1:7860
```

---

## 📖 应用使用说明

### 方式一：分析已录制的考试视频（推荐）

1. **上传视频：**
   - 在 **1. 监考视频输入** 面板中点击 **上传**，或将视频文件拖拽到该区域。
   - 也可以直接点击 **快速示例视频（点击加载）** 中的示例一键载入。
   - 或使用 `sample_videos/` 目录中自带的示例视频手动测试：
     - `sample_videos/155164-809618953.mp4` *（斜向机位教室，向前偷看抄袭）*
     - `sample_videos/7092083-hd_1920_1080_30fps.mp4` *（教室正面机位，过道两侧串通）*
2. **选择运行模式：**
   - **教室 / 考场监控（CCTV）：** 多考生模式。追踪课桌前全部考生，监测向前探头偷看、转头看向过道、手机使用行为。
   - **远程在线考试（摄像头）：** 单人远程监考模式。检测考生离开座位、室内出现多人、视线偏移、使用手机等行为。
3. **配置抽帧间隔（加速）：**
   - 默认`3`（每 3 帧只处理 1 帧）。处理速度提升约 400%，同时保留完整时序行为信息。
   - 如果需要逐帧完整标注，请设置为`1`。
4. **点击 “开始分析”：**
   - 实时进度条展示处理进度。
5. **查看分析结果：**
   - **标注后的输出画面：** 观看处理后带实时标注框的视频：
     - 🟩 **翠绿色：** 状态正常，考生专注答题。
     - 🟥 **红色标记：** 确认存在作弊违规行为。
     - 🟦 **蓝色框：** 检测到课桌区域出现违禁物品（手机）。
   - **关键指标卡片**：查看受监控考生总数、标记违规数、无违规考生数、考场诚信指数。
   - **违规证据截图**：点击任意抓拍关键帧，查看带时间戳的高清违规证据截图。
   - **违规事件记录**：按时间顺序记录时间戳、考生编号、违规类型、置信度。
   - **下载审查报告**：点击**下载审查报告（JSON）**，导出机器可读的完整取证档案，用于教务存档。

---

### 方式二：摄像头实时监考

1. 在视频输入框切换到**摄像头**标签页。
2. 授予浏览器摄像头权限。
3. 录制片段或者完整会话。
4. 选择**远程在线考试（摄像头）**模式。
5. 点击**开始分析**，检查考生考试合规情况。

---

### 方式三：Python API 调用

可以把监考引擎导入到你自己的 Python 应用或批处理脚本中：

```python
from src.pipeline import SurveillancePipeline

# 初始化流水线
pipeline = SurveillancePipeline()

# 处理视频文件
output_video_path, incidents, summary, snapshots, stats = pipeline.process_video(
    video_path="sample_videos/155164-809618953.mp4",
    mode="Classroom / Exam Hall (CCTV)",
    frame_skip=3
)

print(summary)
print(f"Room Integrity: {stats['integrity_score']}")

# 遍历被标记的违规事件
for incident in incidents:
    print(f"[{incident['timestamp']}] {incident['student_id']}: {incident['violation']} (Severity: {incident['severity']})")
```

> **注意：** `mode` 参数需传入英文值（`"Classroom / Exam Hall (CCTV)"` 或 `"Remote Online Exam (Webcam)"`）。网页上显示的中文标签只是展示层的翻译，不影响引擎内部判断。
>
> 同样地，返回的 `incidents` 与导出的 JSON 报告中，`violation`、`severity` 等字段均保持英文原值，便于程序化处理；只有网页界面会显示为中文。

---

## 🎯 基准评测与示例视频

仓库在 `sample_videos/` 目录中提供了两段真实考场录像：

| 示例视频 | 场景与机位 | 受监控考生 | 标记违规考生 | 无违规考生 | 误报 | 检出的违规行为 |
| :--- | :--- | :---: | :---: | :---: | :---: | :--- |
| **`sample_videos/155164-809618953.mp4`** | 斜向闭路监控机位 | **5** | **1**（`学生 #2`） | **4** | **0** | `偷看并抄袭前排考生` 于 4.3s、6.9s、11.7s、14.3s、16.9s、21.9s |
| **`sample_videos/7092083-hd_1920_1080_30fps.mp4`** | 教室正面机位 | **5** | **2**（`学生 #3` 与 `#5`） | **3** | **0** | `隔排偷看 / 传递信息（右侧）` [2.2s、4.7s、7.2s] 与 `隔排偷看 / 传递信息（左侧）` [2.9s] |

两段视频都使用完全相同的统一流水线依次处理，未调整任何设置或阈值。

---

## 🔬 技术实现原理

1. **固定座位课桌追踪（`src/tracker.py`）**
传统交并比追踪算法，当考生身体前倾、姿态变化时容易发生 ID 混淆错乱。
Aegis 系统将每个考生绑定到课桌中心点，使用指数移动平均（EMA）欧式质心追踪。考生在整场考试内保持固定唯一编号。
2. **不受画面缩放影响姿态归一化（`src/pose_analyzer.py`）**
通过头部位置除以肩宽计算归一化的水平、垂直视线偏转角度。
肩宽数值下限限制为 70 像素，避免画面远处考生带来的数值计算溢出。
3. **动态座位基准学习**
程序运行最初 2.5 秒，学习每个考生正常答题姿态，抵消不同摄像头拍摄角度带来的影响。
4. **多维度人体姿态判定规则（`src/rules_engine.py`）**

- **向前抄袭偷看**：考生身体前倾，头部俯仰角度向前偏移（俯仰变化值＜‑0.30，水平偏转＞0.16）触发告警。
- **过道两侧串通**：同时满足基准姿态偏移以及真实头部水平转动（向右偏转＞0.35，向左偏转＜‑0.35）。
- **持续时间过滤**：姿态异常必须维持 0.6‑0.7 秒以上才判定违规，过滤考生短暂自然转头动作。

---

## 📂 项目目录结构

```text
ai-exam-surveillance/
├── sample_videos/
│   ├── 155164-809618953.mp4           # 测试视频1（向前偷看抄袭）
│   └── 7092083-hd_1920_1080_30fps.mp4 # 测试视频2（过道两侧串通）
├── src/
│   ├── __init__.py
│   ├── detector.py                    # 违禁物品与设备检测
│   ├── pose_analyzer.py               # 基于17关键点、不受缩放影响的视线估算
│   ├── tracker.py                     # 绑定课桌的考生追踪模块
│   ├── rules_engine.py                # 时序违规状态机
│   ├── i18n.py                        # 网页界面中文文案（纯展示层翻译）
│   └── pipeline.py                    # 视频流调度与视频编码
├── app.py                             # Gradio交互式网页程序
├── openh264-2.5.0-win64.dll           # OpenH264库，用于浏览器播放视频
├── yolov8n.pt                         # YOLOv8目标检测权重文件
├── yolov8n-pose.pt                    # YOLOv8姿态估计权重文件
├── requirements.txt                   # 依赖清单
├── LICENSE                            # MIT开源协议
└── README.md                          # 项目说明文档
```

---

## 🛠️ 常见问题（FAQ）

<details>
<summary><b>1. 7860 端口已被占用，怎么换端口？</b></summary>
在 <code>app.py</code> 最后一行修改：
<pre><code>demo.launch(server_name="127.0.0.1", server_port=8080)</code></pre>
</details>

<details>
<summary><b>2. 如何启用 GPU 加速？</b></summary>
如果装有 NVIDIA 显卡并已配置 CUDA，PyTorch 与 Ultralytics 会自动使用 GPU，无需修改任何代码。
</details>

<details>
<summary><b>3. 为什么要附带 openh264？</b></summary>
Windows 上的 OpenCV 需要 Cisco OpenH264 动态库才能编码标准 H.264（<code>avc1</code>）MP4 视频。附带该 DLL 可确保开箱即得浏览器可播放的输出视频，无需手动安装编解码器。
</details>

<details>
<summary><b>4. 输出视频里的人物标注为什么还是英文？</b></summary>
视频画面上的文字由 <code>cv2.putText</code> 绘制，其内置的 Hershey 字体只支持 ASCII 字符，无法渲染中文。因此标注叠加层保持英文，中文只应用在网页界面上。
</details>

---

## 📜 开源协议

本项目基于 MIT 协议开源，详见 [LICENSE](LICENSE) 文件。
