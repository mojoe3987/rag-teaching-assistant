from pathlib import Path
from PyPDF2 import PdfReader
from pptx import Presentation

def extract_text_from_pdf(file_path):
    reader = PdfReader(file_path)
    text = ""
    for page_num, page in enumerate(reader.pages):
        text += f"\n[Page {page_num + 1}]\n" + page.extract_text()
    return text

def extract_text_from_pptx(file_path):
    presentation = Presentation(file_path)
    text = ""
    for slide_num, slide in enumerate(presentation.slides):
        slide_text = ""
        for shape in slide.shapes:
            if shape.has_text_frame:
                slide_text += shape.text + " "
        text += f"\n[Slide {slide_num + 1}]\n" + slide_text
    return text

def process_files(input_folder):
    folder = Path(input_folder)
    all_text = []
    for file_path in folder.glob("*"):
        if file_path.suffix == ".pdf":
            all_text.append(extract_text_from_pdf(file_path))
        elif file_path.suffix == ".pptx":
            all_text.append(extract_text_from_pptx(file_path))
        else:
            print(f"Unsupported file format: {file_path}")
    return " ".join(all_text)

def clean_text(content):
    lines = content.splitlines()
    cleaned_lines = [
        line.strip()
        for line in lines
        if not line.isdigit() and len(line.strip()) > 10
    ]
    return "\n".join(cleaned_lines)