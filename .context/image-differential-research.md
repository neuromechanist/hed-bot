# Image Differential Annotation for Video/Movie Frame Analysis

## Overview

This document summarizes research on using image differencing and Vision-Language Models (VLMs) to automatically detect and annotate frame-to-frame changes in video stimuli, with output expressed as Hierarchical Event Descriptor (HED) annotations. The goal is to inform the design of a video differential annotation feature for HEDit, extending the existing VisionAgent to support temporal change detection in movies and video sequences.

---

## 1. Frame Differencing Approaches in Computer Vision

### 1.1 Classical Techniques

**Temporal Differencing (Frame Subtraction)**

The simplest approach computes the absolute pixel-wise difference between consecutive frames. A threshold is applied to the difference image to identify regions of significant change. This technique is computationally cheap and works well for detecting motion or sudden scene changes, but is sensitive to illumination shifts and camera noise. Two-frame differencing (comparing frame N to frame N-1) is the baseline; three-frame differencing (comparing N-1, N, and N+1) reduces false positives from noise.

**Background Subtraction**

Methods like Gaussian Mixture Models (GMM), K-Nearest Neighbors (KNN), and the ViBe algorithm model a background frame and detect foreground changes against it. OpenCV provides `cv2.createBackgroundSubtractorMOG2()` and `cv2.createBackgroundSubtractorKNN()` as standard implementations. These are more robust to gradual illumination changes than simple differencing. For experimental stimuli (where the "background" is often a controlled display), background subtraction can be highly effective.

**Optical Flow**

Dense optical flow (Farneback, Lucas-Kanade) and learned optical flow (RAFT, FlowNet, GMFlow) estimate per-pixel motion vectors between frames. Optical flow provides not just "what changed" but "where things moved," enabling motion-direction annotations. RAFT (Recurrent All-Pairs Field Transforms), introduced at ECCV 2020, remains a strong baseline; more recent models like FlowFormer (2022) and VideoFlow (2023) improve accuracy on complex scenes with occlusion.

**Scene Change / Shot Boundary Detection**

Scene change detection identifies transitions between shots in video (cuts, dissolves, wipes). Histogram-based methods compare color distribution across frames. Deep learning approaches like TransNet V2 (2020) use temporal CNNs to classify frame pairs as same-scene or different-scene. For movie stimuli in neuroscience experiments, shot boundaries are critical events that evoke distinct neural responses.

### 1.2 Deep Learning Methods (2024-2025)

**Segment Anything Model 2 (SAM 2)**

Meta's SAM 2 (2024) extends the original Segment Anything Model to video, providing temporally consistent object segmentation across frames. It propagates segmentation masks through time, enabling object-level change tracking (appearance, disappearance, deformation). This is relevant for differential annotation because SAM 2 can identify which objects changed, not just which pixels changed.

**Video Foundation Models**

Models like InternVideo2 (2024) and VideoMAE V2 (2023) learn rich temporal representations from video. These can be used for change-aware feature extraction, where the model's attention patterns reveal what changed between frames. While not directly producing change descriptions, they provide strong features for downstream change classification.

**Temporal Difference Networks**

TDN (Temporal Difference Network) and its successors explicitly model frame-to-frame differences as input features for action recognition. The core idea, computing difference frames and feeding them alongside RGB frames, is directly applicable to differential annotation. Recent work (2024-2025) has shown that feeding explicit difference maps to vision transformers improves temporal sensitivity.

### 1.3 Structural Similarity and Perceptual Metrics

Beyond pixel differencing, perceptual similarity metrics can quantify the magnitude of change:

- **SSIM (Structural Similarity Index)**: Measures structural degradation; useful for identifying frames with significant visual changes versus minor noise
- **LPIPS (Learned Perceptual Image Patch Similarity)**: Uses deep features to measure perceptual difference; more aligned with human perception than pixel metrics
- **DISTS (Deep Image Structure and Texture Similarity)**: Separates structural and textural changes

These metrics help threshold which frame transitions are "interesting enough" to annotate, filtering out minor jitter or compression artifacts.

---

## 2. HED for Video/Movie Annotation

### 2.1 Temporal Scoping Tags

HED provides a robust temporal annotation framework through three key tags:

