from .helpers import generate_text, FormatType, wait_for_next_step
from typing import Optional, List, Dict, Any
from .prompts import step1_prompt
from ..loaders import load_input, LoaderError
import logging, os
from pathlib import Path
from tqdm import tqdm


logger = logging.getLogger(__name__)

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
        wait_for_next_step()
        if system_prompt == None:
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

        logger.info(f"Processing {len(chunks)} chunks")

        with open(output_file, 'w', encoding='utf-8') as out_file:
            for chunk_num, chunk in enumerate(tqdm(chunks, desc="Processing chunks", disable=None)):
                processed_chunk = process_chunk(
                    client=client,
                    text_chunk=chunk,
                    chunk_num=chunk_num,
                    format_type=format_type,
                    system_prompt=system_prompt,
                    model_name=config["Small-Text-Model"]["model"],
                    max_tokens=config["Step1"]["max_tokens"],
                    temperature=config["Step1"]["temperature"]
                )
                out_file.write(processed_chunk + "\n")
                out_file.flush()

        logger.info("Processing complete")
        return str(output_file)

    except (DocumentProcessingError, ChunkProcessingError, LoaderError) as e:
        logger.error(f"Processing failed: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error during processing: {str(e)}")
        raise DocumentProcessingError(f"Document processing failed: {str(e)}")
