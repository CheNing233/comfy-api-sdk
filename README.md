# comfy-api-sdk

面向 ComfyUI HTTP/WebSocket 接口的异步 Python SDK。本文档覆盖 `comfy_library` 中当前已实现且建议对外使用的接口。

## 1. 快速开始

### 1.1 依赖与导入

```python
import asyncio
from comfy_library import config
from comfy_library.client import ComfyUIClient
from comfy_library.workflow import ComfyWorkflow
```

### 1.2 端到端最小流程（异步）

```python
import asyncio
from comfy_library import config
from comfy_library.client import ComfyUIClient
from comfy_library.workflow import ComfyWorkflow

async def main():
    async with ComfyUIClient("http://127.0.0.1:8188", proxy=config.PROXY) as client:
        workflow = ComfyWorkflow("example_src/neta_lumina_i2i.json")
        workflow.add_replacement("6", "text", "A beautiful cat, cinematic")
        workflow.add_output_node("9")
        results = await client.execute_workflow(workflow, output_dir="outputs")
        print(results)

if __name__ == "__main__":
    asyncio.run(main())
```

## 2. 接口总览

### 2.1 类与模块

- `ComfyUIClient`：连接服务端、提交工作流、监听执行、下载输出、管理任务队列。
- `ComfyWorkflow`：声明工作流 JSON 路径、节点输入替换规则、输出节点提取规则。
- `config`：SDK 超时、重试、代理等运行参数常量。

### 2.2 对外推荐接口与内部接口边界

- **对外推荐接口**
  - `ComfyUIClient.__init__`
  - `ComfyUIClient.execute_workflow`
  - `ComfyUIClient.upload_file`
  - `ComfyUIClient.queue_prompt`
  - `ComfyUIClient.get_history`
  - `ComfyUIClient.wait_for_prompt_completion`
  - `ComfyUIClient.view_tasks`
  - `ComfyUIClient.interrupt_running_task`
  - `ComfyUIClient.delete_queued_tasks`
  - `ComfyUIClient.get_models`
  - `ComfyUIClient.load_and_prepare_workflow`
  - `ComfyWorkflow.__init__`
  - `ComfyWorkflow.add_replacement`
  - `ComfyWorkflow.add_output_node`
- **内部实现接口（一般不直接调用）**
  - `ComfyUIClient._get_http_url`
  - `ComfyUIClient._get_data_by_selector`
  - `ComfyUIClient._get_outputs_for_node`
  - `ComfyUIClient._download_file`

---

## 3. ComfyWorkflow 接口文档

### 3.1 `ComfyWorkflow(workflow_json_path)`

#### 字段

- `workflow_json_path: str`：工作流 JSON 文件路径。
- `_replacements: Dict[str, Dict[str, Any]]`：节点输入替换表（内部缓存，执行前由 client 使用）。
- `_output_nodes: Dict[str, List[str]]`：输出提取规则（节点 ID -> selector 列表）。

#### 用法

- 创建工作流对象后，先通过 `add_replacement` 填充动态输入，再通过 `add_output_node` 声明输出。
- 该对象本身不执行请求，仅作为 `ComfyUIClient.execute_workflow` 的入参。

#### 示例

```python
workflow = ComfyWorkflow("example_src/neta_lumina_i2i.json")
workflow.add_replacement("33", "image", "server_image.png")
workflow.add_replacement("6", "text", "masterpiece, best quality")
workflow.add_output_node("9")  # 默认下载
workflow.add_output_node("69", ["text[0]", "text[99]"])
```

#### 边缘情况

- `workflow_json_path` 不存在时，后续执行会在 `load_and_prepare_workflow` 抛出 `FileNotFoundError`。
- 节点 ID 若不在 workflow JSON 中，不会崩溃，但对应替换不会生效。

### 3.2 `add_replacement(node_id, input_name, value)`

#### 字段

- `node_id: str`：目标节点 ID。
- `input_name: str`：节点 inputs 下的字段名。
- `value: Any`：替换值。
- 返回值：`self`（支持链式调用）。

#### 用法

- 用于动态改写 workflow JSON 中指定节点输入。
- 可多次调用覆盖同一节点下多个输入字段。

#### 示例

```python
workflow.add_replacement("3", "seed", 123456789)
workflow.add_replacement("6", "text", "cinematic lighting")
```

#### 边缘情况

