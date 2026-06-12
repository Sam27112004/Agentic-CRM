import fitz
doc = fitz.open('SenAI_Advanced_Technical_Test.pdf')
text = '\n'.join([page.get_text() for page in doc])
with open('pdf_text.txt', 'w', encoding='utf-8') as f:
    f.write(text)
print("Done! Written to pdf_text.txt")
