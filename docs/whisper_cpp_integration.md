# Whisper.cpp 集成文档

本文档详细说明了如何在集成助手项目中集成 Whisper.cpp，并针对 Snapdragon XElite 平台进行优化。

## 概述

Whisper.cpp 是 OpenAI Whisper 模型的 C++ 实现，它提供了高效的语音转录功能。通过将 Whisper.cpp 集成到集成助手项目中，我们可以利用 Snapdragon XElite 平台的硬件加速能力，提高语音转录的性能和效率。

## 系统要求

- Windows 10/11 或 Linux 操作系统
- CMake 3.12+
- Git
- Python 3.8+
- Snapdragon XElite 平台（可选，但推荐用于获得最佳性能）

## 安装步骤

### 1. 设置 Whisper.cpp

我们提供了一个自动化脚本来下载、编译和配置 Whisper.cpp：

```bash
python scripts/setup_whisper_cpp.py --model small
```

参数说明：
- `--model`: 指定要使用的模型，可选值包括 tiny、base、small、medium、large-v1、large-v2、large-v3 等
- `--no-xelite`: 如果不需要针对 Snapdragon XElite 平台优化，可以添加此参数

脚本将执行以下操作：
1. 下载 Whisper.cpp 源代码
2. 下载指定的模型
3. 编译 Whisper.cpp，并针对 Snapdragon XElite 平台进行优化
4. 复制服务器可执行文件
5. 创建配置文件
6. 更新项目配置
7. 创建启动脚本

### 2. 启动 Whisper.cpp 服务

可以使用以下命令启动 Whisper.cpp 服务：

```bash
python scripts/start_whisper_cpp_server.py
```

参数说明：
- `--host`: 指定服务主机地址，默认为 127.0.0.1
- `--port`: 指定服务端口，默认为 8178
- `--model`: 指定要使用的模型，默认使用配置文件中指定的模型

### 3. 测试 Whisper.cpp 服务

可以使用以下命令测试 Whisper.cpp 服务：

```bash
python scripts/test_whisper_cpp.py --audio path/to/audio.wav
```

参数说明：
- `--audio`: 指定要转录的音频文件路径（必需）
- `--host`: 指定服务主机地址，默认为 127.0.0.1
- `--port`: 指定服务端口，默认为 8178
- `--benchmark`: 运行基准测试
- `--iterations`: 指定基准测试的迭代次数，默认为 3

## 配置说明

Whisper.cpp 组件的配置位于 `config.yaml` 文件中的 `meeting.whisper` 部分：

```yaml
meeting:
  whisper:
    use_cpp: true                # 是否使用 Whisper.cpp
    model_name: "small"          # 模型名称
    model_path: "whisper_cpp/models"  # 模型路径
    server_host: "127.0.0.1"     # 服务主机地址
    server_port: 8178            # 服务端口
    use_xelite: true             # 是否使用 Snapdragon XElite 优化
    num_threads: 8               # 线程数
    use_gpu: true                # 是否使用 GPU
    use_dsp: true                # 是否使用 DSP
    use_npu: true                # 是否使用 NPU
```

## Snapdragon XElite 优化

Whisper.cpp 组件针对 Snapdragon XElite 平台进行了以下优化：

1. **多线程处理**：利用 Snapdragon XElite 的多核 CPU 进行并行处理
2. **GPU 加速**：利用 Snapdragon XElite 的 GPU 进行矩阵运算加速
3. **DSP 加速**：利用 Snapdragon XElite 的数字信号处理器进行音频处理加速
4. **NPU 加速**：利用 Snapdragon XElite 的神经网络处理单元进行模型推理加速

这些优化可以通过配置文件进行调整，以适应不同的硬件环境和性能需求。

## 性能基准测试

可以使用以下命令运行性能基准测试：

```bash
python scripts/test_whisper_cpp.py --audio path/to/audio.wav --benchmark
```

基准测试将测量以下指标：
- 处理时间：转录音频所需的时间
- 实时因子 (RTF)：处理时间与音频长度的比值，值越小表示性能越好

## 故障排除

1. **服务启动失败**
   - 检查是否已正确安装依赖项
   - 检查模型文件是否已下载
   - 检查端口是否被占用

2. **转录结果不准确**
   - 尝试使用更大的模型（如 medium 或 large）
   - 检查音频文件质量
   - 确保音频格式为 WAV 或 MP3

3. **性能不佳**
   - 确保已启用 Snapdragon XElite 优化
   - 调整线程数以适应硬件环境
   - 尝试使用较小的模型（如 tiny 或 base）

## 与其他组件的集成

Whisper.cpp 组件已集成到集成助手项目的 Langraph 架构中，它将在以下情况下被优先使用：

1. 配置文件中设置了 `use_cpp: true`
2. Whisper.cpp 服务可用

如果 Whisper.cpp 服务不可用，系统将自动回退到其他转录方式，如 AnythingLLM API 或本地 Whisper 模型。

## 参考资料

- [Whisper.cpp GitHub 仓库](https://github.com/ggerganov/whisper.cpp)
- [OpenAI Whisper 模型](https://github.com/openai/whisper)
- [Snapdragon XElite 开发者文档](https://developer.qualcomm.com/)
