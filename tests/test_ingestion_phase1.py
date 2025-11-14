"""
Tests for Phase 1 ingestion expansion: Jupyter notebooks and code files.

Tests the new extraction functions added in Phase 1:
- extract_jupyter_notebook()
- extract_code_file()
"""

import pytest
import json
from backend.ingest import extract_jupyter_notebook, extract_code_file


class TestJupyterNotebookExtraction:
    """Test Jupyter notebook content extraction."""

    def test_extract_simple_notebook(self):
        """Test extraction from a basic Jupyter notebook."""
        # Create minimal valid notebook
        notebook = {
            "cells": [
                {
                    "cell_type": "markdown",
                    "source": ["# Hello World\n", "This is a test notebook."]
                },
                {
                    "cell_type": "code",
                    "source": ["print('Hello, World!')"],
                    "outputs": [
                        {
                            "text": ["Hello, World!\n"]
                        }
                    ]
                }
            ],
            "metadata": {
                "kernelspec": {
                    "display_name": "Python 3",
                    "language": "python"
                }
            }
        }

        content_bytes = json.dumps(notebook).encode('utf-8')
        result = extract_jupyter_notebook(content_bytes, 'test.ipynb')

        # Verify output
        assert 'JUPYTER NOTEBOOK' in result
        assert 'test.ipynb' in result
        assert 'Python 3' in result
        assert '[Markdown 1]' in result
        assert 'Hello World' in result
        assert '[Code Cell 1]' in result
        assert "print('Hello, World!')" in result
        assert '[Output]' in result
        assert 'Hello, World!' in result

    def test_extract_notebook_with_multiple_cells(self):
        """Test notebook with multiple code and markdown cells."""
        notebook = {
            "cells": [
                {"cell_type": "markdown", "source": ["# Title"]},
                {"cell_type": "code", "source": ["x = 1"], "outputs": []},
                {"cell_type": "code", "source": ["y = 2"], "outputs": []},
                {"cell_type": "markdown", "source": ["## Results"]},
            ],
            "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python"}}
        }

        content_bytes = json.dumps(notebook).encode('utf-8')
        result = extract_jupyter_notebook(content_bytes, 'multi.ipynb')

        assert '[Code Cell 1]' in result
        assert '[Code Cell 2]' in result
        assert '[Markdown 1]' in result
        assert '[Markdown 2]' in result

    def test_extract_notebook_with_dataframe_output(self):
        """Test notebook with pandas DataFrame output."""
        notebook = {
            "cells": [
                {
                    "cell_type": "code",
                    "source": ["import pandas as pd\ndf = pd.DataFrame({'A': [1, 2]})"],
                    "outputs": [
                        {
                            "data": {
                                "text/plain": ["   A\n0  1\n1  2"]
                            }
                        }
                    ]
                }
            ],
            "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python"}}
        }

        content_bytes = json.dumps(notebook).encode('utf-8')
        result = extract_jupyter_notebook(content_bytes, 'dataframe.ipynb')

        assert 'import pandas' in result
        assert '[Output]' in result

    def test_extract_empty_notebook(self):
        """Test notebook with no cells."""
        notebook = {
            "cells": [],
            "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python"}}
        }

        content_bytes = json.dumps(notebook).encode('utf-8')
        result = extract_jupyter_notebook(content_bytes, 'empty.ipynb')

        assert 'JUPYTER NOTEBOOK' in result
        assert 'Python 3' in result

    def test_extract_notebook_invalid_json(self):
        """Test handling of invalid JSON."""
        content_bytes = b"not valid json"

        with pytest.raises(Exception) as exc_info:
            extract_jupyter_notebook(content_bytes, 'invalid.ipynb')

        assert 'Invalid Jupyter notebook format' in str(exc_info.value)

    def test_extract_notebook_source_as_string(self):
        """Test notebook where source is a string instead of list."""
        notebook = {
            "cells": [
                {"cell_type": "code", "source": "x = 1\nprint(x)", "outputs": []}
            ],
            "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python"}}
        }

        content_bytes = json.dumps(notebook).encode('utf-8')
        result = extract_jupyter_notebook(content_bytes, 'string_source.ipynb')

        assert 'x = 1' in result
        assert 'print(x)' in result


