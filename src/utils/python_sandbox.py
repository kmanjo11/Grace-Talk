import sys
import io
import contextlib
from types import ModuleType
import builtins

class RestrictedEnvironment:
    """Basic Python sandbox using restricted execution environment"""

    def __init__(self):
        # Safe built-in functions
        self.safe_builtins = {
            'abs': builtins.abs,
            'all': builtins.all,
            'any': builtins.any,
            'ascii': builtins.ascii,
            'bin': builtins.bin,
            'bool': builtins.bool,
            'bytearray': builtins.bytearray,
            'bytes': builtins.bytes,
            'callable': builtins.callable,
            'chr': builtins.chr,
            'classmethod': builtins.classmethod,
            'complex': builtins.complex,
            'dict': builtins.dict,
            'divmod': builtins.divmod,
            'enumerate': builtins.enumerate,
            'filter': builtins.filter,
            'float': builtins.float,
            'format': builtins.format,
            'frozenset': builtins.frozenset,
            'hash': builtins.hash,
            'hex': builtins.hex,
            'id': builtins.id,
            'int': builtins.int,
            'isinstance': builtins.isinstance,
            'issubclass': builtins.issubclass,
            'iter': builtins.iter,
            'len': builtins.len,
            'list': builtins.list,
            'map': builtins.map,
            'max': builtins.max,
            'min': builtins.min,
            'next': builtins.next,
            'object': builtins.object,
            'oct': builtins.oct,
            'ord': builtins.ord,
            'pow': builtins.pow,
            'print': builtins.print,
            'property': builtins.property,
            'range': builtins.range,
            'repr': builtins.repr,
            'reversed': builtins.reversed,
            'round': builtins.round,
            'set': builtins.set,
            'slice': builtins.slice,
            'sorted': builtins.sorted,
            'staticmethod': builtins.staticmethod,
            'str': builtins.str,
            'sum': builtins.sum,
            'super': builtins.super,
            'tuple': builtins.tuple,
            'type': builtins.type,
            'zip': builtins.zip,
        }

        # Restricted globals
        self.restricted_globals = {
            '__builtins__': self.safe_builtins,
            '__name__': '__main__',
            '__doc__': None,
            '__package__': None,
            '__loader__': None,
            '__spec__': None,
            '__annotations__': {},
            '__file__': '<string>',
        }

    def execute_code(self, code: str, language: str = "python") -> str:
        """Execute code in restricted Python environment"""
        if language != "python":
            return f"⚠️ Python sandbox only supports Python code. For {language}, use local execution."

        try:
            # Capture stdout
            old_stdout = sys.stdout
            sys.stdout = captured_output = io.StringIO()

            # Execute code in restricted environment
            exec(code, self.restricted_globals)

            # Get output
            output = captured_output.getvalue()

            # Restore stdout
            sys.stdout = old_stdout

            if output.strip():
                return f"🐍 Python Sandbox:\n{output}"
            else:
                return "🐍 Python Sandbox: Code executed successfully (no output)"

        except Exception as e:
            # Restore stdout in case of error
            sys.stdout = old_stdout
            return f"🐍 Python Sandbox Error: {str(e)}"
