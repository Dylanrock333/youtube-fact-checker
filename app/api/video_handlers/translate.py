from googletrans import Translator
import logging

translator = Translator()

async def translate_full_prompt(prompt: str, target_language: str) -> str:
    """Translate entire prompt before sending to LLM"""
    logging.info(f"Translating prompt to {target_language}")
    if target_language == 'en':
        return prompt
    
    try:
        # Translate the entire prompt at once for consistency
        result = await translator.translate(prompt, dest=target_language)
        logging.info(f"Translated prompt to {target_language}")
        return result.text
    except Exception as e:
        logging.error(f"Translation failed: {e}, using English")
        return prompt

def get_language_instruction(target_language: str) -> str:
    """Get native language instruction for LLM"""
    instructions = {
        'es': 'Responde completamente en español.',
        'fr': 'Répondez entièrement en français.',
        'de': 'Antworten Sie vollständig auf Deutsch.',
        'pt': 'Responda completamente em português.',
        'it': 'Rispondi completamente in italiano.',
        'ja': '完全に日本語で回答してください。',
        'zh': '请完全用中文回答。',
        'ru': 'Отвечайте полностью на русском языке.'
    }
    return instructions.get(target_language, 'Respond completely in English.')