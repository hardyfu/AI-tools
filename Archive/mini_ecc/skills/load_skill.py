import os

def load_skill(filename):
    """
    从 skills 目录加载 skill
    """
    base_dir = os.path.dirname(__file__)
    file_path = os.path.join(base_dir, filename)

    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()