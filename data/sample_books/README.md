# Sample Books Directory

Place PDF files here for OCR processing.

## File Naming Convention

PDFs should follow this naming pattern:
```
{book_id}_{chapter_number}_{title}.pdf
```

Example:
- `1_1_introduction.pdf` - Book ID 1, Chapter 1
- `8_3_desert_planet.pdf` - Book ID 8, Chapter 3

## Processing

The PDF processor monitors this directory and automatically:
1. Detects new PDF files
2. Performs OCR using Mathpix API
3. Chunks the extracted text
4. Generates embeddings
5. Stores in Milvus vector database

## Sample Files

You can add sample book chapter PDFs here for testing the OCR pipeline.
