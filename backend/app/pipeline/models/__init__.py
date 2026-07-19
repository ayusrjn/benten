import logging
import numpy as np
from typing import Dict, Any

try:
    from transformers import pipeline
except ImportError:
    pipeline = None

logger = logging.getLogger(__name__)

_sentiment_pipeline = None

def get_sentiment_pipeline():
    global _sentiment_pipeline
    if _sentiment_pipeline is None and pipeline is not None:
        try:
            logger.info("Loading RoBERTa sentiment model")
            _sentiment_pipeline = pipeline("text-classification", model="SamLowe/roberta-base-go_emotions", top_k=3)
        except Exception as e:
            logger.error(f"Failed to load sentiment pipeline: {e}")
    return _sentiment_pipeline

def score_sentiment_roberta(transcript_text: str) -> Dict[str, float]:
    """
    Passes textual transcript turns through RoBERTa-go-emotions for sentiment classification.
    """
    logger.info("Running RoBERTa sentiment analysis")
    if not transcript_text.strip():
        return {}
        
    classifier = get_sentiment_pipeline()
    if classifier is None:
        return {"neutral": 1.0}
        
    try:
        # classifier returns a list of lists when top_k is specified
        results = classifier(transcript_text)
        if isinstance(results, list) and len(results) > 0:
            if isinstance(results[0], list):
                results = results[0]
        return {item['label']: float(item['score']) for item in results}
    except Exception as e:
        logger.error(f"Error during sentiment analysis: {e}")
        return {"neutral": 1.0}

def score_voice_quality_nisqa(audio_np: np.ndarray, sample_rate: int = 16000) -> float:
    """
    Evaluates speech quality using NISQA-light to output Mean Opinion Score (MOS) between 1.0 and 5.0.
    Currently mocked until the official NISQA PyTorch module is integrated.
    """
    logger.info("Running NISQA voice quality analysis (Mocked)")
    # Mocking for now as per user request
    return 4.2