- **Onset**: Marks the beginning of an extended event. Requires a Definition anchor: `(Def/Event-name, Onset)`
- **Offset**: Marks the end of an extended event. Must match a prior Onset: `(Def/Event-name, Offset)`
- **Inset**: Marks an intermediate point within an Onset/Offset scope. Used for state changes during an ongoing event: `(Def/Event-name, Inset)`

Additionally:
- **Duration/# s**: Specifies event duration when known
- **Delay/# s**: Specifies a delayed start relative to the event marker

### 2.2 Modeling Frame-to-Frame Changes in HED

HED does not have dedicated "change detection" tags, but changes can be expressed through combinations of existing tags and temporal scoping. The following patterns are recommended:

**Pattern A: Object Appearance (something new appears)**

```
Definition: (Definition/Face-appearance, (Sensory-event, Visual-presentation, (Face, Appears)))

At frame where face appears:
(Def/Face-appearance, Onset)

At frame where face disappears:
(Def/Face-appearance, Offset)
```

**Pattern B: Scene Change (cut or transition)**

```
At the transition frame:
(Def/Video-playback, Inset), Sensory-event, Visual-presentation, (Scene, Transition)
```

Relevant HED tags for scene content include:
- `Scene` (with extensionAllowed for sub-types like Indoor-scene, Outdoor-scene)
- `Transition` for marking the change event itself
- `Appears` and `Disappears` for object-level changes

**Pattern C: Object Motion**

```
(Def/Video-playback, Inset), Sensory-event, Visual-presentation, ((Human, Face), (Move, To-left-of, Center-of, Computer-screen))
```

**Pattern D: Continuous Video Playback with Sub-Events**

This is the most natural pattern for movie stimuli, matching the example already in the HED comprehensive guide:

```
t=0.000: (Def/Movie-playback, Onset)
t=2.500: (Def/Movie-playback, Inset), (Scene, Outdoor-scene, (Mountain, Lake))
t=5.200: (Def/Movie-playback, Inset), ((Human, Face), Appears)
t=8.100: (Def/Movie-playback, Inset), (Scene, Transition), (Scene, Indoor-scene)
t=12.00: (Def/Movie-playback, Inset), ((Human, Face), Disappears)
t=30.00: (Def/Movie-playback, Offset)
```

### 2.3 Relevant HED Tags for Change Description

From the HED 8.3.0/8.4.0 standard schema, the following tags are relevant for differential annotation:

| Change Type | HED Tags |
|---|---|
| Something appeared | `Appears`, with object tags in a group |
| Something disappeared | `Disappears`, with object tags in a group |
| Something moved | `Move` or `Motion`, with spatial relation tags |
| Scene changed | `Scene`, `Transition` |
| Color/luminance changed | Attribute tags (`Luminance`, `Color`, etc.) with `Increasing` or `Decreasing` |
| Temporal context | `Onset`, `Offset`, `Inset`, `Duration` |
| Event classification | `Sensory-event`, `Visual-presentation` |

### 2.4 BIDS Integration

In Brain Imaging Data Structure (BIDS), movie stimuli are annotated in `events.tsv` files with columns:

- `onset`: Time in seconds from stimulus start
- `duration`: Event duration
- `HED`: HED annotation string (or assembled from sidecar)

For movie stimulus annotation, each detected change becomes a row in events.tsv:

```tsv
onset	duration	event_type	HED
0.0	30.0	movie_start	(Def/Movie-playback, Onset)
2.5	0.0	scene_content	(Def/Movie-playback, Inset), Sensory-event, Visual-presentation, (Scene, Outdoor-scene)
5.2	0.0	face_appears	(Def/Movie-playback, Inset), ((Human, Face), Appears)
30.0	0.0	movie_end	(Def/Movie-playback, Offset)
```

This follows the BIDS convention where instantaneous events have `duration=0` and continuous events are tracked via Onset/Offset.

---

## 3. Vision-Language Models for Change Description

### 3.1 Change Captioning Task

Change captioning is an established computer vision task where the goal is to generate a natural language description of the differences between two images. This is distinct from image captioning (describing a single image) and video captioning (summarizing a video).

**Key Datasets:**
- **CLEVR-Change** (2018): Synthetic dataset with geometric objects; changes include color, material, position, addition, and removal
- **Spot-the-Diff** (2018): Real surveillance camera image pairs with natural language change descriptions
- **CLEVR-DC** (2021): Extended CLEVR-Change with more complex multi-object changes
- **ChangeChat** (2024): Recent dataset designed for conversational change description with VLMs

