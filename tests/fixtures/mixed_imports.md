# Sample Project

## Usage

```python
import os
import sys
from json import loads, dumps
from example import hello_world, another_function

# Use stdlib
path = os.path.join("foo", "bar")
data = loads('{"key": "value"}')

# Use local package
hello_world()
result = another_function()
```
