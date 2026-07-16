# 车牌号识别系统

独立的车牌号识别演示系统，包含 FastAPI 后端、中文前端工作台、SQLite 识别历史和可配置识别 Provider。

## 功能

- 上传 JPG、PNG、WEBP 图片。
- 展示图片预览、识别车牌号、置信度、识别模式和耗时。
- 保存识别历史到 SQLite。
- 通过 `RECOGNIZER_PROVIDER` 在 `mock`、`local`、`ai` 之间切换。
- `local` 模式调用本机 Tesseract，执行真实 OCR，不会回退到 mock。
- 默认 `mock` 模式无需模型和外部 API，适合演示和联调。

## 安装

```bash
cd license-plate-recognition-system
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## 启动

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8088
```

打开：

```text
http://127.0.0.1:8088
```

## 配置

```text
RECOGNIZER_PROVIDER=mock
AI_API_KEY=
AI_ENDPOINT=
AI_MODEL=
LOCAL_MODEL_PATH=
DATABASE_URL=sqlite:///data/recognitions.db
UPLOAD_DIR=uploads
```

`mock` 是默认模式，不需要模型和外部 API。`local` 使用 `LOCAL_MODEL_PATH` 指定的 Tesseract 可执行文件，`ai` 会检查 `AI_API_KEY` 和 `AI_ENDPOINT`。配置缺失时系统会返回中文错误提示，并在识别记录中保留失败状态。

### 使用真实本地 OCR（不使用 mock）

本地模式要求安装 Tesseract，并具备 `chi_sim` 和 `eng` 语言数据。Windows 配置示例：

```text
RECOGNIZER_PROVIDER=local
LOCAL_MODEL_PATH=C:\Program Files\Tesseract-OCR\tesseract.exe
```

在 PowerShell 中启动：

```powershell
$env:RECOGNIZER_PROVIDER = "local"
$env:LOCAL_MODEL_PATH = "C:\Program Files\Tesseract-OCR\tesseract.exe"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8088
```

检查语言数据：

```powershell
& "C:\Program Files\Tesseract-OCR\tesseract.exe" --list-langs
```

本地识别通过 `chi_sim+eng`、TSV 输出和 10 秒超时运行 Tesseract，支持大陆普通车牌和新能源车牌格式。它不包含独立的车牌定位模型或图像预处理，也不会把 `O`/`I` 猜测为数字。OCR 正常执行但没有匹配到车牌格式时，接口会明确返回“未识别到符合格式的车牌号”；这是一次真实处理结果，不会生成假车牌或回退到 mock。

## API

```text
GET  /api/config
POST /api/recognitions
GET  /api/recognitions
```

`POST /api/recognitions` 使用 `multipart/form-data`，字段名为 `file`。

## 测试

```bash
python -m pytest -v
```

如果当前 Windows 用户临时目录权限受限，可以把 pytest 临时目录放到项目内：

```bash
python -m pytest -v --basetemp=.pytest_tmp
```