class TestCodeFileExtraction:
    """Test source code file extraction."""

    def test_extract_python_file(self):
        """Test Python code extraction."""
        code = """
def hello_world():
    '''Print hello world.'''
    print('Hello, World!')

class MyClass:
    def __init__(self):
        self.name = 'Test'

if __name__ == '__main__':
    hello_world()
"""
        content_bytes = code.encode('utf-8')
        result = extract_code_file(content_bytes, 'hello.py')

        assert 'SOURCE CODE FILE: hello.py' in result
        assert 'Language: Python' in result
        assert 'Total Lines:' in result
        assert 'Code Lines:' in result
        assert 'Functions/Methods:' in result
        assert 'Classes:' in result
        assert 'def hello_world():' in result
        assert 'class MyClass:' in result

    def test_extract_javascript_file(self):
        """Test JavaScript code extraction."""
        code = """
function greet(name) {
    return `Hello, ${name}!`;
}

class Person {
    constructor(name) {
        this.name = name;
    }
}

const arrow = () => console.log('Arrow function');
"""
        content_bytes = code.encode('utf-8')
        result = extract_code_file(content_bytes, 'app.js')

        assert 'Language: JavaScript' in result
        assert 'function greet' in result
        assert 'class Person' in result

    def test_extract_go_file(self):
        """Test Go code extraction."""
        code = """
package main

import "fmt"

func main() {
    fmt.Println("Hello, Go!")
}
"""
        content_bytes = code.encode('utf-8')
        result = extract_code_file(content_bytes, 'main.go')

        assert 'Language: Go' in result
        assert 'package main' in result
        assert 'func main()' in result

    def test_extract_yaml_file(self):
        """Test YAML config file extraction."""
        code = """
version: '3'
services:
  web:
    image: nginx
    ports:
      - "80:80"
"""
        content_bytes = code.encode('utf-8')
        result = extract_code_file(content_bytes, 'docker-compose.yaml')

        assert 'Language: YAML' in result
        assert 'version:' in result
        assert 'services:' in result

    def test_extract_sql_file(self):
        """Test SQL file extraction."""
        code = """
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    username TEXT NOT NULL,
    email TEXT UNIQUE
);

SELECT * FROM users WHERE id = 1;
"""
        content_bytes = code.encode('utf-8')
        result = extract_code_file(content_bytes, 'schema.sql')

        assert 'Language: SQL' in result
        assert 'CREATE TABLE users' in result
        assert 'SELECT * FROM users' in result

    def test_extract_rust_file(self):
        """Test Rust code extraction."""
        code = """
fn main() {
    println!("Hello, Rust!");
}

struct Point {
    x: i32,
    y: i32,
}
"""
        content_bytes = code.encode('utf-8')
        result = extract_code_file(content_bytes, 'main.rs')

        assert 'Language: Rust' in result
        assert 'fn main()' in result
        assert 'struct Point' in result

    def test_extract_file_with_non_utf8(self):
        """Test handling of non-UTF-8 files."""
        # Create content with latin-1 encoding
        code = "print('Héllo')  # Special character"
        content_bytes = code.encode('latin-1')

        result = extract_code_file(content_bytes, 'test.py')

        assert 'Language: Python' in result
        assert 'CODE:' in result

    def test_line_count_excludes_comments(self):
        """Test that code line count excludes comments."""
        code = """
# This is a comment
def test():  # inline comment
    pass
# Another comment
"""
        content_bytes = code.encode('utf-8')
        result = extract_code_file(content_bytes, 'test.py')

        # Should have fewer code lines than total lines
        assert 'Total Lines:' in result
        assert 'Code Lines:' in result

    def test_typescript_file(self):
        """Test TypeScript file extraction."""
        code = """
interface User {
    name: string;
    age: number;
}

const greet = (user: User): string => {
    return `Hello, ${user.name}`;
};
"""
        content_bytes = code.encode('utf-8')
        result = extract_code_file(content_bytes, 'app.ts')

        assert 'Language: TypeScript' in result
        assert 'interface User' in result
        assert 'const greet' in result

    def test_html_file(self):
        """Test HTML file extraction."""
        code = """
<!DOCTYPE html>
<html>
<head>
    <title>Test Page</title>
</head>
<body>
    <h1>Hello World</h1>
</body>
</html>
"""
        content_bytes = code.encode('utf-8')
        result = extract_code_file(content_bytes, 'index.html')

        assert 'Language: HTML' in result
        assert '<!DOCTYPE html>' in result
        assert '<h1>Hello World</h1>' in result

    def test_empty_code_file(self):
        """Test handling of empty code file."""
        content_bytes = b""
        result = extract_code_file(content_bytes, 'empty.py')

        assert 'Language: Python' in result
        assert 'Total Lines: 1' in result  # Empty string creates 1 empty line


class TestIntegrationWithIngest:
    """Test integration with main ingest_upload_file function."""

    def test_jupyter_notebook_routed_correctly(self):
        """Test that .ipynb files are routed to notebook extractor."""
        from backend.ingest import ingest_upload_file

        notebook = {
            "cells": [{"cell_type": "code", "source": ["x = 1"], "outputs": []}],
            "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python"}}
        }

        content_bytes = json.dumps(notebook).encode('utf-8')
        result = ingest_upload_file('test.ipynb', content_bytes)

        assert 'JUPYTER NOTEBOOK' in result

    def test_python_file_routed_correctly(self):
        """Test that .py files are routed to code extractor."""
        from backend.ingest import ingest_upload_file

        code = "def hello():\n    print('hello')"
        content_bytes = code.encode('utf-8')
        result = ingest_upload_file('test.py', content_bytes)

        assert 'SOURCE CODE FILE' in result
        assert 'Language: Python' in result