**Established Models (Pre-VLM Era):**
- DUDA (Dual Dynamic Attention, 2020): Attends to both images simultaneously with cross-attention
- MCCFormers (Multi-Change Captioning Transformers, 2022): Transformer-based with explicit difference features
- Neighborhood Contrastive Transformer (NCT, 2022): Uses contrastive learning to identify changed regions

### 3.2 VLM-Based Change Description (2024-2025)

Recent Vision-Language Models have shown strong zero-shot and few-shot capability for describing differences between images:

**Multi-Image Input Models:**

- **GPT-4V / GPT-4o (OpenAI)**: Accepts multiple images in a single prompt. Can be instructed to compare two frames and describe differences. Performance is strong for high-level semantic changes but can miss subtle pixel-level differences.
- **Claude 3.5 Sonnet / Claude 3 Opus (Anthropic)**: Similar multi-image capability. Strong at structured output (useful for generating HED-compatible descriptions).
- **Qwen-VL / Qwen2-VL (Alibaba)**: Open-weight VLM available through OpenRouter. Supports multi-image input. The Qwen2-VL-72B model (2024) shows competitive change description performance.
- **InternVL2 (2024)**: Open-source VLM with strong multi-image understanding, available in sizes from 2B to 76B parameters.
- **LLaVA-OneVision (2024)**: Extends LLaVA to handle multiple images and video with a unified architecture.

**Specialized Change Detection VLMs:**

- **ChangeCLIP (2024)**: Fine-tunes CLIP for remote sensing change detection; the approach of CLIP-based change features is generalizable.
- **ChangeChat (2024)**: An instruction-tuned VLM specifically designed for interactive change description, where users can ask follow-up questions about what changed.
- **CDChat (2024)**: Another change-detection-specific chatbot built on multi-modal LLMs, trained to identify and describe changes between image pairs.

### 3.3 Prompting Strategies for Frame Comparison

Three main approaches exist for prompting VLMs to describe frame differences:

**Approach 1: Side-by-Side Composition**

Concatenate two frames horizontally (or vertically) into a single image and prompt:

```
"The image shows two video frames side by side. The left frame is from
time T1 and the right frame is from time T2. Describe specifically what
changed between the left and right frames. Focus on: objects that appeared
or disappeared, objects that moved, changes in scene composition, and
lighting changes."
```

Advantages: Works with single-image VLMs. Simple to implement.
Disadvantages: Halves the effective resolution per frame. May confuse the model if frames are very similar.

**Approach 2: Multi-Image Sequential Input**

Send two images as separate inputs with explicit temporal framing:

```
[Image 1: Frame at t=2.5s]
[Image 2: Frame at t=5.2s]

"These are two consecutive frames from a video. The first image is from
2.5 seconds and the second from 5.2 seconds. List all visual changes
between the first and second frame. For each change, specify:
1. What changed (object/region)
2. Type of change (appeared, disappeared, moved, transformed)
3. Location in the frame"
```

Advantages: Full resolution for each frame. More natural for multi-image VLMs.
Disadvantages: Requires multi-image model support. Higher token usage.

**Approach 3: Difference Highlighting / Heatmap Overlay**

Pre-compute a visual difference map and provide it alongside (or overlaid on) the frames:

```
[Image 1: Original frame]
[Image 2: Frame with change regions highlighted in red/yellow overlay]

"The second image shows a video frame with highlighted regions indicating
where visual changes occurred compared to the previous frame. Describe
what changed in each highlighted region."
```

Advantages: Focuses VLM attention on actual change regions. Reduces hallucination of non-existent changes.
Disadvantages: Requires pre-processing pipeline. Heatmap may obscure subtle details.

**Approach 4: Structured Output Prompting**

For HEDit integration, prompting for structured output is essential:

```
"Compare these two video frames and describe changes in the following
JSON format:
{
  'changes': [
    {
      'type': 'appeared|disappeared|moved|changed|scene_cut',
      'object': 'description of the object',
      'location': 'where in the frame',
      'details': 'additional description'
    }
  ],
  'scene_changed': true/false,
  'overall_description': 'one sentence summary'
}"
```

This structured output can be directly mapped to HED tags by the annotation pipeline.

### 3.4 Performance Considerations

For video annotation at scale (e.g., a 2-hour movie at 1 fps sampling), VLM-based change description faces practical constraints:

