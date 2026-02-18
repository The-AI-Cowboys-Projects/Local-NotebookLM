from .helpers import generate_text, FormatType, wait_for_next_step
from typing import Optional, List, Dict, Any
from .prompts import step1_prompt
from ..loaders import load_input, LoaderError
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging, os
from pathlib import Path
from tqdm import tqdm


logger = logging.getLogger(__name__)

MAX_WORKERS = 4  # parallel LLM calls for chunk cleaning

class DocumentProcessingError(Exception):
    pass
class ChunkProcessingError(DocumentProcessingError):
    pass

def create_word_bounded_chunks(text: str, target_chunk_size: int) -> List[str]:
    try:
        words = text.split()
        chunks = []
        current_chunk = []
        current_length = 0

        for word in words:
            word_length = len(word) + 1
            if current_length + word_length > target_chunk_size and current_chunk:
                chunks.append(' '.join(current_chunk))
                current_chunk = [word]
                current_length = word_length
            else:
                current_chunk.append(word)
                current_length += word_length

        if current_chunk:
            chunks.append(' '.join(current_chunk))

        return chunks
    except Exception as e:
        raise ChunkProcessingError(f"Failed to create text chunks: {str(e)}")

def process_chunk(
        client,
        text_chunk,
        system_prompt,
        chunk_num,
        model_name,
        max_tokens,
        temperature,
        format_type
    ) -> str:
    try:
        if system_prompt is None:
            system = step1_prompt.format(text_chunk=text_chunk, format_type=format_type)
        else:
            system = system_prompt

        messages = [
            {"role": "user", "content": system},
        ]
        return generate_text(
            client=client,
            model=model_name,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )

    except Exception as e:
        raise ChunkProcessingError(f"Failed to process chunk {chunk_num}: {str(e)}")

def step1(
    input_path: str,
    client: Any = None,
    config: Optional[Dict[str, Any]] = None,
    output_dir: str = None,
    format_type: FormatType = "podcast",
    system_prompt: str = None
) -> str:
    try:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        extracted_text = load_input(input_path, config["Step1"]["max_chars"])
        if not extracted_text:
            raise DocumentProcessingError("No text extracted from document")

        input_file = output_dir / 'extracted_text.txt'
        input_file.write_text(extracted_text, encoding='utf-8')

        chunks = create_word_bounded_chunks(extracted_text, config["Step1"]["chunk_size"])
        output_file = output_dir / f"clean_{input_file.name}"

        num_chunks = len(chunks)
        logger.info(f"Processing {num_chunks} chunks")

        model_name = config["Small-Text-Model"]["model"]
        max_tokens = config["Step1"]["max_tokens"]
        temperature = config["Step1"]["temperature"]

        if num_chunks <= 1:
            # Single chunk — no need for thread pool overhead
            results = {}
            for i, chunk in enumerate(chunks):
                results[i] = process_chunk(
                    client=client,
                    text_chunk=chunk,
                    chunk_num=i,
                    format_type=format_type,
                    system_prompt=system_prompt,
                    model_name=model_name,
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
        else:
            # Parallel chunk processing — each chunk is independently cleaned
            workers = min(MAX_WORKERS, num_chunks)
            logger.info(f"Using {workers} parallel workers")
            results = {}
            errors = []

            with ThreadPoolExecutor(max_workers=workers) as pool:
                future_to_idx = {}
                for i, chunk in enumerate(chunks):
                    fut = pool.submit(
                        process_chunk,
                        client=client,
                        text_chunk=chunk,
                        chunk_num=i,
                        format_type=format_type,
                        system_prompt=system_prompt,
                        model_name=model_name,
                        max_tokens=max_tokens,
                        temperature=temperature,
                    )
                    future_to_idx[fut] = i

                for fut in tqdm(as_completed(future_to_idx), total=num_chunks, desc="Processing chunks", disable=None):
                    idx = future_to_idx[fut]
                    try:
                        results[idx] = fut.result()
                    except Exception as e:
                        errors.append(f"Chunk {idx}: {e}")

            if errors:
                raise ChunkProcessingError(
                    f"{len(errors)} chunk(s) failed:\n  " + "\n  ".join(errors)
                )

        # Write results in original order
        with open(output_file, 'w', encoding='utf-8') as out_file:
            for i in range(num_chunks):
                out_file.write(results[i] + "\n")
                out_file.flush()

        logger.info("Processing complete")
        return str(output_file)

    except (DocumentProcessingError, ChunkProcessingError, LoaderError) as e:
        logger.error(f"Processing failed: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error during processing: {str(e)}")
        raise DocumentProcessingError(f"Document processing failed: {str(e)}")
