from .helpers import generate_text, FormatType, wait_for_next_step
from .prompts import map_step3_system_prompt
from typing import Dict, Any, Optional, List, Tuple
from ast import literal_eval
from pathlib import Path
import logging, pickle, re, json
from tqdm import tqdm


logger = logging.getLogger(__name__)

class TranscriptError(Exception):
    pass
class FileReadError(TranscriptError):
    pass
class TranscriptGenerationError(TranscriptError):
    pass
class InvalidParameterError(TranscriptError):
    pass

def read_pickle_file(filename: str) -> str:
    try:
        with open(filename, 'rb') as file:
            content = pickle.load(file)
        return content
    except FileNotFoundError:
        raise FileReadError(f"File '{filename}' not found")
    except Exception as e:
        raise FileReadError(f"Failed to read pickle file: {str(e)}")


# ---------------------------------------------------------------------------
# Robust transcript parser — multi-strategy fallback
# ---------------------------------------------------------------------------

def _normalize_speaker(s: str) -> str:
    """Normalize 'speaker1', 'SPEAKER 1', 'Speaker_2' → 'Speaker N'."""
    m = re.search(r'(\d+)', s)
    return f"Speaker {m.group(1)}" if m else "Speaker 1"


def _validate_parsed(data) -> bool:
    """Check if data is a non-empty list of (str, str) tuples/lists."""
    if not isinstance(data, list) or not data:
        return False
    for item in data:
        if not isinstance(item, (tuple, list)) or len(item) < 2:
            return False
        if not isinstance(item[0], str) or not isinstance(item[1], str):
            return False
    return True


def _extract_tuples_regex(text: str) -> List[Tuple[str, str]]:
    """Extract ('Speaker N', 'text') patterns with regex."""
    results = []
    # Double-quoted tuples
    for m in re.finditer(
        r'\(\s*"(Speaker\s*\d+)"\s*,\s*"((?:[^"\\]|\\.)*)"\s*\)',
        text, re.DOTALL | re.IGNORECASE
    ):
        results.append((_normalize_speaker(m.group(1)), m.group(2).replace('\\"', '"').strip()))

    if len(results) >= 2:
        return results

    # Single-quoted tuples
    results = []
    for m in re.finditer(
        r"\(\s*'(Speaker\s*\d+)'\s*,\s*'((?:[^'\\]|\\.)*)'\s*\)",
        text, re.DOTALL | re.IGNORECASE
    ):
        results.append((_normalize_speaker(m.group(1)), m.group(2).replace("\\'", "'").strip()))

    if len(results) >= 2:
        return results

    # Mixed quotes — more lenient
    results = []
    for m in re.finditer(
        r"""\(\s*['"](Speaker\s*\d+)['"]\s*,\s*['"](.+?)['"]\s*\)""",
        text, re.DOTALL | re.IGNORECASE
    ):
        results.append((_normalize_speaker(m.group(1)), m.group(2).strip()))

    return results if len(results) >= 2 else []


def _extract_plain_dialogue(text: str) -> List[Tuple[str, str]]:
    """Extract 'Speaker N: text' plain dialogue format (with optional markdown bold)."""
    results = []
    # Split on speaker labels
    parts = re.split(
        r'(?:^|\n)\s*\*{0,2}(Speaker\s*\d+)\*{0,2}\s*[:：\-—]\s*',
        text, flags=re.IGNORECASE
    )
    # parts: [preamble, speaker1, text1, speaker2, text2, ...]
    if len(parts) >= 3:
        for i in range(1, len(parts) - 1, 2):
            speaker = parts[i].strip()
            dialogue = parts[i + 1].strip()
            dialogue = re.sub(r'\s+', ' ', dialogue)
            if dialogue:
                results.append((_normalize_speaker(speaker), dialogue))

    return results if len(results) >= 1 else []


def _extract_json_dialogue(text: str) -> List[Tuple[str, str]]:
    """Extract dialogue from JSON array format."""
    try:
        json_match = re.search(r'\[[\s\S]*\]', text)
        if not json_match:
            return []
        data = json.loads(json_match.group())
        if not isinstance(data, list):
            return []
        results = []
        for item in data:
            if isinstance(item, dict):
                speaker = str(item.get("speaker", item.get("Speaker", "Speaker 1")))
                dialogue = str(item.get("text", item.get("dialogue",
                               item.get("content", item.get("line", "")))))
                if dialogue:
                    results.append((_normalize_speaker(speaker), dialogue))
            elif isinstance(item, (list, tuple)) and len(item) >= 2:
                results.append((_normalize_speaker(str(item[0])), str(item[1])))
        return results if len(results) >= 1 else []
    except Exception:
        return []