- **Cost**: At ~$0.01-0.03 per image comparison (GPT-4o pricing), a 2-hour movie at 1 fps would cost $72-216. Using cheaper models (Qwen-VL via OpenRouter) reduces this significantly.
- **Latency**: Each comparison takes 2-5 seconds. For 7200 frame pairs, sequential processing would take 4-10 hours.
- **Filtering**: Not every frame pair needs VLM analysis. Pre-filtering with SSIM or pixel differencing to identify "interesting" transitions can reduce VLM calls by 80-95%.
- **Batching**: Some transitions (steady shots with no changes) can be grouped. Only significant change points need detailed VLM description.

A recommended pipeline: compute SSIM for all consecutive frame pairs, set a threshold (e.g., SSIM < 0.95), and only send frame pairs below the threshold to the VLM for detailed change description.

---

## 4. Existing Tools and Standards for Temporal Video Annotation

### 4.1 Linguistic and Behavioral Annotation Tools

**ELAN (EUDICO Linguistic Annotator)**

Developed by the Max Planck Institute for Psycholinguistics. ELAN is the de facto standard for time-aligned linguistic annotation of video and audio. Key features:
- Multiple parallel annotation tiers (comparable to HED layers)
- Frame-accurate temporal alignment
- Export formats: EAF (XML), tab-delimited, CSV
- Plugin architecture for custom annotation types
- Limitation: Manual annotation only; no automated detection

**ANVIL (Annotation of Video and Language)**

Developed by Michael Kipp. ANVIL provides multi-layer video annotation with:
- Attribute-value coding schemes (somewhat analogous to HED tag structure)
- Track-based temporal organization
- Inter-annotator agreement tools
- XML export format

**VIA (VGG Image Annotator)**

Developed by the Visual Geometry Group at Oxford. Lightweight, browser-based annotation tool that supports:
- Temporal segment annotation for video
- Spatial annotation (bounding boxes, polygons) per frame
- JSON/CSV export
- No server required (runs entirely in browser)
- Recent versions (VIA 3.x) support video annotation with temporal tracks

### 4.2 Neuroscience-Specific Tools

**BIDS Events Files**

In BIDS, `*_events.tsv` files accompany stimulus data (EEG, fMRI, MEG) with columns for onset, duration, and event descriptions. The HED column (or JSON sidecar) provides structured annotation. For movie stimuli, BIDS recommends:

- One row per distinct event (scene change, character action, dialogue onset)
- `stim_file` column to reference the movie file
- HED annotations in a JSON sidecar mapping event types to HED strings

**Studyforrest Project**

The Studyforrest dataset (Hanke et al., 2014-2016) is a landmark dataset pairing fMRI recordings during movie viewing (the film Forrest Gump) with detailed temporal annotations including:
- Shot boundary timestamps
- Audio descriptions for visually impaired viewers (as natural language event descriptions)
- Semantic content labels per scene

This dataset demonstrates the kind of annotation that HEDit's differential annotation could automate. The audio descriptions provide a natural language template for what "change descriptions" should capture.

**Pliers (Psycholinguistic and ImageAnnotation Resource for Experiments)**

A Python library from the Poldrack lab that automates extraction of features from naturalistic stimuli:
- Scene detection using visual features
- Face detection per frame
- Audio feature extraction
- Output compatible with BIDS events format
- Could serve as a pre-processing pipeline feeding into HEDit

### 4.3 Computer Vision Annotation Platforms

**CVAT (Computer Vision Annotation Tool)**

Open-source, web-based tool by Intel for video annotation:
- Frame-by-frame object tracking
- Interpolation between keyframes
- Semi-automatic annotation with built-in models
- CVAT format, COCO, Pascal VOC export
- Supports temporal annotation tracks

**Label Studio**

Open-source data labeling platform:
- Video labeling with temporal segments
- Multi-annotator workflow
- ML-assisted labeling
- Flexible export formats including JSON

### 4.4 Gap Analysis

None of the existing tools combine all three capabilities needed for HEDit's use case:

1. **Automated visual change detection** (CV tools have this, but no HED output)
2. **Natural language change description** (VLMs can do this, but no temporal alignment)
3. **HED-structured output** (only HEDit's annotation pipeline does this)

This represents a genuine gap that HEDit can fill by combining frame differencing, VLM description, and HED annotation in a single pipeline.

---

## 5. Design Recommendations for HEDit

### 5.1 Proposed Architecture: DifferentialAnnotationAgent

The differential annotation feature should be implemented as a new agent (or a mode of the existing VisionAgent) that fits into HEDit's LangGraph workflow.

```
                    ┌──────────────┐
                    │  Input:      │
                    │  Video/Frames│
                    └──────┬───────┘
                           │
                    ┌──────v───────┐
                    │  Frame       │
                    │  Extraction  │
                    │  & Sampling  │
                    └──────┬───────┘
                           │
                    ┌──────v───────┐
                    │  Change      │
                    │  Detection   │
                    │  (CV-based)  │
                    └──────┬───────┘
                           │
                  ┌────────v────────┐
                  │  Significant    │
                  │  Change Filter  │
                  │  (SSIM/pixel)   │
                  └────────┬────────┘
                           │
             ┌─────────────v──────────────┐
             │  VLM Change Description    │
             │  (for significant changes) │
             └─────────────┬──────────────┘
                           │
             ┌─────────────v──────────────┐
             │  HED Annotation Pipeline   │
             │  (existing annotate flow)  │
             └─────────────┬──────────────┘
                           │
             ┌─────────────v──────────────┐
             │  Temporal Assembly          │
             │  (Onset/Offset/Inset)      │
             └─────────────┬──────────────┘
                           │
                    ┌──────v───────┐
                    │  Output:     │
                    │  events.tsv  │
                    │  + sidecar   │
                    └──────────────┘
```

### 5.2 Input Modes

The system should support three input modes:

**Mode 1: Two Frames**
- User provides two images (before/after)
- System describes what changed
- Output: Single HED annotation describing the change
- Use case: Quick comparison, experimental stimulus design

**Mode 2: Video + Timestamps**
- User provides video file and a list of timestamps
- System extracts frames at those timestamps and compares consecutive pairs
- Output: events.tsv with HED annotations per transition
- Use case: Annotating known event boundaries in a movie

**Mode 3: Full Video Analysis**
- User provides video file (and optionally a sampling rate)
- System automatically detects significant changes
- Output: Complete events.tsv with all detected events
- Use case: Automated annotation of naturalistic movie stimuli

### 5.3 Processing Pipeline

**Step 1: Frame Extraction**

```python
# Using OpenCV for frame extraction
import cv2

def extract_frames(video_path: str, sample_fps: float = 1.0) -> list[tuple[float, np.ndarray]]:
    """Extract frames at specified sampling rate.

    Returns list of (timestamp_seconds, frame_array) tuples.
    """
    cap = cv2.VideoCapture(video_path)
    native_fps = cap.get(cv2.CAP_PROP_FPS)
    frame_interval = int(native_fps / sample_fps)
    # ... extract every Nth frame
```

**Step 2: Change Detection and Filtering**

```python
from skimage.metrics import structural_similarity as ssim

def detect_significant_changes(
    frames: list[tuple[float, np.ndarray]],
    ssim_threshold: float = 0.90,
) -> list[tuple[float, float, float]]:
    """Identify frame pairs with significant visual changes.

    Returns list of (timestamp1, timestamp2, ssim_score) for
    pairs below the threshold.
    """
    changes = []
    for i in range(len(frames) - 1):
        t1, frame1 = frames[i]
        t2, frame2 = frames[i + 1]
        score = ssim(frame1, frame2, channel_axis=2)
        if score < ssim_threshold:
            changes.append((t1, t2, score))
    return changes
```

**Step 3: VLM Change Description**

Extend the existing VisionAgent to support frame comparison:

```python
DIFFERENTIAL_PROMPT = """Compare these two video frames and describe what changed.

Frame 1 is from time {t1:.1f}s and Frame 2 is from time {t2:.1f}s.

For each change, specify:
- Type: appeared, disappeared, moved, scene_change, attribute_change
- What: the object or element that changed
- Where: location in the frame (center, left, right, top, bottom)
- Detail: brief description of the change

Respond in a structured format. Focus only on meaningful visual changes,
not compression artifacts or minor lighting shifts."""
```

The VisionAgent's `describe_image` method would be extended with a `compare_frames` method that accepts two images and returns structured change descriptions.

**Step 4: Change-to-HED Mapping**

A mapping layer converts structured change descriptions into HED annotations:

```python
CHANGE_TYPE_TO_HED = {
    "appeared": "Appears",
    "disappeared": "Disappears",
    "moved": "Move",
    "scene_change": "(Scene, Transition)",
    "attribute_change": "",  # Handled by specific attribute tags
}

def change_to_hed_description(change: dict) -> str:
    """Convert a structured change dict to a natural language
    description suitable for the HED annotation pipeline.

    Example input:
        {"type": "appeared", "what": "human face", "where": "center"}

    Example output:
        "A human face appeared at the center of the screen"
    """
    # This NL description is then fed to the existing annotation pipeline
```

**Step 5: Temporal Assembly**

Assemble individual change annotations into a coherent events.tsv with proper Onset/Offset/Inset structure:

```python
def assemble_events_tsv(
    video_onset: float,
    video_offset: float,
    changes: list[dict],  # Each has: timestamp, hed_annotation
    definition_name: str = "Video-playback",
) -> str:
    """Assemble detected changes into BIDS events.tsv format.

    The video itself gets Onset/Offset, and each detected change
    becomes an Inset event.
    """
    rows = []
    rows.append({
        "onset": video_onset,
        "duration": video_offset - video_onset,
        "event_type": "video_start",
        "HED": f"(Def/{definition_name}, Onset)"
    })
    for change in changes:
        rows.append({
            "onset": change["timestamp"],
            "duration": 0.0,
            "event_type": change["type"],
            "HED": f"(Def/{definition_name}, Inset), {change['hed_annotation']}"
        })
    rows.append({
        "onset": video_offset,
        "duration": 0.0,
        "event_type": "video_end",
        "HED": f"(Def/{definition_name}, Offset)"
    })
    return rows
```

### 5.4 Integration with Existing HEDit Architecture

**Option A: New DifferentialAgent (Recommended)**

Create a new `DifferentialAgent` in `src/agents/differential_agent.py` that:
- Accepts two frames (or a video) as input
- Uses CV-based change detection for filtering
- Calls VisionAgent for change description of significant transitions
- Feeds natural language change descriptions to the existing AnnotationAgent
- Assembles temporal structure (Onset/Offset/Inset)

This keeps the existing agents unchanged and adds a new orchestration layer.

**Option B: Extend VisionAgent**

Add a `compare_frames()` method to the existing VisionAgent that:
- Accepts two images instead of one
- Uses a differential prompt instead of the standard description prompt
- Returns change descriptions rather than single-image descriptions

This is simpler but couples frame comparison with single-image description.

**Recommendation: Option A** for the following reasons:
- Separation of concerns (change detection vs. image description vs. HED annotation)
- The DifferentialAgent orchestrates multiple existing agents
- CV-based pre-filtering is a distinct responsibility from VLM description
- Temporal assembly (events.tsv generation) is a new capability not in any existing agent

### 5.5 State Extension

The `HedAnnotationState` would need extension for differential mode:

```python
class DifferentialAnnotationState(TypedDict):
    # Existing fields from HedAnnotationState...

    # New fields for differential mode
    frame_pairs: list[dict]        # [{t1, t2, frame1_data, frame2_data, ssim_score}]
    detected_changes: list[dict]   # [{timestamp, type, description, hed_annotation}]
    video_definition: str          # Definition name for Onset/Offset anchor
    events_tsv: list[dict]         # Assembled events.tsv rows
```

### 5.6 API Endpoints

New endpoints for the FastAPI backend:

```
POST /annotate-differential
  Body: {frame1: base64, frame2: base64}
  Response: {changes: [...], hed_annotations: [...]}

POST /annotate-video
  Body: {video: base64, sample_fps: 1.0, ssim_threshold: 0.90}
  Response: {events: [...], definitions: [...], events_tsv: "..."}
```

### 5.7 CLI Commands

```bash
# Compare two frames
hedit compare frame1.png frame2.png

# Annotate a video
hedit annotate-video movie.mp4 --fps 1.0 --threshold 0.90

# Annotate with specific timestamps
hedit annotate-video movie.mp4 --timestamps 2.5,5.2,8.1,12.0
```

### 5.8 Dependencies

New dependencies required:

```
opencv-python-headless  # Frame extraction and differencing
scikit-image            # SSIM computation
numpy                   # Array operations (likely already present via PIL)
```

These are lightweight and well-maintained. `opencv-python-headless` avoids GUI dependencies for server deployment.

---

## 6. Phased Implementation Plan

### Phase 1: Two-Frame Comparison (MVP)

- Extend VisionAgent with `compare_frames()` method
- Implement side-by-side and multi-image prompting strategies
- Add change-to-HED mapping for basic change types (appear, disappear, scene change)
- New API endpoint: `POST /annotate-differential`
- New CLI command: `hedit compare`
- Tests with synthetic image pairs (CLEVR-like)

### Phase 2: Video Support

- Add frame extraction from video files (OpenCV)
- Implement SSIM-based change filtering
- Create DifferentialAgent for orchestration
- Temporal assembly with Onset/Offset/Inset
- New API endpoint: `POST /annotate-video`
- New CLI command: `hedit annotate-video`
- Output: BIDS-compatible events.tsv

### Phase 3: Advanced Features

- Optical flow integration for motion description
- Object tracking with SAM 2 for object-level change annotation
- Batch processing for long videos
- Configurable change sensitivity
- Support for HED library schemas (e.g., SCORE for clinical video)
- Interactive refinement: user reviews and corrects detected changes

---

## 7. Key References and Resources

### Change Captioning and Detection
- Park et al. (2019). Robust Change Captioning. ICCV 2019. Introduced the Spot-the-Diff dataset and DUDA model.
- Qiu et al. (2021). Describing and Localizing Multiple Changes with Transformers. ICCV 2021. MCCFormers.
- Tu et al. (2023). Neighborhood Contrastive Transformer for Change Captioning. IEEE TMM 2023.
- Liu et al. (2024). ChangeChat: An Interactive Chat-Based Change Detection Model. Instruction-tuned VLM for change description.
- Zheng et al. (2024). CDChat: A Large Multimodal Model for Remote Sensing Change Description. Applied the chat-with-changes paradigm.

### Video Understanding Models
- Teed & Deng (2020). RAFT: Recurrent All-Pairs Field Transforms for Optical Flow. ECCV 2020.
- Souček & Lokoč (2020). TransNet V2: An effective deep network for fast shot transition detection.
- Ravi et al. (2024). SAM 2: Segment Anything in Images and Videos. Meta FAIR.
- Wang et al. (2024). InternVideo2: Scaling Foundation Models for Multimodal Video Understanding.

### HED and BIDS
- Robbins et al. (2022). Capturing the nature of events and event context using Hierarchical Event Descriptors (HED). NeuroImage.
- HED Specification: https://hed-specification.readthedocs.io/
- BIDS Specification: https://bids-specification.readthedocs.io/

### Naturalistic Stimuli Annotation
- Hanke et al. (2014, 2016). Studyforrest: A natural stimulation dataset and its ecosystem.
- McNamara et al. (2017). Pliers: A Python library for automated feature extraction from naturalistic stimuli.

### Vision-Language Models
- OpenAI (2024). GPT-4V / GPT-4o with Vision. Multi-image comparison capability.
- Bai et al. (2024). Qwen2-VL: Enhancing Vision-Language Model's Perception of the World at Any Resolution. Alibaba.
- Chen et al. (2024). InternVL2: Better than the Best -- Expanding Performance Boundaries of Open-Source Multimodal Models.

---

## 8. Open Questions

1. **Sampling rate**: What frame sampling rate balances annotation completeness against cost? 1 fps is a reasonable starting point for movies, but action-heavy scenes may need higher rates.

2. **Change significance threshold**: How to define "significant enough to annotate"? SSIM thresholds are scene-dependent. An adaptive threshold based on local statistics may be needed.

3. **Annotation granularity**: Should every detected object change get its own HED annotation, or should changes be aggregated per "event" (e.g., a scene change encompasses multiple simultaneous changes)?

4. **Multi-modal changes**: Movie stimuli include audio. Should the differential annotation also capture audio changes (dialogue onset, music change, sound effects)? This would require audio feature extraction alongside visual differencing.

5. **Validation**: How to validate that VLM-generated change descriptions are accurate? Ground-truth annotation of video changes is expensive. The Studyforrest dataset's audio descriptions could serve as a benchmark.

6. **HED schema extensions**: Are the existing HED tags sufficient for all change types, or would a HED library schema for video annotation (e.g., `HED_video`) be beneficial? Tags like `Camera-pan`, `Zoom-in`, `Focus-shift` are not in the standard schema but are common in film analysis.

7. **Cost optimization**: For the full video analysis mode, can smaller/local models (e.g., Qwen2-VL-7B via Ollama) handle change description adequately, or is a large model (72B+) required for accuracy?
