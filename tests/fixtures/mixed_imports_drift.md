# Sample Project

## Usage

```python
import os
from json import loads, nonexistent_json_func
from example import hello_world, non_existent_function

# stdlib that doesn't exist (should be ignored with --package example)
nonexistent_json_func()

# local package that doesn't exist (should be detected with --package example)
non_existent_function()
```