def parse_transcript_flexible(raw_text: str) -> List[Tuple[str, str]]:
    """Parse LLM transcript output using multiple fallback strategies.

    Tries in order:
      1. literal_eval (strict Python list-of-tuples)
      2. Regex for ("Speaker N", "text") tuple patterns
      3. 'Speaker N: text' plain dialogue
      4. JSON array of objects
      5. Single-speaker monologue fallback
    """
    raw = (raw_text or "").strip()
    if not raw:
        return []

    # Clean common unicode curly quotes / smart punctuation
    cleaned = raw.replace('\u2018', "'").replace('\u2019', "'")
    cleaned = cleaned.replace('\u201c', '"').replace('\u201d', '"')
    cleaned = cleaned.replace('\u2026', '...')
    # Strip markdown code fences
    cleaned = re.sub(r'^```(?:python)?\s*\n?', '', cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r'\n?```\s*$', '', cleaned, flags=re.MULTILINE)
    cleaned = cleaned.strip()

    # Strategy 1: literal_eval
    try:
        data = literal_eval(cleaned)
        if _validate_parsed(data):
            return [(str(s), str(t)) for s, t in data]
    except Exception:
        pass

    # Strategy 2: Regex tuple extraction
    results = _extract_tuples_regex(cleaned)
    if results:
        logger.info(f"Transcript parsed via regex tuple extraction ({len(results)} turns)")
        return results

    # Strategy 3: Plain dialogue format
    results = _extract_plain_dialogue(cleaned)
    if results:
        logger.info(f"Transcript parsed via plain dialogue extraction ({len(results)} turns)")
        return results

    # Strategy 4: JSON array
    results = _extract_json_dialogue(cleaned)
    if results:
        logger.info(f"Transcript parsed via JSON extraction ({len(results)} turns)")
        return results

    # Strategy 5: Single-speaker monologue fallback
    mono = re.sub(r'[\[\]\(\)]', ' ', cleaned)
    mono = re.sub(r'\s+', ' ', mono).strip()
    if len(mono) > 30:
        logger.warning("All parsing strategies failed — using single-speaker monologue fallback")
        return [("Speaker 1", mono)]

    return []
    
def generate_rewritten_transcript(
    client,
    model_name,
    input_text,
    system_prompt,
    max_tokens,
    temperature,
    format_type,
    language
) -> str:
    try:
        wait_for_next_step()
        if system_prompt == None:
            system_prompt = map_step3_system_prompt(format_type=format_type, language=language)
        else:
            system_prompt = system_prompt
        conversation = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": input_text},
        ]
        out = generate_text(
            client=client,
            model=model_name,
            messages=conversation,
            max_tokens=max_tokens,
            temperature=temperature
        )
        return out

    except Exception as e:
        raise TranscriptGenerationError(f"Failed to generate transcript: {str(e)}")

