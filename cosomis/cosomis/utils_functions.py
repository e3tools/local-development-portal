import re

def class_name_to_sentence(class_name: str) -> str:
    words = re.findall(r'[A-Z][a-z]*', class_name)
    if words[-1] == 'View':
        words[-1] = 'Viewed'
    return ' '.join(words)
