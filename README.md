# 车牌号识别系统

独立的车牌号识别演示系统，包含 FastAPI 后端、中文前端工作台、SQLite 识别历史和可配置识别 Provider。

## 功能

- 上传 JPG、PNG、WEBP 图片。
- 展示图片预览、识别车牌号、置信度、识别模式和耗时。
- 保存识别历史到 SQLite。
- 通过 `RECOGNIZER_PROVIDER` 在 `mock`、`local`、`ai` 之间切换。
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

`mock` 是默认模式，不需要模型和外部 API。`local` 会检查 `LOCAL_MODEL_PATH`，`ai` 会检查 `AI_API_KEY` 和 `AI_ENDPOINT`。配置缺失时系统会返回中文错误提示，并在识别记录中保留失败状态。

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