- 如果 `node_id` 存在但节点结构不含 `inputs`，执行时可能触发 KeyError 风险（取决于工作流内容结构）。
- 相同 `(node_id, input_name)` 重复设置时，后一次覆盖前一次。

### 3.3 `add_output_node(node_id, selectors=None)`

#### 字段

- `node_id: str`：输出节点 ID。
- `selectors: Union[str, List[str], None]`
  - `None`：记录 `DEFAULT_DOWNLOAD`，自动下载该节点可识别的文件列表。
  - `str`：单个 selector，如 `images[0].filename`。
  - `List[str]`：多个 selector，自动去重。
- 返回值：`self`。

#### 用法

- 用于声明执行结束后希望从历史输出中提取哪些内容。
- selector 支持点号和数组下标路径（如 `text[0]`、`images[0].filename`）。

#### 示例

```python
workflow.add_output_node("118")                # DEFAULT_DOWNLOAD
workflow.add_output_node("127", "images")      # 提取并下载文件列表
workflow.add_output_node("69", ["text[0]"])    # 提取文本
```

#### 边缘情况

- 传入重复 selector 会被去重。
- selector 路径不存在时，结果中会返回 `"指定的JSON路径不存在"`。
- 节点不是输出节点时，结果中会返回 `"非输出节点"`。

---

## 4. ComfyUIClient 接口文档

### 4.1 `ComfyUIClient(base_url, proxy=None)`

#### 字段

- `base_url: str`
  - 普通格式：`http://127.0.0.1:8188`
  - Token 嵌入格式：`<token>@https://host`（自动生成 `Authorization: Bearer <token>`）
- `proxy: Optional[str]`：代理地址（同时用于 `http://` 与 `https://`）。
- 关键实例字段：
  - `client_id: str`：本地随机 UUID。
  - `ws_address: str`：按 `base_url` 自动推导的 ws/wss 地址。

#### 用法

- 推荐搭配 `async with` 使用，确保连接关闭。
- 与 `ComfyWorkflow` 配合执行完整推理流程。

#### 示例

```python
async with ComfyUIClient("http://127.0.0.1:8188", proxy=config.PROXY) as client:
    ...
```

#### 边缘情况

- `base_url` 中包含 `@` 会被解析为 token+真实地址；格式不正确可能导致地址异常。
- `base_url` 缺少协议头时会影响 ws 地址推导。

### 4.2 `execute_workflow(workflow, output_dir="outputs")`

#### 字段

- `workflow: ComfyWorkflow`：包含 workflow 路径、替换规则、输出规则。
- `output_dir: str`：下载文件保存根目录。
- 返回值：`Dict[str, Any]`
  - 成功：按 `node_id -> selector -> output` 返回。
  - 失败：返回 `{"error": "..."}`。

#### 用法

- 一站式执行：加载工作流 -> 入队 -> 监听 -> 拉取历史 -> 按 selector 汇总结果。
- 适合大多数业务调用场景。

#### 示例

```python
results = await client.execute_workflow(workflow, output_dir="outputs")
if "error" in results:
    print("失败:", results["error"])
else:
    print("成功:", results)
```

#### 边缘情况

- 入队失败：返回 `"无法提交工作流到队列"`。
- 执行超时或中断：返回 `"工作流执行失败或超时"`。
- 历史记录缺失：返回 `"无法获取执行历史记录"`。
- 未声明输出节点时，可能返回空结果或仅日志提示无输出。

### 4.3 `upload_file(file_path, server_subfolder="", overwrite=True)`

#### 字段

- `file_path: str`：本地文件路径。
- `server_subfolder: str`：服务端子目录。
- `overwrite: bool`：是否覆盖同名文件。
- 返回值：`Dict[str, Any]`（服务端上传接口返回 JSON）。

#### 用法

- 上传输入图片后，把返回中的 `name` 填入 workflow 节点输入。

#### 示例

```python
upload_info = await client.upload_file("example_src/upload_img.png")
server_filename = upload_info["name"]
workflow.add_replacement("33", "image", server_filename)
```

#### 边缘情况

- 本地文件不存在会直接抛 `FileNotFoundError`。
- HTTP 错误会抛异常（`httpx.HTTPStatusError` 等），需调用方捕获。

### 4.4 `load_and_prepare_workflow(workflow_path, replacements)`（类方法）

#### 字段

