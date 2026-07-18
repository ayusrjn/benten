# Audio Metrics & Scoring Guide

This guide details the mathematical formulas, voice activity detection thresholds, and deep learning models used by Benten's analysis engine to process raw audio, extract conversational features, and compute overall conversation health scores.

---

## 1. Audio Prep & Normalization

Before signal processing, the Celery worker standardizes the input audio binary.

*   **Format Conversion:** Using `pydub` or `librosa`, audio is decoded and resampled to **16kHz, 16-bit PCM WAV** format.
*   **Loudness Normalization:** The signal amplitude is normalized using the **EBU R128** standard to a target loudness of **-23 LUFS** (Loudness Units relative to Full Scale). This ensures uniform amplitude levels, preventing volume drops from skewing feature extraction.

---

## 2. Speech Segmentation & Diarization

To analyze turn-taking, the engine must distinguish speech from silence and attribute active speech segments to either the `Agent` or the `User`.

### Voice Activity Detection (VAD)
*   **Model:** **Silero VAD (v4)** (loaded via ONNX Runtime for low-latency CPU inference).
*   **Configuration Parameters:**
    *   `threshold = 0.5` (Probability threshold to classify a frame as speech).
    *   `min_speech_duration_ms = 250` (Segments shorter than 250ms are discarded as background noise).
    *   `min_silence_duration_ms = 100` (Speech frames separated by less than 100ms are merged).

### Speaker Diarization
Diarization segments the speech timeline by speaker ID.
*   **Model:** **PyAnnote.audio (v3.1)** (`pyannote/speaker-diarization-3.1` model).
*   **Stereo Channel Mapping:**
    *   If the ingested audio is *stereo*, diarization bypasses model execution. The engine maps **Channel 0** (Left) directly to the **Agent** and **Channel 1** (Right) directly to the **User**.
*   **Mono Channel Clustering:**
    *   If the audio is *mono*, PyAnnote clusters speaker embeddings.
    *   **Role Mapping Heuristic:** The engine scans the first speaking segment. The speaker initiating the call is mapped as `Agent` (matching standard reception greetings); the other speaker is mapped as `User`.

---

## 3. Metric Calculations

### A. Turn Latency
Turn Latency measures the response delay between the user finishing a sentence and the agent initiating a reply.

$$\text{Latency} = t_{\text{agent\_speech\_start}} - t_{\text{user\_speech\_end}}$$

#### Sub-Component Latency Breakdown
For voice providers that supply event logs (STT, LLM, TTS), total latency is decomposed:

$$\text{Latency}_{\text{Total}} = \text{Latency}_{\text{STT}} + \text{Latency}_{\text{LLM}} + \text{Latency}_{\text{TTS}} + \text{Latency}_{\text{Network}}$$

*   **$\text{Latency}_{\text{STT}}$:** Time elapsed from user ending speech to transcription finalized.
*   **$\text{Latency}_{\text{LLM}}$:** Time elapsed from prompt submitted to first token received from the LLM.
*   **$\text{Latency}_{\text{TTS}}$:** Time elapsed from first token sent to first byte of synthetic audio generated.
*   **$\text{Latency}_{\text{Network}}$:** Network transmission and streaming buffers.

### B. Dead Air (Silence Ratio)
Dead Air is defined as any period during a conversation where neither the Agent nor the User is speaking for a duration greater than **1.5 seconds**.

$$\text{Dead Air \%} = \left( \frac{\sum d_{\text{silence\_gap} > 1.5\text{s}}}{\text{Total Call Duration}} \right) \times 100$$

*Where $d_{\text{silence\_gap}}$ is the duration of an inactive VAD segment.*

### C. Interruptions (Overlaps & Barge-ins)
An interruption is detected when both the Agent and the User speak simultaneously. This is represented by overlapping time blocks in their respective diarization tracks.

$$\text{Overlap} \iff t_{\text{user\_start}} < t_{\text{agent\_end}} \quad \text{and} \quad t_{\text{agent\_start}} < t_{\text{user\_end}}$$

#### Interruption Classifications
*   **Barge-in (Agent Back-off):** The user starts speaking while the agent is speaking, and the agent ceases speech within **800ms**.
*   **Double-Talk (Clash):** Both speakers continue talking concurrently for more than **1.0 second**.

$$\text{Barge-in} \iff \text{Overlap} \land d_{\text{overlap\_agent}} \le 800\text{ms}$$
$$\text{Double-Talk} \iff \text{Overlap} \land d_{\text{overlap\_both}} > 1000\text{ms}$$

### D. Speaking Rate
Speaking rate is computed per individual speech turn.

$$\text{WPM} = \frac{\text{Word Count in Segment}}{\left( \frac{t_{\text{segment\_end}} - t_{\text{segment\_start}}}{60} \right)}$$

*   **Optimal Range:** 110 to 150 WPM. Rates $< 90$ WPM indicate lagging, while $> 180$ WPM indicate high urgency or comprehension barriers.

### E. Sentiment & Emotion Timeline
Emotion mapping runs in a dual-pass evaluation:

1.  **Textual Sentiment:** Mapped from segment text transcriptions using **RoBERTa-base-go_emotions** (fine-tuned transformer). The model outputs probabilities for 28 emotion tags, which Benten groups into:
    *   `Positive` (Joy, Approval)
    *   `Neutral` (Neutral)
    *   `Frustrated` (Anger, Annoyance)
    *   `Confused` (Confusion)
2.  **Acoustic Emotion:** The raw user audio segment is passed to **Wav2Vec2-Emotion** (e.g., `wav2vec2-lg-xlsr-speech-emotion-recognition`). It extracts fundamental frequency (F0) shifts, jitter, and amplitude variations to verify emotional arousal.
    *   *High Arousal + Negative Text:* Logged as `Frustrated` (😡).
    *   *Low Arousal + Negative Text:* Logged as `Hesitant/Dissatisfied` (😞).

### F. Voice Quality (MOS)
*   **Model:** **NISQA-light** (reference-free deep learning speech quality assessment).
*   **Output:** Mean Opinion Score (MOS) estimation on a scale of **1.0 (poor)** to **5.0 (excellent)**, measuring signal-to-noise ratio (SNR), packet loss, and clipping.
*   **Conversion to Percentage Score:**
    $$\text{Quality Score} = \min\left(100, \max\left(0, (\text{MOS} - 1.0) \times 25\right)\right)$$

---

## 4. Scoring Engine Weights

The scoring engine aggregates these indicators into a unified **Conversation Health Score (0-100)**:

| Metric Indicator | Weight | Penalty Rule |
| :--- | :---: | :--- |
| **Turn Latency** | 30% | Linear decay for average latency $> 1.2\text{s}$. Penalty caps at 0 points if latency $\ge 3.0\text{s}$. |
| **Dead Air** | 25% | Score decays if Dead Air Ratio exceeds **8%** of the call duration. |
| **Interruptions** | 20% | $-5$ points per **Double-Talk** event; $-2$ points per failed barge-in. |
| **Voice Quality** | 15% | Linear drop if estimated MOS is $< 3.8$ (representing standard VoIP degradation). |
| **Emotion Stability** | 10% | Deducts points if the User emotion timeline contains consecutive `Frustrated` or `Confused` flags. |

### Health Score Formula

$$\text{Health Score} = 100 - (\text{Penalty}_{\text{Latency}} + \text{Penalty}_{\text{DeadAir}} + \text{Penalty}_{\text{Interruptions}} + \text{Penalty}_{\text{Quality}} + \text{Penalty}_{\text{Emotion}})$$
