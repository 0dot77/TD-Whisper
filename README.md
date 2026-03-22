[English](#english) | [한국어](#한국어)

## English

# TD-Whisper

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://python.org)
[![TouchDesigner](https://img.shields.io/badge/TouchDesigner-2023+-orange.svg)](https://derivative.ca)
[![faster-whisper](https://img.shields.io/badge/Engine-faster--whisper-green.svg)](https://github.com/SYSTRAN/faster-whisper)

**Local Speech-to-Text (STT) Plugin for TouchDesigner**

A speech recognition plugin that runs completely offline -- no API keys, no internet required.
Uses [faster-whisper](https://github.com/SYSTRAN/faster-whisper) (based on CTranslate2) to deliver up to 4x faster performance compared to OpenAI Whisper.

---

### What is Local STT?

Typical STT services (Google, OpenAI API, etc.) send audio to cloud servers for processing.

**Local STT** is different:
- All processing happens **on your machine**
- **No API key needed** -- free and unlimited usage
- **No internet needed** -- works in offline environments
- **Privacy-friendly** -- voice data never leaves your computer
- Ideal for installations, performances, and security-sensitive environments

---

### Installation

#### 1. Prepare a Python Environment

A separate Python environment outside of TouchDesigner is required.

```bash
# Create a Python 3.10+ virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install faster-whisper
pip install faster-whisper

# For model downloads
pip install huggingface_hub
```

**For GPU usage (recommended):**
```bash
# CUDA-enabled PyTorch must be installed
pip install torch --index-url https://download.pytorch.org/whl/cu121
pip install faster-whisper
```

#### 2. Download Models

```bash
# List available models
python scripts/download_model.py --list

# Download the base model (recommended starting point)
python scripts/download_model.py --model base

# For better Korean accuracy, use small or larger
python scripts/download_model.py --model small
```

#### 3. TouchDesigner Setup

1. **Create a Base COMP** -- Add a Base COMP to your project
2. **Attach the Extension** -- Add `td/TDWhisper_Extension.py` as an Extension to the Base COMP
3. **Add Custom Parameters** (on the Base COMP):

| Parameter | Type | Description |
|-----------|------|-------------|
| `Modelsize` | Menu | `tiny`, `base`, `small`, `medium`, `large-v3` |
| `Language` | Str | Language code (`ko`, `en`, `ja`, etc.). Leave empty for auto-detection |
| `Pythonexe` | File | Path to the Python executable (e.g., `venv/bin/python`) |
| `Modeldir` | Folder | Path to the model directory (optional) |
| `Text` | Str | Latest transcription result (read-only) |
| `Status` | Str | Current status (read-only) |
| `Listening` | Toggle | Whether continuous listening mode is active (read-only) |

4. **Create an Audio Device In CHOP** -- Add one for microphone input

---

### Usage

#### Single File Transcription

```python
# Transcribe a WAV file
op('TDWhisper').ext.TDWhisperExt.Transcribe('/path/to/audio.wav')

# Get the result
text = op('TDWhisper').ext.TDWhisperExt.GetText()
```

#### CHOP Audio Transcription

```python
# Record 5 seconds from Audio Device In CHOP, then transcribe
ext = op('TDWhisper').ext.TDWhisperExt
ext.TranscribeFromCHOP(
    op('audiodevin1'),
    duration_seconds=5.0,
    callback='TDWhisper_Callbacks'
)
```

#### Continuous Listening Mode

```python
ext = op('TDWhisper').ext.TDWhisperExt

# Start continuous recognition at 3-second intervals
ext.StartListening(
    op('audiodevin1'),
    interval_seconds=3.0,
    callback='TDWhisper_Callbacks'
)

# Stop
ext.StopListening()
```

Continuous listening mode keeps the model loaded in memory, making it significantly faster than single transcriptions that reload the model each time.

#### Using Callbacks

Place `td/TDWhisper_Callbacks.py` in a Text DAT and customize it:

```python
def onTranscriptionComplete(comp, result):
    text = result.get("text", "")

    # Output to a Text TOP
    op('text1').par.text = text

    # Pass as input to an LLM
    op('llm_input').par.Prompt = text

    # Send to other software via OSC
    op('oscout1').sendOSC('/whisper/text', text)
```

---

### Transcription Output Use Cases

| Use Case | Method |
|----------|--------|
| Text visualization | Output results to a Text TOP |
| LLM integration | Pass as input to GPT/Claude API |
| OSC transmission | Send text to other software |
| Voice commands | Trigger events by detecting specific keywords |
| Subtitles | Real-time subtitles using segment timestamps |
| Data logging | Record audience speech during exhibitions (with consent) |

---

### Model Comparison

| Model | Size | VRAM | Speed (vs. real-time) | Korean Accuracy | Recommended Use |
|-------|------|------|-----------------------|-----------------|-----------------|
| `tiny` | 75 MB | ~400 MB | ~32x | Low | Quick prototyping, keyword detection |
| `base` | 145 MB | ~500 MB | ~16x | Moderate | General real-time usage |
| `small` | 488 MB | ~1 GB | ~6x | Good | Korean/multilingual recognition |
| `medium` | 1.5 GB | ~2.6 GB | ~2x | Very good | When high accuracy is needed |
| `large-v3` | 3.1 GB | ~5 GB | ~1x | Best | When highest quality is needed |

> Speed figures are based on GPU (NVIDIA CUDA). On CPU, expect roughly 3-10x slower.

#### GPU vs CPU Performance

- **NVIDIA GPU (CUDA)**: Recommended. Even `large-v3` runs at near real-time speed
- **Apple Silicon (MPS)**: faster-whisper does not currently support MPS; falls back to CPU
- **CPU only**: Recommended to limit usage to `tiny` or `base` models

---

### Use Cases

- **Voice-controlled interactive installations**: Control visuals with audience voice input
- **Real-time subtitle systems**: Display live subtitles for lectures and performances
- **Voice to Text to AI Art**: Use spoken words as prompts for AI image generation
- **Voice data visualization**: Visualize speech patterns, frequency, and emotion
- **Multilingual exhibitions**: Automatic language detection and translation integration
- **Accessibility tools**: Real-time captions for the hearing impaired

---

### Troubleshooting

#### "faster-whisper is not installed"
```bash
# Verify installation in the external Python environment
pip show faster-whisper
# Make sure the Pythonexe parameter points to the correct Python
```

#### "Model not found"
```bash
# Download the model
python scripts/download_model.py --model base
# Make sure the Modeldir parameter points to the models/ folder
```

#### Too slow on CPU
- Use `tiny` or `base` models
- Increase `interval_seconds` to 5 seconds or more
- Use an NVIDIA GPU if possible

#### Inaccurate Korean recognition
- Use `small` or larger models
- Explicitly set the `Language` parameter to `ko` (more accurate than auto-detection)
- Check microphone input quality (apply noise reduction filters)

#### TouchDesigner freezes
- All transcriptions run asynchronously (threaded), so TD should not freeze
- The `Pythonexe` path may be incorrect, causing the process to wait indefinitely
- Test by running the worker directly in a terminal:
  ```bash
  python scripts/whisper_worker.py --model base --audio test.wav
  ```

#### Microphone permissions on macOS
- Go to System Settings > Privacy & Security > Microphone and allow TouchDesigner

---

### Project Structure

```
TD-Whisper/
├── td/
│   ├── TDWhisper_Extension.py    # Extension class
│   └── TDWhisper_Callbacks.py    # Callback examples
├── scripts/
│   ├── whisper_worker.py          # Transcription worker process
│   └── download_model.py         # Model downloader
├── models/                        # Downloaded models (gitignored)
├── README.md
├── LICENSE
└── .gitignore
```

---

### License

MIT License - [0dot77](https://github.com/0dot77)

---

## 한국어

# TD-Whisper

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://python.org)
[![TouchDesigner](https://img.shields.io/badge/TouchDesigner-2023+-orange.svg)](https://derivative.ca)
[![faster-whisper](https://img.shields.io/badge/Engine-faster--whisper-green.svg)](https://github.com/SYSTRAN/faster-whisper)

**TouchDesigner용 로컬 음성-텍스트 변환(STT) 플러그인**

API 키 없이, 인터넷 없이, 완전히 오프라인으로 동작하는 음성 인식 플러그인입니다.
[faster-whisper](https://github.com/SYSTRAN/faster-whisper) (CTranslate2 기반)를 사용하여 OpenAI Whisper 대비 최대 4배 빠른 속도를 제공합니다.

---

### 로컬 STT란?

일반적인 STT 서비스(Google, OpenAI API 등)는 오디오를 클라우드 서버로 전송하여 처리합니다.

**로컬 STT**는 다릅니다:
- 모든 처리가 **내 컴퓨터에서** 이루어집니다
- **API 키 불필요** — 무료로 무제한 사용
- **인터넷 불필요** — 오프라인 환경에서도 동작
- **개인정보 보호** — 음성 데이터가 외부로 전송되지 않음
- 설치 전시, 공연, 보안이 중요한 환경에 적합

---

### 설치

#### 1. Python 환경 준비

TouchDesigner 외부에 별도의 Python 환경이 필요합니다.

```bash
# Python 3.10+ 가상환경 생성
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# faster-whisper 설치
pip install faster-whisper

# 모델 다운로드용
pip install huggingface_hub
```

**GPU 사용 시 (권장):**
```bash
# CUDA 지원 PyTorch가 설치되어 있어야 합니다
pip install torch --index-url https://download.pytorch.org/whl/cu121
pip install faster-whisper
```

#### 2. 모델 다운로드

```bash
# 모델 목록 보기
python scripts/download_model.py --list

# base 모델 다운로드 (권장 시작점)
python scripts/download_model.py --model base

# 한국어 정확도가 중요하다면 small 이상
python scripts/download_model.py --model small
```

#### 3. TouchDesigner 설정

1. **Base COMP 생성** — 프로젝트에 Base COMP를 하나 만듭니다
2. **Extension 연결** — Base COMP에 `td/TDWhisper_Extension.py`를 Extension으로 추가
3. **Custom Parameters 추가** (Base COMP에):

| Parameter | Type | 설명 |
|-----------|------|------|
| `Modelsize` | Menu | `tiny`, `base`, `small`, `medium`, `large-v3` |
| `Language` | Str | 언어 코드 (`ko`, `en`, `ja` 등). 비워두면 자동 감지 |
| `Pythonexe` | File | Python 실행 파일 경로 (예: `venv/bin/python`) |
| `Modeldir` | Folder | 모델 디렉토리 경로 (선택사항) |
| `Text` | Str | 최신 인식 결과 (읽기 전용) |
| `Status` | Str | 현재 상태 (읽기 전용) |
| `Listening` | Toggle | 연속 청취 모드 활성화 여부 (읽기 전용) |

4. **Audio Device In CHOP 생성** — 마이크 입력을 위해 추가

---

### 사용법

#### 단일 파일 변환

```python
# WAV 파일 변환
op('TDWhisper').ext.TDWhisperExt.Transcribe('/path/to/audio.wav')

# 결과 가져오기
text = op('TDWhisper').ext.TDWhisperExt.GetText()
```

#### CHOP 오디오 변환

```python
# Audio Device In CHOP에서 5초 녹음 후 변환
ext = op('TDWhisper').ext.TDWhisperExt
ext.TranscribeFromCHOP(
    op('audiodevin1'),
    duration_seconds=5.0,
    callback='TDWhisper_Callbacks'
)
```

#### 연속 청취 모드

```python
ext = op('TDWhisper').ext.TDWhisperExt

# 3초 간격으로 연속 인식 시작
ext.StartListening(
    op('audiodevin1'),
    interval_seconds=3.0,
    callback='TDWhisper_Callbacks'
)

# 중지
ext.StopListening()
```

연속 청취 모드는 모델을 메모리에 유지한 상태로 동작하므로, 매번 모델을 로드하는 단일 변환보다 훨씬 빠릅니다.

#### 콜백 활용

`td/TDWhisper_Callbacks.py`를 Text DAT에 넣고 커스터마이즈하세요:

```python
def onTranscriptionComplete(comp, result):
    text = result.get("text", "")

    # Text TOP으로 출력
    op('text1').par.text = text

    # LLM 입력으로 전달
    op('llm_input').par.Prompt = text

    # OSC로 다른 소프트웨어에 전송
    op('oscout1').sendOSC('/whisper/text', text)
```

---

### 인식된 텍스트 활용 예시

| 활용 | 방법 |
|------|------|
| 텍스트 시각화 | Text TOP에 결과 출력 |
| LLM 연동 | GPT/Claude API 입력으로 전달 |
| OSC 전송 | 다른 소프트웨어에 텍스트 전달 |
| 음성 명령 | 특정 키워드 감지로 이벤트 트리거 |
| 자막 표시 | 세그먼트 타임스탬프로 실시간 자막 |
| 데이터 로깅 | 전시 중 관객 음성 기록 (동의 하에) |

---

### 모델 비교

| 모델 | 크기 | VRAM | 속도 (대비 실시간) | 한국어 정확도 | 추천 용도 |
|------|------|------|---------------------|-------------|-----------|
| `tiny` | 75 MB | ~400 MB | ~32x | 낮음 | 빠른 프로토타이핑, 키워드 감지 |
| `base` | 145 MB | ~500 MB | ~16x | 보통 | 일반적인 실시간 사용 |
| `small` | 488 MB | ~1 GB | ~6x | 좋음 | 한국어/다국어 인식 |
| `medium` | 1.5 GB | ~2.6 GB | ~2x | 매우 좋음 | 높은 정확도 필요 시 |
| `large-v3` | 3.1 GB | ~5 GB | ~1x | 최고 | 최고 품질 필요 시 |

> 속도는 GPU (NVIDIA CUDA) 기준입니다. CPU에서는 약 3-10배 느립니다.

#### GPU vs CPU 성능

- **NVIDIA GPU (CUDA)**: 권장. `large-v3`도 실시간에 가까운 속도
- **Apple Silicon (MPS)**: faster-whisper는 현재 MPS 미지원, CPU 폴백 사용
- **CPU only**: `tiny`~`base` 모델로 제한하는 것을 권장

---

### 활용 사례

- **음성 제어 인터랙티브 설치**: 관객의 음성으로 비주얼 제어
- **실시간 자막 시스템**: 강연, 공연의 실시간 자막 표시
- **음성 → 텍스트 → AI 아트**: 말한 내용을 AI 이미지 생성 프롬프트로 활용
- **음성 데이터 시각화**: 발화 패턴, 빈도, 감정을 시각적으로 표현
- **다국어 전시**: 관객 언어 자동 감지 및 번역 연동
- **접근성 도구**: 청각장애인을 위한 실시간 자막

---

### 트러블슈팅

#### "faster-whisper가 설치되지 않았습니다"
```bash
# TD 외부 Python 환경에서 설치 확인
pip show faster-whisper
# Pythonexe 파라미터가 올바른 Python을 가리키는지 확인
```

#### "모델을 찾을 수 없습니다"
```bash
# 모델 다운로드
python scripts/download_model.py --model base
# Modeldir 파라미터가 models/ 폴더를 가리키는지 확인
```

#### CPU에서 너무 느림
- `tiny` 또는 `base` 모델 사용
- `interval_seconds`를 5초 이상으로 늘리기
- 가능하면 NVIDIA GPU 사용

#### 한국어 인식이 부정확함
- `small` 이상 모델 사용
- `Language` 파라미터를 `ko`로 명시 (자동 감지보다 정확)
- 마이크 입력 품질 확인 (노이즈 제거 필터 적용)

#### TouchDesigner가 멈춤
- 모든 변환은 비동기(스레드)로 실행되므로 TD가 멈추면 안 됩니다
- `Pythonexe` 경로가 잘못되어 프로세스가 무한 대기하는 경우일 수 있음
- 터미널에서 worker를 직접 실행하여 테스트:
  ```bash
  python scripts/whisper_worker.py --model base --audio test.wav
  ```

#### macOS에서 마이크 권한
- 시스템 설정 → 개인정보 보호 및 보안 → 마이크에서 TouchDesigner 허용

---

### 프로젝트 구조

```
TD-Whisper/
├── td/
│   ├── TDWhisper_Extension.py    # Extension 클래스
│   └── TDWhisper_Callbacks.py    # 콜백 예제
├── scripts/
│   ├── whisper_worker.py          # 변환 워커 프로세스
│   └── download_model.py         # 모델 다운로더
├── models/                        # 다운로드된 모델 (gitignored)
├── README.md
├── LICENSE
└── .gitignore
```

---

### 라이선스

MIT License - [0dot77](https://github.com/0dot77)