- `workflow_path: str`：workflow JSON 文件路径。
- `replacements: Dict[str, Dict[str, Any]]`：节点替换映射。
- 返回值：`Dict[str, Any]`（替换后的工作流 JSON）。

#### 用法

- 可单独调用进行预处理，也可由 `execute_workflow` 自动调用。

#### 示例

```python
prepared = await ComfyUIClient.load_and_prepare_workflow(
    "example_src/neta_lumina_i2i.json",
    {"6": {"text": "new prompt"}}
)
```

#### 边缘情况

- 文件不存在抛 `FileNotFoundError`。
- JSON 内容非法会触发解析错误。
- 节点不存在时该替换会被跳过（不会自动新增节点）。

### 4.5 `queue_prompt(prepared_workflow)`

#### 字段

- `prepared_workflow: Dict[str, Any]`：已准备好的 workflow JSON。
- 返回值：`str | None`（`prompt_id` 或空）。

#### 用法

- 手动拆分流程时先调用本接口入队，再调用监听与历史查询接口。

#### 示例

```python
prompt_id = await client.queue_prompt(prepared)
if not prompt_id:
    print("入队失败")
```

#### 边缘情况

- 网络或服务端错误时返回 `None`（并打印错误）。
- 服务端返回无 `prompt_id` 时也返回 `None`。

### 4.6 `wait_for_prompt_completion(prompt_id, timeout=None)`

#### 字段

- `prompt_id: str`：任务 ID。
- `timeout: Optional[int]`：单次消息等待超时；为空则使用 `WORKFLOW_EXECUTION_TIMEOUT`。
- 返回值：`bool`（是否成功执行）。

#### 用法

- 通过 WebSocket 监听执行进度，并在关键状态下回查历史确认结果。

#### 示例

```python
ok = await client.wait_for_prompt_completion(prompt_id)
if not ok:
    print("任务失败或超时")
```

#### 边缘情况

- WebSocket 连续失败会按 `DOWNLOAD_RETRY_ATTEMPTS` 重试后返回 `False`。
- 监听超时会主动查 history；若未确认成功则返回 `False`。
- 收到 `execution_interrupted` 会直接返回 `False`。

### 4.7 `get_history(prompt_id)`

#### 字段

- `prompt_id: str`：任务 ID。
- 返回值：`Dict[str, Any]`（对应 prompt 的 history 数据，失败时 `{}`）。

#### 用法

- 在执行完成后读取输出和状态消息。

#### 示例

```python
history = await client.get_history(prompt_id)
outputs = history.get("outputs", {})
```

#### 边缘情况

- 请求失败时返回空字典，调用方需自行判空。

### 4.8 `view_tasks()`

#### 字段

- 无入参。
- 返回值：`Dict[str, List[Dict]]`，包含：
  - `running`: 运行中任务（`prompt_id`）
  - `queued`: 排队中任务（`prompt_id`）
  - `completed`: 已完成任务（`prompt_id`, `outputs_preview`）

#### 用法

- 适用于运维或管理脚本（见 `manage_tasks.py`）。

#### 示例

```python
tasks = await client.view_tasks()
print(tasks["running"], tasks["queued"], tasks["completed"][:3])
```

#### 边缘情况

- 任一请求异常时返回空结构：
  `{"running": [], "queued": [], "completed": []}`。
- `outputs_preview` 仅做预览，不保证覆盖全部输出类型。

### 4.9 `interrupt_running_task()`

#### 字段

- 无入参。
- 返回值：`bool`（请求是否成功发送）。

#### 用法

- 中断当前执行任务，一般与任务管理 CLI 配合使用。

#### 示例

```python
if await client.interrupt_running_task():
    print("已发送中断请求")
```

#### 边缘情况

- 返回 `True` 仅表示请求成功发送，不等价于任务已立即停止。
- 请求异常时返回 `False`。

### 4.10 `delete_queued_tasks(prompt_ids)`

#### 字段

- `prompt_ids: List[str]`：待删除的排队任务 ID 列表。
- 返回值：`bool`（请求是否成功发送）。

#### 用法

- 批量删除未开始执行的队列任务。

#### 示例

```python
await client.delete_queued_tasks(["id1", "id2"])
```

#### 边缘情况

- 目标任务不存在或已执行的处理由服务端决定，SDK 仅返回请求成功与否。

### 4.11 `get_models(folder=None, prefer_experimental=True, filter_name=False)`

