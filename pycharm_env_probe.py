import importlib.metadata as metadata
import os
import sys


print("executable:", sys.executable)
print("version:", sys.version)
print("cwd:", os.getcwd())
print("PYTHONPATH:", os.environ.get("PYTHONPATH"))
print("PYTHONNOUSERSITE:", os.environ.get("PYTHONNOUSERSITE"))
print("sys.path:")
for path in sys.path:
    print(" ", path)

for package_name, module_name in (
    ("pydantic", "pydantic"),
    ("pydantic-core", "pydantic_core"),
    ("openai", "openai"),
):
    try:
        module = __import__(module_name)
        print(package_name, metadata.version(package_name), getattr(module, "__file__", None))
    except Exception as exc:
        print(package_name, type(exc).__name__, exc)
