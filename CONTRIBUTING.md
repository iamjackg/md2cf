## Basic steps

To contribute to `md2cf`, clone this repository, then create a virtual environment and install both the project and testing requirements.

Don't forget to run, add, and change tests as needed!

``` bash
# Clone the project
git clone <project URL>
cd md2cf

# Create Virtual Environment
python -m venv venv

# Activate Virtual Environment
source venv/bin/activate

# Install md2cf as an editable package
pip install -e .

# Install the test dependencies
pip install -r requirements-test.txt
```

You can run all the tests with

```bash
python -m pytest
```