#### 字段

- `folder: Optional[str]`
  - `None`：查询模型类别列表（如 `checkpoints`、`loras` 等）。
  - 非空字符串：查询指定类别下的模型文件列表。
- `prefer_experimental: bool`
  - `True`（默认）：优先请求 `/api/experiment/models` 系列接口，失败后回退到 `/models` 系列接口。
  - `False`：优先请求 `/models` 系列接口，再尝试实验接口。
- `filter_name: bool`
  - `False`（默认）：返回完整结构（对象列表或兼容转换后的对象列表）。
  - `True`：仅返回 `name` 数组（`List[str]`），便于快速下拉选择或匹配过滤。
- 返回值：`List[Any]`
  - 类别查询通常返回对象列表（含 `name`、`folders`）或字符串列表（旧接口）。
  - folder 查询优先返回对象列表（如 `name`、`size`、`pathIndex`、`modified`、`created`）。
  - 若走传统 `/models/{folder}` 且仅返回字符串文件名，SDK 会转换为 `{"name": "<filename>"}` 结构，确保最小可读字段一致。
  - 当 `filter_name=True` 时，统一返回名称字符串数组。

#### 用法

- 用于动态发现 ComfyUI 当前可用模型类别与具体模型文件。
- 可直接结合 `name` 与 `size` 做模型筛选或展示。

#### 示例

```python
# 1) 查询模型类别（优先 experiment）
model_groups = await client.get_models()
print(model_groups[0])

# 2) 查询 checkpoints 下模型文件
checkpoint_models = await client.get_models(folder="checkpoints")
for model in checkpoint_models:
    model_name = model.get("name")
    model_size = model.get("size")
    print(model_name, model_size)

# 3) 仅返回 name 数组
checkpoint_names = await client.get_models(folder="checkpoints", filter_name=True)
print(checkpoint_names)
```

#### 边缘情况

- 指定 `folder` 不存在时，实验接口与传统接口都可能返回 404，SDK 最终返回空列表 `[]`。
- 服务器返回非 JSON 响应或网络异常时，SDK 会记录错误并尝试回退；全部失败后返回 `[]`。
- 不同 ComfyUI 版本返回字段可能不同，建议业务侧以 `name` 为必备字段，`size` 等字段做可选读取。

---

## 5. 配置常量（`comfy_library.config`）

### 5.1 `PROXY`

#### 字段

- 类型：`Optional[str]`
- 默认值：`None`

#### 用法

- 传给 `ComfyUIClient(..., proxy=config.PROXY)` 统一设置代理。

#### 示例

```python
from comfy_library import config
config.PROXY = "http://127.0.0.1:7890"
```

#### 边缘情况

- 代理不可用会导致 HTTP/WS 请求失败。

### 5.2 超时与重试常量

#### 字段

- `HTTP_TIMEOUT = 120.0`
- `WS_OPEN_TIMEOUT = 20.0`
- `WS_PING_INTERVAL = 10.0`
- `WS_PING_TIMEOUT = 30.0`
- `WORKFLOW_EXECUTION_TIMEOUT = 1145`
- `DOWNLOAD_RETRY_ATTEMPTS = 3`
- `DOWNLOAD_RETRY_DELAY = 5`

#### 用法

- 用于控制 SDK 默认网络行为、执行监听等待、下载重试策略。

#### 示例

```python
from comfy_library import config
config.WORKFLOW_EXECUTION_TIMEOUT = 1800
config.DOWNLOAD_RETRY_ATTEMPTS = 5
```

#### 边缘情况

- 超时设置过小容易误判失败，过大则等待时间过长。
- 重试次数过高可能拖慢失败反馈。

---

## 6. 参考脚本

- `example_usage.py`：图生图示例，含上传、节点替换、多 selector 输出提取。
- `example_wan22_i2v_usage.py`：复杂视频工作流输出提取示例。
- `manage_tasks.py`：任务查看、中断、删除 CLI 示例。

## 7. 常见问题与建议

- 建议优先用 `execute_workflow` 走“一站式”流程，减少手动拼装步骤。
- 需要更细粒度控制时，再拆分为 `load_and_prepare_workflow` + `queue_prompt` + `wait_for_prompt_completion` + `get_history`。
- 对 selector 建议先在 `/history/<prompt_id>` 验证结构后再写入代码，避免路径不存在。