def generate_rewritten_transcript_with_overlap(
    client,
    model_name,
    input_text,
    max_tokens,
    temperature,
    format_type,
    system_prompt,
    language,
    chunk_size=8000,
    overlap_percent=20
) -> str:
    """Generate transcript in chunks with overlap for seamless continuation."""
    try:
        wait_for_next_step()
        
        # Calculate overlap size in characters
        overlap_size = int(chunk_size * (overlap_percent / 100))
        
        # Split the input text into chunks with overlap
        chunks = []
        start = 0
        while start < len(input_text):
            end = min(start + chunk_size, len(input_text))
            chunks.append(input_text[start:end])
            start = end - overlap_size if end < len(input_text) else end
        
        logger.info(f"Processing transcript in {len(chunks)} chunks with {overlap_percent}% overlap")
        
        # Process each chunk and combine results
        combined_transcript = []
        
        # Add tqdm progress bar
        for i, chunk in tqdm(enumerate(chunks), total=len(chunks), desc="Processing transcript chunks"):
            logger.info(f"Processing chunk {i+1}/{len(chunks)}")
            
            # Add context for continuation chunks
            context = ""
            is_final_chunk = (i == len(chunks) - 1)
            
            if i > 0:
                context = f"IMPORTANT: This is a continuation of a previous transcript. The last part was:\n{combined_transcript[-3:] if len(combined_transcript) >= 3 else combined_transcript}\nContinue the conversation seamlessly from here, maintaining the same style and tone."
            
            if not is_final_chunk:
                context += "\n\nIMPORTANT: DO NOT conclude the conversation or say goodbyes. This is the middle of the conversation, not the end."
            else:
                context += "\n\nThis is the final part of the conversation. You may conclude naturally if appropriate."
            
            # Be more explicit about the format required
            format_instruction = """
            CRITICALLY IMPORTANT: Your output MUST be in the exact format of a Python list of tuples, where each tuple contains a speaker name and their dialogue. 
            Example format: [('Speaker1', 'This is what Speaker1 says.'), ('Speaker2', 'This is Speaker2's response.')]
            Ensure all quotes are properly escaped and the entire response must be valid Python syntax that can be parsed by literal_eval().
            """
            
            # Customize system prompt based on chunk position
            if system_prompt == None:
                chunk_system_prompt = map_step3_system_prompt(format_type=format_type, language=language) + "\n" + format_instruction
            else:
                chunk_system_prompt = system_prompt + "\n" + format_instruction
                
            if not is_final_chunk:
                chunk_system_prompt += "\n\nIMPORTANT: Since this is not the final part of the conversation, DO NOT include any goodbyes, conclusions, or wrap-ups. The conversation should continue naturally."
            
            conversation = [
                {"role": "system", "content": chunk_system_prompt},
                {"role": "user", "content": f"{chunk}\n\n{context}"},
            ]
            
            # Get response from model
            chunk_transcript = generate_text(
                client=client,
                model=model_name,
                messages=conversation,
                max_tokens=max_tokens,
                temperature=temperature,
            )

            # Parse chunk using flexible multi-strategy parser
            logger.debug(f"Raw chunk {i+1} (first 200 chars): {chunk_transcript[:200]}...")
            chunk_data = parse_transcript_flexible(chunk_transcript)

            if not chunk_data:
                logger.warning(f"Flexible parser failed on chunk {i+1}. Trying LLM fix...")
                fix_prompt = [
                    {"role": "system", "content": "Convert the following text into valid Python syntax as a list of tuples with format: [('Speaker 1', 'Text1'), ('Speaker 2', 'Text2'), ...]. Return ONLY the Python list."},
                    {"role": "user", "content": chunk_transcript}
                ]
                try:
                    fixed = generate_text(client=client, model=model_name,
                                          messages=fix_prompt, max_tokens=max_tokens, temperature=0.3)
                    chunk_data = parse_transcript_flexible(fixed)
                except Exception:
                    pass

                if not chunk_data:
                    # Last resort: treat entire chunk output as monologue
                    mono = re.sub(r'[\[\]\(\)\{\}]', ' ', chunk_transcript)
                    mono = re.sub(r'\s+', ' ', mono).strip()
                    if len(mono) > 20:
                        logger.warning(f"Using monologue fallback for chunk {i+1} ({len(mono)} chars)")
                        chunk_data = [("Speaker 1", mono)]
                    else:
                        logger.error(f"All parsers failed on chunk {i+1}. Raw (300 chars): {chunk_transcript[:300]}...")
                        raise TranscriptGenerationError(f"Failed to parse chunk {i+1} after all strategies")

            # Filter goodbye-like messages in non-final chunks
            if not is_final_chunk:
                goodbye_phrases = ["goodbye", "bye", "farewell", "until next time", "see you",
                                   "thanks for listening", "that's all", "wrapping up",
                                   "concluding", "end of", "final thoughts"]
                filtered = []
                for speaker, text in chunk_data:
                    found = next((p for p in goodbye_phrases if p in text.lower()), None)
                    if not found:
                        filtered.append((speaker, text))
                    else:
                        modified = text.lower().split(found)[0]
                        filtered.append((speaker, modified + "let's continue our discussion."))
                chunk_data = filtered

            # Merge into combined transcript
            if i == 0:
                combined_transcript.extend(chunk_data)
            else:
                skip_count = min(2, max(1, len(chunk_data) // 10))
                combined_transcript.extend(chunk_data[skip_count:])

        # Convert back to string representation
        return str(combined_transcript)

    except Exception as e:
        raise TranscriptGenerationError(f"Failed to generate transcript with overlap: {str(e)}")

def validate_transcript_format(transcript: str) -> bool:
    """Check if transcript can be parsed into valid (speaker, text) pairs."""
    return bool(parse_transcript_flexible(transcript))


def step3(
    client = None,
    config: Optional[Dict[str, Any]] = None,
    input_file: str = None,
    output_dir: str = None,
    format_type: FormatType = "podcast",
    system_prompt: str = None,
    language: str = "english"
) -> str:
    try:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        input_path = input_file
        if not input_file.endswith('.pkl'):
            input_path = f"{input_path}.pkl"

        # Read input file
        logger.info(f"Reading input file: {input_file}")
        input_text = read_pickle_file(input_file)

        logger.info(f"Optimizing transcript for TTS...")

        # Check if we need to generate in chunks with overlap
        if len(input_text) > config["Step3"].get("chunk_size", 8000):
            logger.info("Input text is large, generating transcript in chunks with overlap...")
            transcript = generate_rewritten_transcript_with_overlap(
                client=client,
                model_name=config["Big-Text-Model"]["model"],
                input_text=input_text,
                format_type=format_type,
                system_prompt=system_prompt,
                max_tokens=config["Step3"]["max_tokens"],
                temperature=config["Step1"]["temperature"],
                chunk_size=config["Step3"].get("chunk_size", 8000),
                overlap_percent=config["Step3"].get("overlap_percent", 10),
                language=language
            )
        else:
            # Generate rewritten transcript in one go
            logger.info(f"Generating rewritten transcript...")
            transcript = generate_rewritten_transcript(
                client=client,
                system_prompt=system_prompt,
                model_name=config["Big-Text-Model"]["model"],
                input_text=input_text,
                format_type=format_type,
                max_tokens=config["Step3"]["max_tokens"],
                temperature=config["Step1"]["temperature"],
                language=language
            )

        # ── Flexible parsing with multi-strategy fallback ────────
        parsed = parse_transcript_flexible(transcript)

        if not parsed:
            logger.warning("Flexible parser failed on raw output. Trying LLM fix...")
            fix_prompt = [
                {"role": "system", "content": "Convert the following text into valid Python syntax as a list of tuples with format: [('Speaker 1', 'Text1'), ('Speaker 2', 'Text2'), ...]. Return ONLY the Python list, nothing else."},
                {"role": "user", "content": transcript}
            ]
            try:
                fixed = generate_text(
                    client=client,
                    model=config["Big-Text-Model"]["model"],
                    messages=fix_prompt,
                    max_tokens=config["Step3"]["max_tokens"],
                    temperature=0.3,
                )
                parsed = parse_transcript_flexible(fixed)
            except Exception:
                pass

        if not parsed:
            # Last resort: force monologue from raw LLM output
            mono = re.sub(r'[\[\]\(\)\{\}]', ' ', transcript)
            mono = re.sub(r'\s+', ' ', mono).strip()
            if len(mono) > 20:
                logger.warning(f"All strategies failed — forcing monologue fallback ({len(mono)} chars)")
                parsed = [("Speaker 1", mono)]
            else:
                logger.error(f"All parsing strategies failed. Raw (300 chars): {transcript[:300]}...")
                raise TranscriptGenerationError(
                    "Could not parse transcript into speaker-dialogue pairs after all strategies "
                    "(literal_eval, regex tuples, plain dialogue, JSON, monologue fallback). "
                    "The LLM model may be too small for structured output — try a larger model (3b+)."
                )

        # Use the parsed list as the canonical transcript
        transcript = str(parsed)
        logger.info(f"Transcript parsed successfully: {len(parsed)} dialogue turns")

        # Save transcript
        output_file = output_dir / 'podcast_ready_data'
        with open(f'{output_file}.pkl', 'wb') as file:
            pickle.dump(transcript, file)

        with open(f'{output_file}.txt', 'w') as file:
            file.write(transcript)

        logger.info(f"Rewritten transcript saved to: {output_file}")
        return str(input_file), str(output_file)

    except (FileReadError, TranscriptGenerationError, InvalidParameterError) as e:
        logger.error(f"Transcript rewriting failed: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error during transcript rewriting: {str(e)}")
        raise TranscriptError(f"Transcript rewriting failed: {str(e)}")